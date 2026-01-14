#!/usr/bin/env python3
"""
Local testing script for Tuya Power Monitor.
Tests Tuya API connection and Telegram notifications without AWS.

Usage:
    python scripts/test_local.py --test-tuya      # Test Tuya connection
    python scripts/test_local.py --test-telegram  # Test Telegram notification
    python scripts/test_local.py --test-all       # Test everything
    python scripts/test_local.py --poll           # Run a single poll (no DynamoDB)
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config_loader import load_config


def test_tuya_connection():
    """Test Tuya API connection and device status."""
    print("🔌 Testing Tuya API connection...")
    
    config = load_config(use_env=False)
    
    from tuya_client import TuyaClient
    
    try:
        client = TuyaClient(
            config.tuya.endpoint,
            config.tuya.access_id,
            config.tuya.access_key
        )
        
        print(f"  ✓ Connected to Tuya API ({config.tuya.endpoint})")
        
        # Get device status
        online = client.get_device_online_status(config.tuya.device_id)
        status = "🟢 ONLINE" if online else "🔴 OFFLINE"
        print(f"  ✓ Device {config.tuya.device_id}: {status}")
        
        # Get full device details
        details = client.get_device_details(config.tuya.device_id)
        print(f"  ✓ Device name: {details.get('name', 'N/A')}")
        print(f"  ✓ Device category: {details.get('category', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def format_ukrainian_timestamp(tz):
    """Format current time in Ukrainian."""
    from datetime import datetime
    
    months_uk = {
        1: "січня", 2: "лютого", 3: "березня", 4: "квітня",
        5: "травня", 6: "червня", 7: "липня", 8: "серпня",
        9: "вересня", 10: "жовтня", 11: "листопада", 12: "грудня"
    }
    
    now = datetime.now(tz)
    day = now.day
    month = months_uk[now.month]
    year = now.year
    time_str = now.strftime("%H:%M")
    
    return f"{day} {month} {year} о {time_str}"


def test_telegram_notification():
    """Test Telegram bot notification - sends all message types."""
    print("📱 Testing Telegram notifications...")
    
    config = load_config(use_env=False)
    
    from notifier import TelegramNotifier
    from zoneinfo import ZoneInfo
    import time
    
    try:
        notifier = TelegramNotifier(
            config.telegram.bot_token,
            config.telegram.chat_id
        )
        
        tz = ZoneInfo(config.timezone)
        timestamp = format_ukrainian_timestamp(tz)
        
        # Message 1: Power ON
        message_on = f"✅ Електрику увімкнено!\n\n🕐 {timestamp}"
        notifier.send_message(message_on)
        print(f"  ✓ Надіслано: Електрику увімкнено")
        
        time.sleep(1)  # Small delay between messages
        
        # Message 2: Power OFF
        message_off = f"❌ Електрику вимкнено\n\n🕐 {timestamp}"
        notifier.send_message(message_off)
        print(f"  ✓ Надіслано: Електрику вимкнено")
        
        time.sleep(1)
        
        # Message 3: Test/status message
        message_test = f"🧪 Тестове повідомлення\n\n🕐 {timestamp}\n\nМоніторинг електроживлення працює!"
        notifier.send_message(message_test)
        print(f"  ✓ Надіслано: Тестове повідомлення")
        
        print(f"\n  📨 Всього надіслано 3 повідомлення до чату {config.telegram.chat_id}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def run_single_poll():
    """Run a single poll without DynamoDB (uses in-memory state)."""
    print("🔄 Running single poll...")
    
    config = load_config(use_env=False)
    
    from tuya_client import TuyaClient
    from logic import DebounceState, process_state_change
    from datetime import datetime
    from zoneinfo import ZoneInfo
    
    try:
        # Query Tuya
        client = TuyaClient(
            config.tuya.endpoint,
            config.tuya.access_id,
            config.tuya.access_key
        )
        
        online = client.get_device_online_status(config.tuya.device_id)
        status = "ONLINE" if online else "OFFLINE"
        
        tz = ZoneInfo(config.timezone)
        timestamp = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S %Z")
        
        print(f"  📊 Device status: {status}")
        print(f"  🕐 Timestamp: {timestamp}")
        print(f"  ⚙️  Debounce threshold: {config.debounce_count}")
        
        # Simulate state processing
        initial_state = DebounceState()
        new_state, should_notify = process_state_change(
            initial_state, online, config.debounce_count
        )
        
        print(f"  📝 New state: observed={new_state.last_observed_online}, streak={new_state.streak}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test Tuya Power Monitor locally")
    parser.add_argument("--test-tuya", action="store_true", help="Test Tuya API connection")
    parser.add_argument("--test-telegram", action="store_true", help="Test Telegram notification")
    parser.add_argument("--test-all", action="store_true", help="Run all tests")
    parser.add_argument("--poll", action="store_true", help="Run a single poll")
    
    args = parser.parse_args()
    
    if not any([args.test_tuya, args.test_telegram, args.test_all, args.poll]):
        parser.print_help()
        sys.exit(1)
    
    print("=" * 50)
    print("Tuya Power Monitor - Local Test")
    print("=" * 50)
    print()
    
    results = []
    
    if args.test_all or args.test_tuya:
        results.append(("Tuya API", test_tuya_connection()))
        print()
    
    if args.test_all or args.test_telegram:
        results.append(("Telegram", test_telegram_notification()))
        print()
    
    if args.poll:
        results.append(("Poll", run_single_poll()))
        print()
    
    # Summary
    print("=" * 50)
    print("Results:")
    for name, passed in results:
        icon = "✅" if passed else "❌"
        print(f"  {icon} {name}")
    
    all_passed = all(r[1] for r in results)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
