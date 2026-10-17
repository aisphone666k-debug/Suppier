import pytest
from src.domain.confidence_score import ConfidenceScore, InvalidConfidenceScoreException


def test_confidence_score_valid_bounds():
    score = ConfidenceScore(0.85)
    assert score.value == 0.85
    assert score.as_percentage() == "85.0%"
    assert score.is_high_confidence() is True
    assert score.is_acceptable() is True


def test_confidence_score_edge_bounds_zero_and_one():
    zero = ConfidenceScore(0.0)
    one = ConfidenceScore(1.0)
    assert zero.value == 0.0
    assert zero.as_percentage() == "0.0%"
    assert zero.is_acceptable() is False
    assert one.value == 1.0
    assert one.as_percentage() == "100.0%"
    assert one.is_high_confidence() is True


def test_confidence_score_rejects_negative_value():
    with pytest.raises(InvalidConfidenceScoreException) as excinfo:
        ConfidenceScore(-0.01)
    assert "must be between 0.0 and 1.0" in str(excinfo.value)


def test_confidence_score_rejects_value_greater_than_one():
    with pytest.raises(InvalidConfidenceScoreException) as excinfo:
        ConfidenceScore(1.001)
    assert "must be between 0.0 and 1.0" in str(excinfo.value)
