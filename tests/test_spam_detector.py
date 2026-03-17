"""Tests for the SpamDetector analyzer."""
from __future__ import annotations

from datetime import datetime

import pytest

from src.analyzer.spam_detector import SpamDetector
from src.models.email_message import EmailAction, EmailMessage, SenderGroup


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_email(
    *,
    id: str = "msg-1",
    subject: str = "Hello",
    sender_name: str = "Sender",
    sender_email: str = "sender@example.com",
    snippet: str = "",
    body_text: str = "",
    list_unsubscribe: str = "",
    has_unsubscribe_link: bool = False,
    unsubscribe_url: str = "",
) -> EmailMessage:
    return EmailMessage(
        id=id,
        subject=subject,
        sender_name=sender_name,
        sender_email=sender_email,
        date=datetime(2024, 1, 1),
        snippet=snippet,
        body_text=body_text,
        list_unsubscribe=list_unsubscribe,
        has_unsubscribe_link=has_unsubscribe_link,
        unsubscribe_url=unsubscribe_url,
    )


# ---------------------------------------------------------------------------
# SpamDetector._score
# ---------------------------------------------------------------------------

class TestSpamDetectorScore:
    def setup_method(self) -> None:
        self.detector = SpamDetector()

    def test_clean_email_score_is_zero(self) -> None:
        email = make_email(subject="Meeting tomorrow", body_text="Let's meet at 10am.")
        score = self.detector._score(email)
        assert score == 0.0

    def test_keyword_in_subject_increases_score(self) -> None:
        email = make_email(subject="Unsubscribe from our newsletter")
        score = self.detector._score(email)
        assert score > 0

    def test_keyword_in_body_increases_score(self) -> None:
        email = make_email(body_text="Click here to unsubscribe from future emails.")
        score = self.detector._score(email)
        assert score > 0

    def test_list_unsubscribe_header_adds_score(self) -> None:
        email = make_email(list_unsubscribe="<https://example.com/unsub>")
        score = self.detector._score(email)
        # LIST_UNSUBSCRIBE_SCORE = 3.0
        assert score >= 3.0

    def test_spam_sender_pattern_adds_score(self) -> None:
        email = make_email(sender_email="noreply@example.com")
        score = self.detector._score(email)
        # SENDER_PATTERN_SCORE = 2.0
        assert score >= 2.0

    def test_multiple_signals_accumulate(self) -> None:
        email = make_email(
            subject="Special offer! Discount inside",
            sender_email="marketing@shop.com",
            list_unsubscribe="<https://shop.com/unsub>",
        )
        score = self.detector._score(email)
        # keyword + sender pattern + list-unsubscribe
        assert score >= 6.0

    def test_spanish_keyword_detected(self) -> None:
        email = make_email(snippet="Para darse de baja, haz clic aquí.")
        score = self.detector._score(email)
        assert score > 0


# ---------------------------------------------------------------------------
# SpamDetector.analyse
# ---------------------------------------------------------------------------

class TestSpamDetectorAnalyse:
    def setup_method(self) -> None:
        self.detector = SpamDetector()

    def test_analyse_returns_only_spam_emails(self) -> None:
        clean = make_email(id="clean", subject="Hello friend")
        spam = make_email(
            id="spam",
            sender_email="noreply@deals.com",
            list_unsubscribe="<https://deals.com/unsub>",
        )
        result = self.detector.analyse([clean, spam])
        ids = [e.id for e in result]
        assert "spam" in ids
        assert "clean" not in ids

    def test_analyse_assigns_spam_score(self) -> None:
        spam = make_email(
            id="s1",
            sender_email="newsletter@news.com",
            list_unsubscribe="<https://news.com/unsub>",
        )
        result = self.detector.analyse([spam])
        assert result[0].spam_score >= 3.0

    def test_analyse_empty_list(self) -> None:
        assert self.detector.analyse([]) == []

    def test_analyse_all_clean_returns_empty(self) -> None:
        emails = [make_email(id=f"c{i}", subject="Plain text") for i in range(5)]
        result = self.detector.analyse(emails)
        assert result == []


# ---------------------------------------------------------------------------
# SpamDetector.group_by_sender
# ---------------------------------------------------------------------------

class TestGroupBySender:
    def setup_method(self) -> None:
        self.detector = SpamDetector()

    def test_groups_same_sender_together(self) -> None:
        emails = [
            make_email(id="1", sender_email="promo@shop.com", subject="Deal 1", list_unsubscribe="<https://x.com>"),
            make_email(id="2", sender_email="promo@shop.com", subject="Deal 2", list_unsubscribe="<https://x.com>"),
        ]
        scored = self.detector.analyse(emails)
        groups = self.detector.group_by_sender(scored)
        assert len(groups) == 1
        assert groups[0].email_count == 2
        assert groups[0].sender_email == "promo@shop.com"

    def test_groups_different_senders_separately(self) -> None:
        emails = [
            make_email(id="1", sender_email="a@shop.com", list_unsubscribe="<https://a.com>"),
            make_email(id="2", sender_email="b@shop.com", list_unsubscribe="<https://b.com>"),
        ]
        scored = self.detector.analyse(emails)
        groups = self.detector.group_by_sender(scored)
        assert len(groups) == 2

    def test_groups_sorted_by_avg_score_descending(self) -> None:
        # First sender has only list-unsubscribe (score 3), second has more signals
        high = make_email(
            id="h",
            sender_email="noreply@deals.com",
            list_unsubscribe="<https://deals.com>",
            subject="Offer discount",
        )
        low = make_email(
            id="l",
            sender_email="friend@personal.com",
            list_unsubscribe="<https://personal.com>",
        )
        scored = self.detector.analyse([high, low])
        groups = self.detector.group_by_sender(scored)
        # Both are spam, but high should have higher score
        assert groups[0].avg_spam_score >= groups[-1].avg_spam_score

    def test_group_message_ids_collected(self) -> None:
        emails = [
            make_email(id="id1", sender_email="promo@x.com", list_unsubscribe="<https://x.com>"),
            make_email(id="id2", sender_email="promo@x.com", list_unsubscribe="<https://x.com>"),
        ]
        scored = self.detector.analyse(emails)
        groups = self.detector.group_by_sender(scored)
        assert set(groups[0].message_ids) == {"id1", "id2"}

    def test_has_unsubscribe_set_when_any_email_has_link(self) -> None:
        emails = [
            make_email(id="1", sender_email="news@x.com", list_unsubscribe="<https://x.com>"),
            make_email(id="2", sender_email="news@x.com", list_unsubscribe="<https://x.com>"),
        ]
        scored = self.detector.analyse(emails)
        groups = self.detector.group_by_sender(scored)
        assert groups[0].has_unsubscribe is True


# ---------------------------------------------------------------------------
# EmailMessage dataclass
# ---------------------------------------------------------------------------

class TestEmailMessage:
    def test_str_representation(self) -> None:
        email = make_email(sender_email="test@ex.com", subject="Hi there")
        assert "test@ex.com" in str(email)
        assert "Hi there" in str(email)

    def test_default_action_is_none(self) -> None:
        email = make_email()
        assert email.action == EmailAction.NONE

    def test_default_spam_score_is_zero(self) -> None:
        email = make_email()
        assert email.spam_score == 0.0


# ---------------------------------------------------------------------------
# SenderGroup dataclass
# ---------------------------------------------------------------------------

class TestSenderGroup:
    def test_str_representation(self) -> None:
        group = SenderGroup(
            sender_email="promo@shop.com",
            sender_name="Shop Promos",
            email_count=5,
            sample_subjects=["Sale!", "Deal"],
            avg_spam_score=7.5,
            has_unsubscribe=True,
            unsubscribe_url="https://shop.com/unsub",
        )
        s = str(group)
        assert "Shop Promos" in s
        assert "promo@shop.com" in s
        assert "5" in s
