from __future__ import annotations

from collections import defaultdict

from config.settings import settings
from src.models.email_message import EmailMessage, SenderGroup


class SpamDetector:
    """Analyses a list of EmailMessage objects and assigns spam scores."""

    # Score weights
    _KEYWORD_SCORE = 1.0
    _SENDER_PATTERN_SCORE = 2.0
    _LIST_UNSUBSCRIBE_SCORE = 3.0
    _THRESHOLD = 3.0  # Minimum score to consider an email as spam/marketing

    def analyse(self, emails: list[EmailMessage]) -> list[EmailMessage]:
        """Assign a spam_score to every email and return those above the threshold."""
        scored: list[EmailMessage] = []
        for email in emails:
            email.spam_score = self._score(email)
            if email.spam_score >= self._THRESHOLD:
                scored.append(email)
        return scored

    def _score(self, email: EmailMessage) -> float:
        """Calculate a numeric spam/marketing score for an email."""
        score = 0.0
        searchable = " ".join([
            email.subject,
            email.snippet,
            email.body_text,
            email.list_unsubscribe,
        ]).lower()

        # Keyword matching in content
        for keyword in settings.SPAM_KEYWORDS:
            if keyword.lower() in searchable:
                score += self._KEYWORD_SCORE

        # Known spam sender pattern
        sender = email.sender_email.lower()
        for pattern in settings.SPAM_SENDER_PATTERNS:
            if sender.startswith(pattern) or pattern in sender:
                score += self._SENDER_PATTERN_SCORE
                break  # Only count once

        # Presence of List-Unsubscribe header is a strong signal
        if email.list_unsubscribe:
            score += self._LIST_UNSUBSCRIBE_SCORE

        return score

    # ------------------------------------------------------------------
    # Grouping helpers
    # ------------------------------------------------------------------

    @staticmethod
    def group_by_sender(emails: list[EmailMessage]) -> list[SenderGroup]:
        """Group scored emails by sender email address."""
        grouped: dict[str, list[EmailMessage]] = defaultdict(list)
        for email in emails:
            grouped[email.sender_email].append(email)

        groups: list[SenderGroup] = []
        for sender_email, msgs in grouped.items():
            avg_score = sum(m.spam_score for m in msgs) / len(msgs)
            sample_subjects = [m.subject for m in msgs[:3]]
            has_unsubscribe = any(m.has_unsubscribe_link or bool(m.list_unsubscribe) for m in msgs)
            unsubscribe_url = next(
                (m.unsubscribe_url for m in msgs if m.unsubscribe_url), ""
            )
            groups.append(
                SenderGroup(
                    sender_email=sender_email,
                    sender_name=msgs[0].sender_name,
                    email_count=len(msgs),
                    sample_subjects=sample_subjects,
                    avg_spam_score=avg_score,
                    has_unsubscribe=has_unsubscribe,
                    unsubscribe_url=unsubscribe_url,
                    message_ids=[m.id for m in msgs],
                )
            )

        # Sort by average spam score descending
        return sorted(groups, key=lambda g: g.avg_spam_score, reverse=True)
