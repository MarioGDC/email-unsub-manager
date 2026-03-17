from abc import ABC, abstractmethod
from src.models.email_message import EmailMessage


class BaseEmailProvider(ABC):
    """Abstract base class for email providers (Gmail, Outlook, etc.)."""

    @abstractmethod
    def authenticate(self) -> bool:
        ...

    @abstractmethod
    def fetch_emails(self, max_results: int = 500) -> list[EmailMessage]:
        ...

    @abstractmethod
    def delete_emails(self, message_ids: list[str]) -> bool:
        ...

    @abstractmethod
    def block_sender(self, sender_email: str) -> bool:
        ...

    @abstractmethod
    def get_provider_name(self) -> str:
        ...
