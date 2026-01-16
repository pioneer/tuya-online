"""
Tuya Cloud API client wrapper.
Handles authentication and device status queries.
"""

from typing import Dict, Any
from tuya_connector import TuyaOpenAPI


class TuyaClient:
    """Wrapper around Tuya OpenAPI for simplified device queries."""

    def __init__(self, endpoint: str, access_id: str, access_key: str):
        """
        Initialize Tuya client.

        Args:
            endpoint: Tuya API endpoint (e.g., https://openapi.tuyaeu.com)
            access_id: Tuya Access ID
            access_key: Tuya Access Key
        """
        self.api = TuyaOpenAPI(endpoint, access_id, access_key)
        self.api.connect()

    def get_device_online_status(self, device_id: str) -> bool:
        """
        Query device online status from Tuya Cloud.

        Args:
            device_id: Tuya device ID

        Returns:
            True if device is online, False otherwise

        Raises:
            Exception: If API call fails or response is invalid
        """
        response = self.api.get(f"/v1.0/devices/{device_id}")

        if not response.get("success"):
            error_msg = response.get("msg", "Unknown error")
            error_code = response.get("code", "unknown")
            raise Exception(f"Tuya API error: {error_code} - {error_msg}")

        result = response.get("result")
        if not result:
            raise Exception("Tuya API returned empty result")

        online = result.get("online")
        if online is None:
            raise Exception("Device online status not found in response")

        return bool(online)

    def get_device_details(self, device_id: str) -> Dict[str, Any]:
        """
        Get full device details from Tuya Cloud.

        Args:
            device_id: Tuya device ID

        Returns:
            Device details dictionary

        Raises:
            Exception: If API call fails
        """
        response = self.api.get(f"/v1.0/devices/{device_id}")

        if not response.get("success"):
            error_msg = response.get("msg", "Unknown error")
            error_code = response.get("code", "unknown")
            raise Exception(f"Tuya API error: {error_code} - {error_msg}")

        return response.get("result", {})
