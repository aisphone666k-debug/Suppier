from dataclasses import dataclass


class InvalidConfidenceScoreException(ValueError):
    """Raised when confidence score falls outside [0.0, 1.0]."""
    pass


@dataclass(frozen=True)
class ConfidenceScore:
    value: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.value <= 1.0):
            raise InvalidConfidenceScoreException(
                f"Confidence score ({self.value}) must be between 0.0 and 1.0"
            )

    def as_percentage(self, decimals: int = 1) -> str:
        return f"{self.value * 100:.{decimals}f}%"

    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        return self.value >= threshold

    def is_acceptable(self, threshold: float = 0.35) -> bool:
        return self.value >= threshold
