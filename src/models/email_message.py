from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class EmailAction(Enum):
    """Actions the user can take on a detected spam/marketing email."""
    NONE = "none"
    DELETE = "delete"
    BLOCK = "block"
    UNSUBSCRIBE = "unsubscribe"


@dataclass
class EmailMessage:
    """Represents a single email message with metadata for spam detection."""

    id: str
    subject: str
    sender_name: str
    sender_email: str
    date: datetime | None
    snippet: str = ""
    body_text: str = ""
    body_html: str = ""
    list_unsubscribe: str = ""
    has_unsubscribe_link: bool = False
    unsubscribe_url: str = ""
    spam_score: float = 0.0
    provider: str = ""

    action: EmailAction = field(default=EmailAction.NONE)

    def __str__(self) -> str:
        return f"[{self.sender_email}] {self.subject}"


@dataclass
class SenderGroup:
    """Groups emails by sender for easier user review."""

    sender_email: str
    sender_name: str
    email_count: int
    sample_subjects: list[str]
    avg_spam_score: float
    has_unsubscribe: bool
    unsubscribe_url: str
    action: EmailAction = field(default=EmailAction.NONE)
    message_ids: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"{self.sender_name} <{self.sender_email}> "
            f"({self.email_count} correos, score: {self.avg_spam_score:.1f})"
        )

    @property
    def display_name(self) -> str:
        """Human-readable sender name, falling back to the email address."""
        return self.sender_name or self.sender_email
