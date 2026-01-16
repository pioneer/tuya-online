"""
Telegram notification sender.
Sends messages via Telegram Bot API.
"""

import requests
from typing import Dict, Any


class TelegramNotifier:
    """Send notifications via Telegram Bot API."""

    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize Telegram notifier.

        Args:
            bot_token: Telegram bot token
            chat_id: Telegram chat ID to send messages to
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    def send_message(self, text: str) -> Dict[str, Any]:
        """
        Send a text message via Telegram.

        Args:
            text: Message text to send

        Returns:
            Telegram API response

        Raises:
            Exception: If message sending fails
        """
        payload = {"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"}

        try:
            response = requests.post(self.api_url, json=payload, timeout=10)
            response.raise_for_status()

            result = response.json()
            if not result.get("ok"):
                raise Exception(f"Telegram API error: {result.get('description', 'Unknown error')}")

            return result

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to send Telegram message: {str(e)}")
