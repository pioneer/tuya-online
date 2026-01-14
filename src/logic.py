"""
Core state transition and debouncing logic.
Pure functions for testability.
"""

import time
from dataclasses import dataclass, asdict
from typing import Optional, Tuple


@dataclass
class DebounceState:
    """
    State structure for debouncing logic.
    
    Attributes:
        last_confirmed_online: Last confirmed power state (True=on, False=off, None=unknown)
        last_observed_online: Most recent observed power state
        streak: Number of consecutive polls showing last_observed_online
        last_change_ts: Unix timestamp of last confirmed state change
        last_message_ts: Unix timestamp of last notification sent
    """
    last_confirmed_online: Optional[bool] = None
    last_observed_online: Optional[bool] = None
    streak: int = 0
    last_change_ts: Optional[float] = None
    last_message_ts: Optional[float] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return asdict(self)


def process_state_change(
    prev_state: DebounceState,
    current_online: bool,
    debounce_threshold: int
) -> Tuple[DebounceState, bool]:
    """
    Process a new online status reading and determine if notification should be sent.
    
    Debouncing logic:
    - If current reading matches last_observed: increment streak
    - If current reading differs from last_observed: reset to new observation with streak=1
    - Confirm state change when:
      1. We have a previous confirmed state
      2. Observed state differs from confirmed state
      3. Streak >= debounce_threshold
    
    Args:
        prev_state: Previous debounce state
        current_online: Current device online status
        debounce_threshold: Number of consecutive readings required to confirm change
        
    Returns:
        Tuple of (new_state, should_notify)
    """
    new_state = DebounceState(
        last_confirmed_online=prev_state.last_confirmed_online,
        last_observed_online=prev_state.last_observed_online,
        streak=prev_state.streak,
        last_change_ts=prev_state.last_change_ts,
        last_message_ts=prev_state.last_message_ts
    )
    
    # Update observation and streak
    if current_online == prev_state.last_observed_online:
        # Same observation, increment streak (cap at threshold + 1 to avoid overflow)
        new_state.streak = min(prev_state.streak + 1, debounce_threshold + 1)
    else:
        # Different observation, reset
        new_state.last_observed_online = current_online
        new_state.streak = 1
    
    # Check if we should confirm a state change
    should_notify = False
    
    if (
        new_state.last_confirmed_online is not None and
        new_state.last_observed_online != new_state.last_confirmed_online and
        new_state.streak >= debounce_threshold
    ):
        # State change confirmed!
        new_state.last_confirmed_online = new_state.last_observed_online
        new_state.last_change_ts = time.time()
        new_state.last_message_ts = time.time()
        should_notify = True
    
    # Handle initial state (first time we have data)
    elif new_state.last_confirmed_online is None and new_state.streak >= debounce_threshold:
        # Initial state confirmed
        new_state.last_confirmed_online = new_state.last_observed_online
        new_state.last_change_ts = time.time()
        # Don't notify on initial state establishment
        should_notify = False
    
    return new_state, should_notify


def format_state_summary(state: DebounceState) -> str:
    """
    Format state for human-readable logging.
    
    Args:
        state: Current debounce state
        
    Returns:
        Formatted string
    """
    confirmed = "ON" if state.last_confirmed_online else "OFF" if state.last_confirmed_online is not None else "UNKNOWN"
    observed = "ON" if state.last_observed_online else "OFF" if state.last_observed_online is not None else "UNKNOWN"
    
    return (
        f"Confirmed: {confirmed}, "
        f"Observed: {observed}, "
        f"Streak: {state.streak}"
    )
