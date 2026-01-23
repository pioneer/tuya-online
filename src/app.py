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


# Ukrainian month names for human-friendly timestamps
MONTHS_UK = {
    1: "січня",
    2: "лютого",
    3: "березня",
    4: "квітня",
    5: "травня",
    6: "червня",
    7: "липня",
    8: "серпня",
    9: "вересня",
    10: "жовтня",
    11: "листопада",
    12: "грудня",
}


def format_ukrainian_timestamp(dt: datetime) -> str:
    """Format datetime in Ukrainian human-friendly format."""
    return f"{dt.day} {MONTHS_UK[dt.month]} {dt.year} о {dt.strftime('%H:%M')}"


def format_ukrainian_duration(seconds: float) -> str:
    """
    Format duration in Ukrainian.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string like "2 години 15 хвилин" or "45 хвилин" or "3 дні 5 годин"
    """
    total_seconds = int(seconds)

    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60

    parts = []

    if days > 0:
        if days == 1:
            parts.append("1 день")
        elif 2 <= days <= 4:
            parts.append(f"{days} дні")
        else:
            parts.append(f"{days} днів")

    if hours > 0:
        if hours == 1:
            parts.append("1 година")
        elif 2 <= hours <= 4:
            parts.append(f"{hours} години")
        else:
            parts.append(f"{hours} годин")

    if minutes > 0 or not parts:  # Show minutes if nothing else or if > 0
        if minutes == 1:
            parts.append("1 хвилина")
        elif 2 <= minutes <= 4:
            parts.append(f"{minutes} хвилини")
        else:
            parts.append(f"{minutes} хвилин")

    return " ".join(parts)


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
    confirmation_delay_minutes = int(os.environ.get("CONFIRMATION_DELAY_MINUTES", "3"))
    timezone_str = os.environ.get("TIMEZONE", "Europe/Kyiv")

    try:
        timezone = ZoneInfo(timezone_str)
    except Exception as e:
        print(
            json.dumps({"error": "invalid_timezone", "timezone": timezone_str, "message": str(e)})
        )
        timezone = ZoneInfo("UTC")

    # Initialize notifier (needed for test mode)
    notifier = TelegramNotifier(tg_bot_token, tg_chat_id)

    # Handle test mode
    if event.get("test"):
        print(json.dumps({"event": "test_mode", "test": True}))

        now = datetime.now(timezone)
        timestamp_str = format_ukrainian_timestamp(now)

        message = f"🧪 Тестове повідомлення з AWS Lambda\n\n🕐 {timestamp_str}\n\nМоніторинг електроживлення працює!"

        try:
            notifier.send_message(message)
            print(json.dumps({"event": "test_notification_sent", "message": message}))
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {"success": True, "test": True, "message": "Test notification sent"}
                ),
            }
        except Exception as e:
            print(json.dumps({"event": "test_notification_failed", "error": str(e)}))
            return {"statusCode": 500, "body": json.dumps({"success": False, "error": str(e)})}

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
            print(
                json.dumps(
                    {
                        "event": "tuya_query_success",
                        "device_id": tuya_device_id,
                        "online": device_online,
                    }
                )
            )
        except Exception as tuya_error:
            print(
                json.dumps(
                    {
                        "event": "tuya_query_failed",
                        "error": str(tuya_error),
                        "traceback": traceback.format_exc(),
                    }
                )
            )
            # Don't change state if Tuya API fails
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "tuya_api_failed", "message": str(tuya_error)}),
            }

        # Save timestamps BEFORE processing (we need them for notifications)
        # first_observed_change_ts is when the state change was FIRST detected (streak=1)
        prev_first_observed_change_ts = prev_state.get("first_observed_change_ts")
        prev_last_confirmed_online_ts = prev_state.get("last_confirmed_online_ts")
        prev_last_confirmed_offline_ts = prev_state.get("last_confirmed_offline_ts")

        # Step 3: Apply debouncing and state transition logic
        new_state, should_notify = process_state_change(
            prev_state=DebounceState(**prev_state),
            current_online=device_online,
            debounce_threshold=debounce_count,
            confirmation_delay_seconds=confirmation_delay_minutes * 60,
        )

        new_state_dict = new_state.to_dict()
        print(
            json.dumps(
                {
                    "event": "state_processed",
                    "new_state": new_state_dict,
                    "should_notify": should_notify,
                }
            )
        )

        # Step 4: Send notification if state changed
        notification_sent = False
        if should_notify:
            # Use the timestamp when the change was FIRST observed (streak=1)
            # This shows when the outage actually started, not when it was confirmed
            if prev_first_observed_change_ts is not None:
                event_time = datetime.fromtimestamp(prev_first_observed_change_ts, tz=timezone)
            else:
                # Fallback to now if no timestamp (shouldn't happen)
                event_time = datetime.now(timezone)

            timestamp_str = format_ukrainian_timestamp(event_time)

            if new_state.last_confirmed_online:
                message = f"✅ Електрику увімкнено!\n\n🕐 {timestamp_str}"
                # Add outage duration if we know when it went offline
                if prev_last_confirmed_offline_ts is not None:
                    # Calculate duration from when power went offline to when it came back
                    duration_seconds = (
                        prev_first_observed_change_ts - prev_last_confirmed_offline_ts
                    )
                    if duration_seconds > 0:
                        duration_str = format_ukrainian_duration(duration_seconds)
                        message += f"\n⏱️ Тривалість відключення: {duration_str}"
            else:
                message = f"❌ Електрику вимкнено\n\n🕐 {timestamp_str}"
                # Add uptime duration if we know when power came on
                if prev_last_confirmed_online_ts is not None:
                    # Calculate duration from when power came on to when it went off
                    duration_seconds = prev_first_observed_change_ts - prev_last_confirmed_online_ts
                    if duration_seconds > 0:
                        duration_str = format_ukrainian_duration(duration_seconds)
                        message += f"\n⏱️ Електрика була: {duration_str}"

            try:
                notifier.send_message(message)
                notification_sent = True
                print(
                    json.dumps(
                        {
                            "event": "notification_sent",
                            "message": message,
                            "event_timestamp": timestamp_str,
                            "first_observed_at": prev_first_observed_change_ts,
                        }
                    )
                )
            except Exception as notif_error:
                print(
                    json.dumps(
                        {
                            "event": "notification_failed",
                            "error": str(notif_error),
                            "traceback": traceback.format_exc(),
                        }
                    )
                )
                # Mark notification failure but continue to save state
                new_state_dict["notify_failed"] = True

        # Step 5: Persist new state
        state_store.save_state(new_state_dict)
        print(json.dumps({"event": "state_saved", "state": new_state_dict}))

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "success": True,
                    "device_online": device_online,
                    "notification_sent": notification_sent,
                    "state": new_state_dict,
                }
            ),
        }

    except Exception as e:
        print(
            json.dumps(
                {"event": "unhandled_error", "error": str(e), "traceback": traceback.format_exc()}
            )
        )
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "internal_error", "message": str(e)}),
        }
