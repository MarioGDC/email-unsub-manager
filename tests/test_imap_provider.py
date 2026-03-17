"""Tests for the ImapProvider."""
import email
import imaplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from src.providers.imap_provider import ImapProvider


class TestImapProviderServerDetection:
    def test_detect_gmail(self):
        provider = ImapProvider(email_address="user@gmail.com", password="pass")
        assert provider.server == "imap.gmail.com"

    def test_detect_outlook(self):
        provider = ImapProvider(email_address="user@outlook.com", password="pass")
        assert provider.server == "outlook.office365.com"

    def test_detect_hotmail(self):
        provider = ImapProvider(email_address="user@hotmail.com", password="pass")
        assert provider.server == "outlook.office365.com"

    def test_detect_live(self):
        provider = ImapProvider(email_address="user@live.com", password="pass")
        assert provider.server == "outlook.office365.com"

    def test_detect_yahoo(self):
        provider = ImapProvider(email_address="user@yahoo.com", password="pass")
        assert provider.server == "imap.mail.yahoo.com"

    def test_detect_unknown_domain(self):
        provider = ImapProvider(email_address="user@unknown-provider.com", password="pass")
        assert provider.server == ""

    def test_explicit_server_not_overridden(self):
        provider = ImapProvider(
            email_address="user@gmail.com",
            password="pass",
            server="custom.imap.server.com",
        )
        assert provider.server == "custom.imap.server.com"

    def test_no_email_no_server(self):
        provider = ImapProvider(password="pass")
        assert provider.server == ""


class TestImapProviderAuthentication:
    def test_authenticate_success(self):
        with patch("imaplib.IMAP4_SSL") as mock_imap_cls:
            mock_conn = MagicMock()
            mock_imap_cls.return_value = mock_conn

            provider = ImapProvider(
                email_address="user@gmail.com",
                password="correct_password",
            )
            result = provider.authenticate()

            assert result is True
            mock_imap_cls.assert_called_once_with("imap.gmail.com", 993)
            mock_conn.login.assert_called_once_with("user@gmail.com", "correct_password")

    def test_authenticate_wrong_password(self):
        with patch("imaplib.IMAP4_SSL") as mock_imap_cls:
            mock_conn = MagicMock()
            mock_conn.login.side_effect = imaplib.IMAP4.error("AUTHENTICATIONFAILED")
            mock_imap_cls.return_value = mock_conn

            provider = ImapProvider(
                email_address="user@gmail.com",
                password="wrong_password",
            )
            with pytest.raises(RuntimeError) as exc_info:
                provider.authenticate()

            assert "contraseña" in exc_info.value.args[0].lower() or "2fa" in exc_info.value.args[0].lower()

    def test_authenticate_connection_error(self):
        with patch("imaplib.IMAP4_SSL") as mock_imap_cls:
            mock_imap_cls.side_effect = ConnectionRefusedError("Connection refused")

            provider = ImapProvider(
                email_address="user@gmail.com",
                password="pass",
            )
            with pytest.raises(RuntimeError) as exc_info:
                provider.authenticate()

            assert "conectar" in exc_info.value.args[0].lower()

    def test_authenticate_no_server_raises_value_error(self):
        provider = ImapProvider(
            email_address="user@unknown-provider.com",
            password="pass",
        )
        with pytest.raises(ValueError) as exc_info:
            provider.authenticate()

        assert "servidor" in exc_info.value.args[0].lower()

    def test_authenticate_missing_credentials(self):
        provider = ImapProvider(server="imap.example.com")
        with pytest.raises(ValueError) as exc_info:
            provider.authenticate()

        assert "email" in exc_info.value.args[0].lower() or "contraseña" in exc_info.value.args[0].lower()


class TestImapProviderParsing:
    def setup_method(self):
        self.provider = ImapProvider(
            email_address="user@gmail.com",
            password="pass",
        )

    def test_parse_sender_with_name_and_angle_brackets(self):
        name, addr = ImapProvider._parse_sender("John Doe <john@example.com>")
        assert name == "John Doe"
        assert addr == "john@example.com"

    def test_parse_sender_email_only(self):
        name, addr = ImapProvider._parse_sender("john@example.com")
        assert name == ""
        assert addr == "john@example.com"

    def test_parse_sender_quoted_name(self):
        name, addr = ImapProvider._parse_sender('"Acme Corp" <info@acme.com>')
        assert name == "Acme Corp"
        assert addr == "info@acme.com"

    def test_parse_sender_lowercase_email(self):
        _, addr = ImapProvider._parse_sender("User <USER@EXAMPLE.COM>")
        assert addr == "user@example.com"

    def test_decode_header_plain(self):
        result = ImapProvider._decode_header("Hello World")
        assert result == "Hello World"

    def test_decode_header_empty(self):
        result = ImapProvider._decode_header("")
        assert result == ""

    def test_decode_header_encoded(self):
        # RFC 2047 encoded: "=?utf-8?b?SGVsbG8=?=" decodes to "Hello"
        result = ImapProvider._decode_header("=?utf-8?b?SGVsbG8=?=")
        assert "Hello" in result

    def _build_simple_email(
        self,
        subject: str = "Test Subject",
        from_addr: str = "sender@example.com",
        body_text: str = "Hello",
        body_html: str = "",
        list_unsub: str = "",
    ) -> email.message.Message:
        if body_html:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = from_addr
            msg.attach(MIMEText(body_text, "plain"))
            msg.attach(MIMEText(body_html, "html"))
        else:
            msg = MIMEText(body_text, "plain")
            msg["Subject"] = subject
            msg["From"] = from_addr
        if list_unsub:
            msg["List-Unsubscribe"] = list_unsub
        return msg

    def test_parse_message_basic(self):
        msg = self._build_simple_email(
            subject="Test Subject",
            from_addr="Newsletter <news@example.com>",
            body_text="Hello world",
        )
        parsed = self.provider._parse_message(msg, "42")

        assert parsed is not None
        assert parsed.id == "42"
        assert parsed.subject == "Test Subject"
        assert parsed.sender_email == "news@example.com"
        assert parsed.sender_name == "Newsletter"
        assert "Hello world" in parsed.body_text
        assert parsed.provider == "imap"

    def test_parse_message_with_list_unsubscribe(self):
        msg = self._build_simple_email(
            list_unsub="<https://example.com/unsub>"
        )
        parsed = self.provider._parse_message(msg, "1")
        assert parsed is not None
        assert "https://example.com/unsub" in parsed.list_unsubscribe

    def test_parse_message_multipart(self):
        msg = self._build_simple_email(
            body_text="Plain text content",
            body_html="<html><body>HTML content</body></html>",
        )
        parsed = self.provider._parse_message(msg, "10")
        assert parsed is not None
        assert "Plain text content" in parsed.body_text
        assert "HTML content" in parsed.body_html

    def test_parse_message_no_subject(self):
        msg = email.message.Message()
        msg["From"] = "sender@example.com"
        msg.set_payload("Body")

        parsed = self.provider._parse_message(msg, "99")
        assert parsed is not None
        assert parsed.subject == "(sin asunto)"

    def test_extract_body_plain_only(self):
        msg = MIMEText("Just plain text", "plain")
        text, html = ImapProvider._extract_body(msg)
        assert "Just plain text" in text
        assert html == ""

    def test_extract_body_html_only(self):
        msg = MIMEText("<b>Bold</b>", "html")
        text, html = ImapProvider._extract_body(msg)
        assert text == ""
        assert "<b>Bold</b>" in html


class TestImapProviderFetch:
    def test_fetch_emails_not_authenticated(self):
        provider = ImapProvider(email_address="user@gmail.com", password="pass")
        with pytest.raises(RuntimeError) as exc_info:
            provider.fetch_emails()
        assert "autenticado" in exc_info.value.args[0].lower()

    def test_fetch_emails_returns_list(self):
        """Mock a minimal IMAP fetch returning one email."""
        raw_msg = MIMEText("Test body", "plain")
        raw_msg["Subject"] = "Hello"
        raw_msg["From"] = "sender@example.com"
        raw_bytes = raw_msg.as_bytes()

        mock_conn = MagicMock()
        mock_conn.select.return_value = ("OK", [b"INBOX"])
        mock_conn.search.return_value = ("OK", [b"1"])
        mock_conn.fetch.return_value = ("OK", [(b"1 (RFC822 {123})", raw_bytes)])

        provider = ImapProvider(email_address="user@gmail.com", password="pass")
        provider.connection = mock_conn

        emails = provider.fetch_emails(max_results=10)
        assert len(emails) == 1
        assert emails[0].subject == "Hello"
        assert emails[0].sender_email == "sender@example.com"

    def test_fetch_emails_respects_max_results(self):
        """Only fetch up to max_results emails."""
        raw_msg = MIMEText("Body", "plain")
        raw_msg["Subject"] = "Test"
        raw_msg["From"] = "a@example.com"
        raw_bytes = raw_msg.as_bytes()

        mock_conn = MagicMock()
        mock_conn.select.return_value = ("OK", [b"INBOX"])
        # 10 message IDs
        mock_conn.search.return_value = ("OK", [b"1 2 3 4 5 6 7 8 9 10"])
        mock_conn.fetch.return_value = ("OK", [(b"1 (RFC822 {100})", raw_bytes)])

        provider = ImapProvider(email_address="user@gmail.com", password="pass")
        provider.connection = mock_conn

        emails = provider.fetch_emails(max_results=3)
        assert len(emails) <= 3


class TestImapProviderActions:
    def test_delete_emails_success(self):
        mock_conn = MagicMock()
        mock_conn.expunge.return_value = ("OK", [])

        provider = ImapProvider(email_address="user@gmail.com", password="pass")
        provider.connection = mock_conn

        result = provider.delete_emails(["1", "2", "3"])
        assert result is True
        assert mock_conn.store.call_count == 3

    def test_delete_emails_without_connection(self):
        provider = ImapProvider(email_address="user@gmail.com", password="pass")
        result = provider.delete_emails(["1"])
        assert result is False

    def test_block_sender_always_returns_false(self):
        provider = ImapProvider(email_address="user@gmail.com", password="pass")
        result = provider.block_sender("spam@example.com")
        assert result is False

    def test_get_provider_name_includes_server(self):
        provider = ImapProvider(email_address="user@gmail.com", password="pass")
        name = provider.get_provider_name()
        assert name == "IMAP (imap.gmail.com)"
