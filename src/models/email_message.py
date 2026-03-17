from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class EmailAction(Enum):
    """Actions that can be taken on emails."""
    SKIP = "skip"
    DELETE = "delete"
    UNSUBSCRIBE = "unsubscribe"
    BLOCK = "block"


@dataclass
class EmailMessage:
    """Represents a single email message."""
    id: str
    subject: str
    sender_name: str
    sender_email: str
    date: datetime | None
    snippet: str
    body_text: str = ""
    body_html: str = ""
    list_unsubscribe: str = ""
    provider: str = ""
    spam_score: float = 0.0
    action: EmailAction = EmailAction.SKIP


@dataclass
class SenderGroup:
    """Groups emails by sender for bulk actions."""
    sender_email: str
    sender_name: str
    emails: list[EmailMessage] = field(default_factory=list)
    avg_spam_score: float = 0.0
    action: EmailAction = EmailAction.SKIP

    @property
    def email_count(self) -> int:
        return len(self.emails)

    @property
    def latest_email(self) -> EmailMessage | None:
        if not self.emails:
            return None
        dated = [e for e in self.emails if e.date is not None]
        if not dated:
            return self.emails[0]
        return max(dated, key=lambda e: e.date)
