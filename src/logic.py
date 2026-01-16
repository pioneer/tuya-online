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
        pending_change_since: Unix timestamp when potential state change was first detected
                             (debounce threshold reached but waiting for confirmation delay)
        first_observed_change_ts: Unix timestamp when the current observation streak started
                                  (when we first saw the new state, for notification timestamp)
    """

    last_confirmed_online: Optional[bool] = None
    last_observed_online: Optional[bool] = None
    streak: int = 0
    last_change_ts: Optional[float] = None
    last_message_ts: Optional[float] = None
    pending_change_since: Optional[float] = None  # for confirmation delay
    first_observed_change_ts: Optional[float] = None  # when the change was FIRST observed

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return asdict(self)


def process_state_change(
    prev_state: DebounceState,
    current_online: bool,
    debounce_threshold: int,
    confirmation_delay_seconds: int = 0,
) -> Tuple[DebounceState, bool]:
    """
    Process a new online status reading and determine if notification should be sent.

    Two-phase debouncing logic:
    Phase 1 (debounce): Wait for N consecutive polls showing the same state
    Phase 2 (confirmation): After debounce threshold reached, wait M more seconds
                           before confirming. If state reverts during this window,
                           cancel the pending change (prevents false positives).

    This handles transient API glitches where Tuya might report offline for ~3 minutes
    then recover - a real outage would persist beyond the confirmation delay.

    Args:
        prev_state: Previous debounce state
        current_online: Current device online status
        debounce_threshold: Number of consecutive readings required to start confirmation
        confirmation_delay_seconds: Additional seconds to wait after debounce before notifying

    Returns:
        Tuple of (new_state, should_notify)
    """
    now = time.time()

    new_state = DebounceState(
        last_confirmed_online=prev_state.last_confirmed_online,
        last_observed_online=prev_state.last_observed_online,
        streak=prev_state.streak,
        last_change_ts=prev_state.last_change_ts,
        last_message_ts=prev_state.last_message_ts,
        pending_change_since=prev_state.pending_change_since,
        first_observed_change_ts=prev_state.first_observed_change_ts,
    )

    # Update observation and streak
    if current_online == prev_state.last_observed_online:
        # Same observation, increment streak (cap at threshold + 1 to avoid overflow)
        new_state.streak = min(prev_state.streak + 1, debounce_threshold + 1)
    else:
        # Different observation, reset
        new_state.last_observed_online = current_online
        new_state.streak = 1
        # Record when we FIRST observed this new state (for notification timestamp)
        new_state.first_observed_change_ts = now
        # If we had a pending change and the state reverted, cancel it
        if prev_state.pending_change_since is not None:
            new_state.pending_change_since = None

    # Check if we should confirm a state change
    should_notify = False

    # State change detection logic (only if we have a confirmed state to compare with)
    if (
        new_state.last_confirmed_online is not None
        and new_state.last_observed_online != new_state.last_confirmed_online
        and new_state.streak >= debounce_threshold
    ):
        # Debounce threshold reached - is this a new detection or continuation?
        if new_state.pending_change_since is None:
            # New potential state change detected - start confirmation timer
            new_state.pending_change_since = now

        # Check if confirmation delay has passed
        elapsed = now - new_state.pending_change_since
        if elapsed >= confirmation_delay_seconds:
            # Confirmation delay passed - state change confirmed!
            new_state.last_confirmed_online = new_state.last_observed_online
            new_state.last_change_ts = now
            new_state.last_message_ts = now
            new_state.pending_change_since = None  # Clear pending
            should_notify = True

    # Handle initial state (first time we have data)
    elif new_state.last_confirmed_online is None and new_state.streak >= debounce_threshold:
        # Initial state confirmed (no delay needed for initial state)
        new_state.last_confirmed_online = new_state.last_observed_online
        new_state.last_change_ts = now
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
    confirmed = (
        "ON"
        if state.last_confirmed_online
        else "OFF"
        if state.last_confirmed_online is not None
        else "UNKNOWN"
    )
    observed = (
        "ON"
        if state.last_observed_online
        else "OFF"
        if state.last_observed_online is not None
        else "UNKNOWN"
    )

    return f"Confirmed: {confirmed}, Observed: {observed}, Streak: {state.streak}"
