from dataclasses import dataclass
from datetime import date


class InvalidValidityPeriodException(ValueError):
    """Raised when validity period violates temporal bounds."""
    pass


@dataclass(frozen=True)
class ValidityPeriod:
    issue_date: date
    expiration_date: date

    def __post_init__(self) -> None:
        if self.expiration_date < self.issue_date:
            raise InvalidValidityPeriodException(
                f"Expiration date ({self.expiration_date}) cannot precede issue date ({self.issue_date})"
            )

    def is_expired(self, reference_date: date) -> bool:
        """A quotation is expired strictly when reference_date > expiration_date."""
        return reference_date > self.expiration_date

    def days_remaining(self, reference_date: date) -> int:
        """Returns days until expiration relative to reference_date (negative if expired)."""
        return (self.expiration_date - reference_date).days
