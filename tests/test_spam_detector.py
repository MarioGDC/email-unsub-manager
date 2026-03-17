"""Tests for the SpamDetector analyzer."""
from datetime import datetime

import pytest

from src.models.email_message import EmailMessage, EmailAction
from src.analyzer.spam_detector import SpamDetector


def _make_email(
    id: str = "1",
    subject: str = "",
    sender_email: str = "sender@example.com",
    sender_name: str = "Sender",
    body_text: str = "",
    body_html: str = "",
    list_unsubscribe: str = "",
    spam_score: float = 0.0,
) -> EmailMessage:
    return EmailMessage(
        id=id,
        subject=subject,
        sender_name=sender_name,
        sender_email=sender_email,
        date=datetime(2024, 1, 1),
        snippet=body_text[:200],
        body_text=body_text,
        body_html=body_html,
        list_unsubscribe=list_unsubscribe,
        provider="imap",
        spam_score=spam_score,
    )


class TestSpamDetectorScoring:
    def setup_method(self):
        self.detector = SpamDetector()

    def test_clean_email_scores_zero(self):
        email_msg = _make_email(subject="Meeting tomorrow", sender_email="boss@company.com")
        result = self.detector.analyze([email_msg])
        assert result[0].spam_score == 0.0

    def test_list_unsubscribe_header_adds_score(self):
        email_msg = _make_email(list_unsubscribe="<https://example.com/unsub>")
        result = self.detector.analyze([email_msg])
        assert result[0].spam_score >= 30

    def test_noreply_sender_adds_score(self):
        email_msg = _make_email(sender_email="noreply@newsletter.com")
        result = self.detector.analyze([email_msg])
        assert result[0].spam_score >= 15

    def test_newsletter_sender_adds_score(self):
        email_msg = _make_email(sender_email="newsletter@company.com")
        result = self.detector.analyze([email_msg])
        assert result[0].spam_score >= 15

    def test_spam_keyword_in_subject_adds_score(self):
        email_msg = _make_email(subject="Unsubscribe from our newsletter")
        result = self.detector.analyze([email_msg])
        assert result[0].spam_score >= 5

    def test_multiple_keywords_in_subject(self):
        email_msg = _make_email(subject="Newsletter: special offer and discount")
        result = self.detector.analyze([email_msg])
        # newsletter, offer, discount → 3 keywords × 5 = 15
        assert result[0].spam_score >= 15

    def test_keyword_in_body_adds_score(self):
        email_msg = _make_email(body_text="Click here to unsubscribe from our mailing list.")
        result = self.detector.analyze([email_msg])
        assert result[0].spam_score >= 3

    def test_unsubscribe_link_in_html_adds_score(self):
        html = '<a href="https://example.com/unsubscribe">Unsubscribe</a>'
        email_msg = _make_email(body_html=html)
        result = self.detector.analyze([email_msg])
        assert result[0].spam_score >= 20

    def test_tracking_pixel_adds_score(self):
        html = '<img src="https://track.example.com/pixel.gif" width="1" height="1" />'
        email_msg = _make_email(body_html=html)
        result = self.detector.analyze([email_msg])
        assert result[0].spam_score >= 10

    def test_score_capped_at_100(self):
        html = (
            '<a href="https://example.com/unsubscribe">Unsubscribe</a>'
            '<img src="https://track.example.com/pixel.gif" width="1" height="1" />'
        )
        email_msg = _make_email(
            subject="Newsletter: unsubscribe offer discount sale promotional deal",
            sender_email="noreply@marketing.com",
            body_text="unsubscribe newsletter marketing opt-out discount sale",
            body_html=html,
            list_unsubscribe="<https://example.com/unsub>",
        )
        result = self.detector.analyze([email_msg])
        assert result[0].spam_score == 100.0

    def test_analyze_multiple_emails(self):
        emails = [
            _make_email(id="1", subject="Meeting"),
            _make_email(id="2", list_unsubscribe="<https://example.com/unsub>"),
            _make_email(id="3", sender_email="noreply@shop.com"),
        ]
        result = self.detector.analyze(emails)
        assert len(result) == 3
        assert result[0].spam_score == 0.0
        assert result[1].spam_score >= 30
        assert result[2].spam_score >= 15


class TestSpamDetectorGrouping:
    def setup_method(self):
        self.detector = SpamDetector()

    def test_group_by_sender_basic(self):
        emails = [
            _make_email(id="1", sender_email="news@example.com", spam_score=50.0),
            _make_email(id="2", sender_email="news@example.com", spam_score=60.0),
            _make_email(id="3", sender_email="other@example.com", spam_score=70.0),
        ]
        groups = self.detector.group_by_sender(emails, min_score=15.0)
        assert len(groups) == 2
        emails_per_group = {g.sender_email: g.email_count for g in groups}
        assert emails_per_group["news@example.com"] == 2
        assert emails_per_group["other@example.com"] == 1

    def test_group_filters_by_min_score(self):
        emails = [
            _make_email(id="1", sender_email="low@example.com", spam_score=5.0),
            _make_email(id="2", sender_email="high@example.com", spam_score=50.0),
        ]
        groups = self.detector.group_by_sender(emails, min_score=15.0)
        assert len(groups) == 1
        assert groups[0].sender_email == "high@example.com"

    def test_group_avg_score(self):
        emails = [
            _make_email(id="1", sender_email="news@example.com", spam_score=40.0),
            _make_email(id="2", sender_email="news@example.com", spam_score=60.0),
        ]
        groups = self.detector.group_by_sender(emails, min_score=15.0)
        assert len(groups) == 1
        assert groups[0].avg_spam_score == 50.0

    def test_group_sorted_by_score_descending(self):
        emails = [
            _make_email(id="1", sender_email="low@example.com", spam_score=20.0),
            _make_email(id="2", sender_email="high@example.com", spam_score=80.0),
            _make_email(id="3", sender_email="mid@example.com", spam_score=50.0),
        ]
        groups = self.detector.group_by_sender(emails, min_score=15.0)
        scores = [g.avg_spam_score for g in groups]
        assert scores == sorted(scores, reverse=True)

    def test_empty_list_returns_empty(self):
        groups = self.detector.group_by_sender([], min_score=15.0)
        assert groups == []
