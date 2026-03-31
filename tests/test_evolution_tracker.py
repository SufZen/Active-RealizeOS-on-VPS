"""Tests for realize_core.evolution.tracker -- satisfaction detection and interaction timer."""

from realize_core.evolution.tracker import detect_satisfaction_signal


class TestDetectSatisfactionSignal:
    # --- Negative signals ---
    def test_thats_wrong(self):
        result = detect_satisfaction_signal("No that's wrong, I needed the other one")
        assert result is not None
        signal, confidence = result
        assert signal == "correction"

    def test_incorrect(self):
        result = detect_satisfaction_signal("That answer is incorrect")
        assert result is not None
        assert result[0] == "correction"

    def test_try_again(self):
        result = detect_satisfaction_signal("Please try again with different parameters")
        assert result is not None
        assert result[0] == "correction"

    def test_you_misunderstood(self):
        result = detect_satisfaction_signal("You misunderstood my request")
        assert result is not None
        assert result[0] == "correction"

    # --- Retry signals ---
    def test_retry(self):
        result = detect_satisfaction_signal("Can you retry that?")
        assert result is not None
        assert result[0] == "retry"

    def test_let_me_rephrase(self):
        result = detect_satisfaction_signal("Let me rephrase my question")
        assert result is not None
        assert result[0] == "retry"

    # --- Positive signals ---
    def test_thanks(self):
        result = detect_satisfaction_signal("Thanks for helping!")
        assert result is not None
        assert result[0] == "positive"

    def test_perfect(self):
        result = detect_satisfaction_signal("Perfect, that's what I needed")
        assert result is not None
        assert result[0] == "positive"

    def test_exactly(self):
        result = detect_satisfaction_signal("Exactly what I was looking for")
        assert result is not None
        assert result[0] == "positive"

    # --- Negation detection (false positive prevention) ---
    def test_not_good_is_correction(self):
        """'not good' should be correction, not positive."""
        result = detect_satisfaction_signal("That's not good at all")
        assert result is not None
        assert result[0] == "correction"

    def test_no_thanks_is_correction(self):
        """'no thanks' should be correction, not positive."""
        result = detect_satisfaction_signal("No thanks, that's not helpful")
        assert result is not None
        assert result[0] == "correction"

    def test_not_perfect(self):
        """'not perfect' should be correction."""
        result = detect_satisfaction_signal("It's not perfect but close")
        assert result is not None
        assert result[0] == "correction"

    def test_doesnt_look_great(self):
        """'doesn't look great' should be correction."""
        result = detect_satisfaction_signal("This doesn't look great")
        assert result is not None
        assert result[0] == "correction"

    # --- No signal ---
    def test_neutral_message(self):
        result = detect_satisfaction_signal("What time is the meeting tomorrow?")
        assert result is None

    def test_empty_message(self):
        result = detect_satisfaction_signal("")
        assert result is None

    # --- Word boundary tests ---
    def test_again_in_word_no_false_positive(self):
        """'once again thank you' — 'again' is a retry signal but 'thank' is positive.
        Since retry signals are checked before positive, this should be retry.
        But 'once again thank you' is actually positive intent — the regex should
        match 'retry' first since it's checked first."""
        result = detect_satisfaction_signal("once again thank you for the help")
        # 'retry' is checked before positive, but 'again' alone is not in RETRY_SIGNALS
        # (we removed bare "again" from RETRY_SIGNALS to reduce false positives)
        assert result is not None
        # Should match "thanks" as positive
        assert result[0] == "positive"

    # --- Confidence values ---
    def test_negative_has_high_confidence(self):
        result = detect_satisfaction_signal("That's not right")
        assert result is not None
        _, confidence = result
        assert confidence >= 0.8

    def test_positive_has_moderate_confidence(self):
        result = detect_satisfaction_signal("Great work!")
        assert result is not None
        _, confidence = result
        assert 0.5 <= confidence <= 0.8
