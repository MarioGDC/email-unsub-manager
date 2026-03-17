"""Tests for the ImapProvider."""
from __future__ import annotations

import email
import imaplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from unittest.mock import MagicMock, patch

import pytest

from src.providers.imap_provider import ImapProvider, _detect_imap_server


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_raw_email(
    subject: str = "Test Subject",
    from_addr: str = "Sender Name <sender@example.com>",
    date_str: str = "Mon, 1 Jan 2024 12:00:00 +0000",
    body_text: str = "Hello world",
    body_html: str = "",
    list_unsubscribe: str = "",
) -> bytes:
    """Build a raw RFC 2822 email message as bytes."""
    if body_html:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))
    else:
        msg = MIMEText(body_text, "plain")  # type: ignore[assignment]

    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["Date"] = date_str
    if list_unsubscribe:
        msg["List-Unsubscribe"] = list_unsubscribe

    return msg.as_bytes()


def _make_provider(**kwargs) -> ImapProvider:
    """Create an ImapProvider without loading settings from .env."""
    defaults = {
        "email_address": "test@outlook.com",
        "password": "secret",
        "imap_server": "outlook.office365.com",
        "imap_port": 993,
    }
    defaults.update(kwargs)
    with patch("src.providers.imap_provider.ImapProvider.__init__", lambda self, **kw: None):
        provider = ImapProvider.__new__(ImapProvider)
    provider._email = defaults["email_address"]
    provider._password = defaults["password"]
    provider._server = defaults["imap_server"]
    provider._port = defaults["imap_port"]
    provider._conn = None
    return provider


# ---------------------------------------------------------------------------
# _detect_imap_server
# ---------------------------------------------------------------------------

class TestDetectImapServer:
    def test_outlook_domain(self) -> None:
        assert _detect_imap_server("user@outlook.com") == "outlook.office365.com"

    def test_hotmail_domain(self) -> None:
        assert _detect_imap_server("user@hotmail.com") == "outlook.office365.com"

    def test_live_domain(self) -> None:
        assert _detect_imap_server("user@live.com") == "outlook.office365.com"

    def test_gmail_domain(self) -> None:
        assert _detect_imap_server("user@gmail.com") == "imap.gmail.com"

    def test_yahoo_domain(self) -> None:
        assert _detect_imap_server("user@yahoo.com") == "imap.mail.yahoo.com"

    def test_unknown_domain_returns_empty(self) -> None:
        assert _detect_imap_server("user@customdomain.org") == ""

    def test_no_at_sign_returns_empty(self) -> None:
        assert _detect_imap_server("not-an-email") == ""


# ---------------------------------------------------------------------------
# Parsing: _decode_header_value
# ---------------------------------------------------------------------------

class TestDecodeHeaderValue:
    def test_plain_ascii(self) -> None:
        assert ImapProvider._decode_header_value("Hello") == "Hello"

    def test_empty_string(self) -> None:
        assert ImapProvider._decode_header_value("") == ""

    def test_encoded_utf8(self) -> None:
        # "Hola" encoded as base64 UTF-8
        encoded = "=?utf-8?b?SG9sYQ==?="
        assert ImapProvider._decode_header_value(encoded) == "Hola"


# ---------------------------------------------------------------------------
# Parsing: _parse_sender
# ---------------------------------------------------------------------------

class TestParseSender:
    def test_name_and_email(self) -> None:
        name, addr = ImapProvider._parse_sender("John Doe <john@example.com>")
        assert name == "John Doe"
        assert addr == "john@example.com"

    def test_email_only(self) -> None:
        name, addr = ImapProvider._parse_sender("john@example.com")
        assert addr == "john@example.com"
        assert name == "john@example.com"

    def test_email_is_lowercased(self) -> None:
        _, addr = ImapProvider._parse_sender("John <JOHN@EXAMPLE.COM>")
        assert addr == "john@example.com"


# ---------------------------------------------------------------------------
# Parsing: _parse_date
# ---------------------------------------------------------------------------

class TestParseDate:
    def test_valid_date(self) -> None:
        dt = ImapProvider._parse_date("Mon, 1 Jan 2024 12:00:00 +0000")
        assert isinstance(dt, datetime)
        assert dt.year == 2024

    def test_empty_string_returns_none(self) -> None:
        assert ImapProvider._parse_date("") is None

    def test_invalid_date_returns_none(self) -> None:
        assert ImapProvider._parse_date("not-a-date") is None


# ---------------------------------------------------------------------------
# Parsing: _extract_unsubscribe_url
# ---------------------------------------------------------------------------

class TestExtractUnsubscribeUrl:
    def test_list_unsubscribe_header_http(self) -> None:
        url = ImapProvider._extract_unsubscribe_url(
            "<https://example.com/unsub>", "", ""
        )
        assert url == "https://example.com/unsub"

    def test_list_unsubscribe_mailto_skipped(self) -> None:
        # mailto is not an HTTP URL, should fall through
        url = ImapProvider._extract_unsubscribe_url(
            "<mailto:unsub@example.com>", "", ""
        )
        assert url == ""

    def test_body_text_fallback(self) -> None:
        body_text = "To unsubscribe visit https://example.com/opt-out"
        url = ImapProvider._extract_unsubscribe_url("", "", body_text)
        assert url == "https://example.com/opt-out"

    def test_no_url_returns_empty(self) -> None:
        assert ImapProvider._extract_unsubscribe_url("", "", "") == ""


# ---------------------------------------------------------------------------
# Parsing: _parse_message (integration)
# ---------------------------------------------------------------------------

class TestParseMessage:
    def _provider(self) -> ImapProvider:
        return _make_provider()

    def test_subject_extracted(self) -> None:
        raw = _make_raw_email(subject="Special Offer!")
        parsed_msg = email.message_from_bytes(raw)
        provider = self._provider()
        result = provider._parse_message("1", parsed_msg)
        assert result.subject == "Special Offer!"

    def test_sender_name_and_email_extracted(self) -> None:
        raw = _make_raw_email(from_addr="Shop <shop@deals.com>")
        parsed_msg = email.message_from_bytes(raw)
        provider = self._provider()
        result = provider._parse_message("2", parsed_msg)
        assert result.sender_name == "Shop"
        assert result.sender_email == "shop@deals.com"

    def test_date_extracted(self) -> None:
        raw = _make_raw_email(date_str="Mon, 1 Jan 2024 08:00:00 +0000")
        parsed_msg = email.message_from_bytes(raw)
        provider = self._provider()
        result = provider._parse_message("3", parsed_msg)
        assert result.date is not None
        assert result.date.year == 2024

    def test_body_text_extracted(self) -> None:
        raw = _make_raw_email(body_text="Hello from the newsletter!")
        parsed_msg = email.message_from_bytes(raw)
        provider = self._provider()
        result = provider._parse_message("4", parsed_msg)
        assert "Hello from the newsletter!" in result.body_text

    def test_list_unsubscribe_header_extracted(self) -> None:
        raw = _make_raw_email(list_unsubscribe="<https://deals.com/unsub>")
        parsed_msg = email.message_from_bytes(raw)
        provider = self._provider()
        result = provider._parse_message("5", parsed_msg)
        assert result.list_unsubscribe == "<https://deals.com/unsub>"
        assert result.has_unsubscribe_link is True
        assert result.unsubscribe_url == "https://deals.com/unsub"

    def test_missing_subject_uses_default(self) -> None:
        raw = _make_raw_email(subject="")
        parsed_msg = email.message_from_bytes(raw)
        # remove Subject header to simulate missing
        del parsed_msg["Subject"]
        provider = self._provider()
        result = provider._parse_message("6", parsed_msg)
        assert result.subject == "(sin asunto)"

    def test_provider_field_is_imap(self) -> None:
        raw = _make_raw_email()
        parsed_msg = email.message_from_bytes(raw)
        provider = self._provider()
        result = provider._parse_message("7", parsed_msg)
        assert result.provider == "imap"


# ---------------------------------------------------------------------------
# authenticate: connection / auth error handling
# ---------------------------------------------------------------------------

class TestAuthenticate:
    def test_missing_email_returns_false(self) -> None:
        provider = _make_provider(email_address="", password="pass", imap_server="imap.example.com")
        assert provider.authenticate() is False

    def test_missing_password_returns_false(self) -> None:
        provider = _make_provider(email_address="user@example.com", password="", imap_server="imap.example.com")
        assert provider.authenticate() is False

    def test_missing_server_returns_false(self) -> None:
        provider = _make_provider(
            email_address="user@customdomain.org",
            password="pass",
            imap_server="",
        )
        assert provider.authenticate() is False

    def test_auth_failure_returns_false(self) -> None:
        provider = _make_provider()
        with patch("imaplib.IMAP4_SSL") as mock_ssl:
            instance = MagicMock()
            instance.login.side_effect = imaplib.IMAP4.error("AUTHENTICATIONFAILED")
            mock_ssl.return_value = instance
            assert provider.authenticate() is False

    def test_connection_error_returns_false(self) -> None:
        provider = _make_provider()
        with patch("imaplib.IMAP4_SSL", side_effect=OSError("Connection refused")):
            assert provider.authenticate() is False

    def test_successful_auth_returns_true(self) -> None:
        provider = _make_provider()
        with patch("imaplib.IMAP4_SSL") as mock_ssl:
            instance = MagicMock()
            instance.login.return_value = ("OK", [b"Logged in"])
            mock_ssl.return_value = instance
            assert provider.authenticate() is True
            assert provider._conn is instance


# ---------------------------------------------------------------------------
# delete_emails
# ---------------------------------------------------------------------------

class TestDeleteEmails:
    def test_delete_marks_and_expunges(self) -> None:
        provider = _make_provider()
        provider._conn = MagicMock()
        provider._conn.select.return_value = ("OK", [])
        provider._conn.store.return_value = ("OK", [])
        provider._conn.expunge.return_value = ("OK", [])

        result = provider.delete_emails(["1", "2", "3"])

        assert result is True
        assert provider._conn.store.call_count == 3
        provider._conn.expunge.assert_called_once()

    def test_delete_without_connection_returns_false(self) -> None:
        provider = _make_provider()
        assert provider.delete_emails(["1"]) is False

    def test_delete_imap_error_returns_false(self) -> None:
        provider = _make_provider()
        provider._conn = MagicMock()
        provider._conn.select.side_effect = imaplib.IMAP4.error("NO [TRYCREATE]")
        assert provider.delete_emails(["1"]) is False


# ---------------------------------------------------------------------------
# block_sender
# ---------------------------------------------------------------------------

class TestBlockSender:
    def test_block_sender_returns_false(self) -> None:
        provider = _make_provider()
        result = provider.block_sender("spam@example.com")
        assert result is False

    def test_block_sender_prints_instructions(self, capsys) -> None:
        provider = _make_provider()
        provider.block_sender("spam@example.com")
        captured = capsys.readouterr()
        assert "spam@example.com" in captured.out
        assert "IMAP" in captured.out


# ---------------------------------------------------------------------------
# get_provider_name
# ---------------------------------------------------------------------------

class TestGetProviderName:
    def test_name(self) -> None:
        provider = _make_provider()
        assert provider.get_provider_name() == "IMAP Universal"
