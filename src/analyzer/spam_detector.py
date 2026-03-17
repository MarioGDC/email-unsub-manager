from bs4 import BeautifulSoup

from src.models.email_message import EmailMessage, SenderGroup
from config.settings import settings


class SpamDetector:
    """Analyzes emails and assigns spam/marketing scores."""

    def analyze(self, emails: list[EmailMessage]) -> list[EmailMessage]:
        """Assign a spam_score to each email and return the list."""
        for email_msg in emails:
            email_msg.spam_score = self._score(email_msg)
        return emails

    def _score(self, email_msg: EmailMessage) -> float:
        """Calculate a spam score 0-100 for an email."""
        score = 0.0

        # List-Unsubscribe header present
        if email_msg.list_unsubscribe:
            score += 30

        # Sender matches known spam patterns
        sender_lower = email_msg.sender_email.lower()
        for pattern in settings.SPAM_SENDER_PATTERNS:
            if sender_lower.startswith(pattern) or pattern in sender_lower:
                score += 15
                break

        # Keywords in subject
        subject_lower = email_msg.subject.lower()
        for keyword in settings.SPAM_KEYWORDS:
            if keyword.lower() in subject_lower:
                score += 5

        # Keywords in body text
        body_lower = (email_msg.body_text or "").lower()
        for keyword in settings.SPAM_KEYWORDS:
            if keyword.lower() in body_lower:
                score += 3

        # Unsubscribe links in HTML body
        if email_msg.body_html:
            unsub_count = self._count_unsubscribe_links(email_msg.body_html)
            if unsub_count > 0:
                score += 20

            # Tracking pixels
            if self._has_tracking_pixel(email_msg.body_html):
                score += 10

        # Normalize to 0-100
        return min(score, 100.0)

    @staticmethod
    def _count_unsubscribe_links(html: str) -> int:
        """Count links containing unsubscribe-related text in HTML."""
        try:
            soup = BeautifulSoup(html, "html.parser")
            count = 0
            unsub_terms = ["unsubscribe", "darse de baja", "cancelar suscripción", "opt-out", "opt out"]
            for a_tag in soup.find_all("a", href=True):
                link_text = (a_tag.get_text() or "").lower()
                href = (a_tag.get("href") or "").lower()
                if any(term in link_text or term in href for term in unsub_terms):
                    count += 1
            return count
        except Exception:
            return 0

    @staticmethod
    def _has_tracking_pixel(html: str) -> bool:
        """Detect 1x1 tracking pixels in HTML."""
        try:
            soup = BeautifulSoup(html, "html.parser")
            for img in soup.find_all("img"):
                width = img.get("width", "")
                height = img.get("height", "")
                if str(width) == "1" and str(height) == "1":
                    return True
            return False
        except Exception:
            return False

    @staticmethod
    def group_by_sender(
        emails: list[EmailMessage], min_score: float = 15.0
    ) -> list[SenderGroup]:
        """Group emails by sender, filtering by minimum spam score."""
        groups: dict[str, SenderGroup] = {}

        for email_msg in emails:
            if email_msg.spam_score < min_score:
                continue
            key = email_msg.sender_email.lower()
            if key not in groups:
                groups[key] = SenderGroup(
                    sender_email=email_msg.sender_email,
                    sender_name=email_msg.sender_name,
                )
            groups[key].emails.append(email_msg)

        # Compute average score per group
        result = []
        for group in groups.values():
            if group.emails:
                group.avg_spam_score = sum(e.spam_score for e in group.emails) / len(group.emails)
            result.append(group)

        # Sort by average spam score descending
        result.sort(key=lambda g: g.avg_spam_score, reverse=True)
        return result
