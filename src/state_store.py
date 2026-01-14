"""
DynamoDB state storage for power monitor.
Persists debounce state across Lambda invocations.
"""

import boto3
from typing import Dict, Any
from decimal import Decimal


class StateStore:
    """DynamoDB-backed state persistence."""
    
    STATE_PK = "state"
    
    def __init__(self, table_name: str):
        """
        Initialize state store.
        
        Args:
            table_name: DynamoDB table name
        """
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)
    
    def load_state(self) -> Dict[str, Any]:
        """
        Load state from DynamoDB.
        
        Returns:
            State dictionary with default values if not found
        """
        try:
            response = self.table.get_item(Key={"pk": self.STATE_PK})
            
            if "Item" in response:
                item = response["Item"]
                # Convert DynamoDB types to Python types
                return self._deserialize_item(item)
            else:
                # Return default state if not found
                return self._default_state()
        except Exception as e:
            print(f"Error loading state from DynamoDB: {e}")
            # Return default state on error
            return self._default_state()
    
    def save_state(self, state: Dict[str, Any]) -> None:
        """
        Save state to DynamoDB.
        
        Args:
            state: State dictionary to persist
        """
        item = {"pk": self.STATE_PK, **state}
        # Convert floats to Decimal for DynamoDB
        item = self._serialize_item(item)
        self.table.put_item(Item=item)
    
    @staticmethod
    def _default_state() -> Dict[str, Any]:
        """Return default initial state."""
        return {
            "last_confirmed_online": None,
            "last_observed_online": None,
            "streak": 0,
            "last_change_ts": None,
            "last_message_ts": None
        }
    
    @staticmethod
    def _serialize_item(item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Python types to DynamoDB types."""
        serialized = {}
        for key, value in item.items():
            if isinstance(value, float):
                serialized[key] = Decimal(str(value))
            elif isinstance(value, dict):
                serialized[key] = StateStore._serialize_item(value)
            else:
                serialized[key] = value
        return serialized
    
    @staticmethod
    def _deserialize_item(item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DynamoDB types to Python types."""
        deserialized = {}
        for key, value in item.items():
            if key == "pk":
                continue  # Skip partition key
            elif isinstance(value, Decimal):
                # Convert Decimal to int or float
                deserialized[key] = int(value) if value % 1 == 0 else float(value)
            elif isinstance(value, dict):
                deserialized[key] = StateStore._deserialize_item(value)
            else:
                deserialized[key] = value
        return deserialized
