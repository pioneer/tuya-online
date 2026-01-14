"""
Unit tests for debouncing and state transition logic.
Run with: pytest tests/test_logic.py
"""

import pytest
from src.logic import DebounceState, process_state_change


class TestDebounceLogic:
    """Test suite for debouncing logic."""
    
    def test_initial_state_establishment(self):
        """Test that initial state requires debounce_threshold readings."""
        # Start with unknown state
        state = DebounceState()
        
        # First reading: online=True
        new_state, should_notify = process_state_change(state, True, debounce_threshold=2)
        assert new_state.last_observed_online is True
        assert new_state.streak == 1
        assert new_state.last_confirmed_online is None
        assert should_notify is False
        
        # Second reading: still True, should confirm
        new_state, should_notify = process_state_change(new_state, True, debounce_threshold=2)
        assert new_state.last_observed_online is True
        assert new_state.streak == 2
        assert new_state.last_confirmed_online is True
        assert should_notify is False  # Don't notify on initial state
    
    def test_state_change_requires_debounce(self):
        """Test that state changes require consecutive readings."""
        # Start with confirmed online state
        state = DebounceState(
            last_confirmed_online=True,
            last_observed_online=True,
            streak=2
        )
        
        # First offline reading
        new_state, should_notify = process_state_change(state, False, debounce_threshold=2)
        assert new_state.last_observed_online is False
        assert new_state.streak == 1
        assert new_state.last_confirmed_online is True  # Still confirmed online
        assert should_notify is False
        
        # Second offline reading, should confirm change
        new_state, should_notify = process_state_change(new_state, False, debounce_threshold=2)
        assert new_state.last_observed_online is False
        assert new_state.streak == 2
        assert new_state.last_confirmed_online is False  # Now confirmed offline
        assert should_notify is True
    
    def test_glitch_rejection(self):
        """Test that transient glitches don't trigger state changes."""
        # Start with confirmed online state
        state = DebounceState(
            last_confirmed_online=True,
            last_observed_online=True,
            streak=2
        )
        
        # Transient offline reading
        new_state, should_notify = process_state_change(state, False, debounce_threshold=2)
        assert new_state.streak == 1
        assert new_state.last_confirmed_online is True
        assert should_notify is False
        
        # Back online (glitch rejected)
        new_state, should_notify = process_state_change(new_state, True, debounce_threshold=2)
        assert new_state.last_observed_online is True
        assert new_state.streak == 1
        assert new_state.last_confirmed_online is True
        assert should_notify is False
        
        # Confirm still online
        new_state, should_notify = process_state_change(new_state, True, debounce_threshold=2)
        assert new_state.streak == 2
        assert new_state.last_confirmed_online is True
        assert should_notify is False  # No change, so no notification
    
    def test_streak_increments_correctly(self):
        """Test that streak increments with consecutive matching readings."""
        state = DebounceState(
            last_confirmed_online=True,
            last_observed_online=True,
            streak=2
        )
        
        # Multiple consecutive matching readings
        new_state, _ = process_state_change(state, True, debounce_threshold=2)
        assert new_state.streak == 3
        
        new_state, _ = process_state_change(new_state, True, debounce_threshold=2)
        assert new_state.streak == 3  # Capped at threshold + 1
    
    def test_streak_resets_on_observation_change(self):
        """Test that streak resets when observation changes."""
        state = DebounceState(
            last_confirmed_online=True,
            last_observed_online=True,
            streak=5
        )
        
        # Different observation resets streak
        new_state, should_notify = process_state_change(state, False, debounce_threshold=2)
        assert new_state.last_observed_online is False
        assert new_state.streak == 1
        assert should_notify is False
    
    def test_online_to_offline_transition(self):
        """Test complete online to offline transition."""
        # Start confirmed online
        state = DebounceState(
            last_confirmed_online=True,
            last_observed_online=True,
            streak=2
        )
        
        # Poll 1: offline
        state, notify = process_state_change(state, False, debounce_threshold=2)
        assert notify is False
        assert state.last_confirmed_online is True
        
        # Poll 2: offline (confirmed)
        state, notify = process_state_change(state, False, debounce_threshold=2)
        assert notify is True
        assert state.last_confirmed_online is False
        assert state.last_change_ts is not None
    
    def test_offline_to_online_transition(self):
        """Test complete offline to online transition."""
        # Start confirmed offline
        state = DebounceState(
            last_confirmed_online=False,
            last_observed_online=False,
            streak=2
        )
        
        # Poll 1: online
        state, notify = process_state_change(state, True, debounce_threshold=2)
        assert notify is False
        assert state.last_confirmed_online is False
        
        # Poll 2: online (confirmed)
        state, notify = process_state_change(state, True, debounce_threshold=2)
        assert notify is True
        assert state.last_confirmed_online is True
        assert state.last_change_ts is not None
    
    def test_higher_debounce_threshold(self):
        """Test with higher debounce threshold (N=3)."""
        state = DebounceState(
            last_confirmed_online=True,
            last_observed_online=True,
            streak=2
        )
        
        # Poll 1: offline
        state, notify = process_state_change(state, False, debounce_threshold=3)
        assert notify is False
        assert state.streak == 1
        
        # Poll 2: offline
        state, notify = process_state_change(state, False, debounce_threshold=3)
        assert notify is False
        assert state.streak == 2
        
        # Poll 3: offline (confirmed with N=3)
        state, notify = process_state_change(state, False, debounce_threshold=3)
        assert notify is True
        assert state.streak == 3
        assert state.last_confirmed_online is False
    
    def test_to_dict_serialization(self):
        """Test state serialization."""
        state = DebounceState(
            last_confirmed_online=True,
            last_observed_online=False,
            streak=1,
            last_change_ts=1234567890.0,
            last_message_ts=1234567890.0
        )
        
        state_dict = state.to_dict()
        assert state_dict["last_confirmed_online"] is True
        assert state_dict["last_observed_online"] is False
        assert state_dict["streak"] == 1
        assert state_dict["last_change_ts"] == 1234567890.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
