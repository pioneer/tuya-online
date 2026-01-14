"""
AWS Lambda handler for Tuya power monitoring.
Polls Tuya device status, applies debouncing, and sends Telegram notifications on state changes.
"""

import json
import os
import traceback
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any

from tuya_client import TuyaClient
from state_store import StateStore
from notifier import TelegramNotifier
from logic import process_state_change, DebounceState


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler invoked by EventBridge schedule every minute.
    
    Supports test mode: invoke with {"test": true} to send a test notification.
    
    Steps:
    1. Load previous state from DynamoDB
    2. Query Tuya device online status
    3. Apply debouncing logic
    4. Send Telegram notification if state changed
    5. Persist new state to DynamoDB
    """
    print(json.dumps({"event": "lambda_invoked", "request_id": context.aws_request_id}))
    
    # Load environment variables
    tuya_endpoint = os.environ["TUYA_ENDPOINT"]
    tuya_access_id = os.environ["TUYA_ACCESS_ID"]
    tuya_access_key = os.environ["TUYA_ACCESS_KEY"]
    tuya_device_id = os.environ["TUYA_DEVICE_ID"]
    tg_bot_token = os.environ["TG_BOT_TOKEN"]
    tg_chat_id = os.environ["TG_CHAT_ID"]
    ddb_table = os.environ["DDB_TABLE"]
    debounce_count = int(os.environ.get("DEBOUNCE_COUNT", "2"))
    timezone_str = os.environ.get("TIMEZONE", "Europe/Kyiv")
    
    try:
        timezone = ZoneInfo(timezone_str)
    except Exception as e:
        print(json.dumps({"error": "invalid_timezone", "timezone": timezone_str, "message": str(e)}))
        timezone = ZoneInfo("UTC")
    
    # Initialize notifier (needed for test mode)
    notifier = TelegramNotifier(tg_bot_token, tg_chat_id)
    
    # Handle test mode
    if event.get("test"):
        print(json.dumps({"event": "test_mode", "test": True}))
        
        # Format timestamp in Ukrainian
        now = datetime.now(timezone)
        months_uk = {
            1: "січня", 2: "лютого", 3: "березня", 4: "квітня",
            5: "травня", 6: "червня", 7: "липня", 8: "серпня",
            9: "вересня", 10: "жовтня", 11: "листопада", 12: "грудня"
        }
        timestamp_str = f"{now.day} {months_uk[now.month]} {now.year} о {now.strftime('%H:%M')}"
        
        message = f"🧪 Тестове повідомлення з AWS Lambda\n\n🕐 {timestamp_str}\n\nМоніторинг електроживлення працює!"
        
        try:
            notifier.send_message(message)
            print(json.dumps({"event": "test_notification_sent", "message": message}))
            return {
                "statusCode": 200,
                "body": json.dumps({"success": True, "test": True, "message": "Test notification sent"})
            }
        except Exception as e:
            print(json.dumps({"event": "test_notification_failed", "error": str(e)}))
            return {
                "statusCode": 500,
                "body": json.dumps({"success": False, "error": str(e)})
            }
    
    # Initialize remaining components
    state_store = StateStore(ddb_table)
    tuya_client = TuyaClient(tuya_endpoint, tuya_access_id, tuya_access_key)
    
    try:
        # Step 1: Load previous state
        prev_state = state_store.load_state()
        print(json.dumps({"event": "state_loaded", "state": prev_state}))
        
        # Step 2: Query Tuya device
        try:
            device_online = tuya_client.get_device_online_status(tuya_device_id)
            print(json.dumps({"event": "tuya_query_success", "device_id": tuya_device_id, "online": device_online}))
        except Exception as tuya_error:
            print(json.dumps({
                "event": "tuya_query_failed",
                "error": str(tuya_error),
                "traceback": traceback.format_exc()
            }))
            # Don't change state if Tuya API fails
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "tuya_api_failed", "message": str(tuya_error)})
            }
        
        # Step 3: Apply debouncing and state transition logic
        new_state, should_notify = process_state_change(
            prev_state=DebounceState(**prev_state),
            current_online=device_online,
            debounce_threshold=debounce_count
        )
        
        new_state_dict = new_state.to_dict()
        print(json.dumps({
            "event": "state_processed",
            "new_state": new_state_dict,
            "should_notify": should_notify
        }))
        
        # Step 4: Send notification if state changed
        notification_sent = False
        if should_notify:
            # Format timestamp in Ukrainian
            now = datetime.now(timezone)
            months_uk = {
                1: "січня", 2: "лютого", 3: "березня", 4: "квітня",
                5: "травня", 6: "червня", 7: "липня", 8: "серпня",
                9: "вересня", 10: "жовтня", 11: "листопада", 12: "грудня"
            }
            day = now.day
            month = months_uk[now.month]
            year = now.year
            time_str = now.strftime("%H:%M")
            timestamp_str = f"{day} {month} {year} о {time_str}"
            
            if new_state.last_confirmed_online:
                message = f"✅ Електрику увімкнено!\n\n🕐 {timestamp_str}"
            else:
                message = f"❌ Електрику вимкнено\n\n🕐 {timestamp_str}"
            
            try:
                notifier.send_message(message)
                notification_sent = True
                print(json.dumps({
                    "event": "notification_sent",
                    "message": message,
                    "timestamp": timestamp_str
                }))
            except Exception as notif_error:
                print(json.dumps({
                    "event": "notification_failed",
                    "error": str(notif_error),
                    "traceback": traceback.format_exc()
                }))
                # Mark notification failure but continue to save state
                new_state_dict["notify_failed"] = True
        
        # Step 5: Persist new state
        state_store.save_state(new_state_dict)
        print(json.dumps({"event": "state_saved", "state": new_state_dict}))
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "success": True,
                "device_online": device_online,
                "notification_sent": notification_sent,
                "state": new_state_dict
            })
        }
        
    except Exception as e:
        print(json.dumps({
            "event": "unhandled_error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "internal_error", "message": str(e)})
        }
