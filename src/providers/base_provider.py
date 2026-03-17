from abc import ABC, abstractmethod

from src.models.email_message import EmailMessage


class BaseEmailProvider(ABC):
    """Abstract base class for email providers."""

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the email service. Returns True on success."""

    @abstractmethod
    def fetch_emails(self, max_results: int = 500) -> list[EmailMessage]:
        """Fetch emails from the inbox."""

    @abstractmethod
    def delete_emails(self, message_ids: list[str]) -> bool:
        """Delete emails by their IDs. Returns True on success."""

    @abstractmethod
    def block_sender(self, sender_email: str) -> bool:
        """Block a sender. Returns True if supported and successful."""

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return a human-readable name for this provider."""
