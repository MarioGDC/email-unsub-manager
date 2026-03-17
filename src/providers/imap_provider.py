from __future__ import annotations

import email
import imaplib
import re
from datetime import datetime
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime
from typing import Optional

from src.models.email_message import EmailMessage
from src.providers.base_provider import BaseEmailProvider


_NO_SUBJECT = "(sin asunto)"

# Pre-configured IMAP servers for popular providers
_IMAP_SERVERS: dict[str, str] = {
    "outlook": "outlook.office365.com",
    "hotmail": "outlook.office365.com",
    "live": "outlook.office365.com",
    "gmail": "imap.gmail.com",
    "yahoo": "imap.mail.yahoo.com",
}


def _detect_imap_server(email_address: str) -> str:
    """Auto-detect IMAP server based on the email domain."""
    domain = email_address.lower().split("@")[-1] if "@" in email_address else ""
    # Check common provider keywords in domain
    for keyword, server in _IMAP_SERVERS.items():
        if keyword in domain:
            return server
    return ""


class ImapProvider(BaseEmailProvider):
    """Universal IMAP provider using Python's built-in imaplib.

    Works with any IMAP-enabled mailbox (Outlook/Hotmail, Gmail, Yahoo, etc.)
    using only an email address and password (or app password).
    No Azure Portal or Google Cloud Console registration required.
    """

    def __init__(
        self,
        email_address: str = "",
        password: str = "",
        imap_server: str = "",
        imap_port: int = 993,
    ) -> None:
        from config.settings import settings

        self._email = email_address or settings.IMAP_EMAIL
        self._password = password or settings.IMAP_PASSWORD
        self._server = imap_server or settings.IMAP_SERVER or _detect_imap_server(self._email)
        self._port = imap_port or settings.IMAP_PORT
        self._conn: Optional[imaplib.IMAP4_SSL] = None

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def authenticate(self) -> bool:
        """Connect to the IMAP server and authenticate with email + password."""
        if not self._email or not self._password:
            print(
                "[ImapProvider] Error: se requiere email y contraseña. "
                "Configura IMAP_EMAIL e IMAP_PASSWORD en el archivo .env "
                "o pásalos como argumentos."
            )
            return False

        if not self._server:
            print(
                "[ImapProvider] Error: no se pudo detectar el servidor IMAP automáticamente. "
                "Configura IMAP_SERVER en el archivo .env (ej: imap.gmail.com)."
            )
            return False

        try:
            self._conn = imaplib.IMAP4_SSL(self._server, self._port)
            self._conn.login(self._email, self._password)
            return True
        except imaplib.IMAP4.error as exc:
            error_msg = str(exc)
            if "AUTHENTICATIONFAILED" in error_msg or "Invalid credentials" in error_msg:
                print(
                    "[ImapProvider] Error de autenticación: contraseña incorrecta o "
                    "acceso IMAP deshabilitado. "
                    "Si tienes verificación en dos pasos, usa una contraseña de aplicación."
                )
            else:
                print(f"[ImapProvider] Error de autenticación: {exc}")
            return False
        except OSError as exc:
            print(
                f"[ImapProvider] No se pudo conectar al servidor {self._server}:{self._port}. "
                f"Verifica que el servidor IMAP esté accesible. Detalle: {exc}"
            )
            return False

    # ------------------------------------------------------------------
    # Fetch emails
    # ------------------------------------------------------------------

    def fetch_emails(self, max_results: int = 500) -> list[EmailMessage]:
        """Fetch emails from INBOX using IMAP SEARCH."""
        if self._conn is None:
            raise RuntimeError("No autenticado. Llama a authenticate() primero.")

        try:
            self._conn.select("INBOX")
            _, data = self._conn.search(None, "ALL")
        except imaplib.IMAP4.error as exc:
            print(f"[ImapProvider] Error al buscar correos: {exc}")
            return []

        message_ids = data[0].split() if data and data[0] else []
        # Take the most recent emails (last N ids)
        message_ids = message_ids[-max_results:]

        messages: list[EmailMessage] = []
        for uid in reversed(message_ids):  # most recent first
            msg = self._fetch_single_message(uid)
            if msg:
                messages.append(msg)

        return messages

    def _fetch_single_message(self, uid: bytes) -> Optional[EmailMessage]:
        """Fetch and parse a single message by its IMAP sequence number."""
        try:
            _, msg_data = self._conn.fetch(uid, "(RFC822)")  # type: ignore[union-attr]
            if not msg_data or msg_data[0] is None:
                return None

            raw_email = msg_data[0][1]
            if not isinstance(raw_email, bytes):
                return None

            parsed = email.message_from_bytes(raw_email)
            return self._parse_message(uid.decode(), parsed)
        except Exception as exc:  # noqa: BLE001
            print(f"[ImapProvider] No se pudo obtener el mensaje {uid}: {exc}")
            return None

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse_message(self, uid: str, msg: email.message.Message) -> EmailMessage:
        """Parse a Python email.message.Message into an EmailMessage."""
        subject = self._decode_header_value(msg.get("Subject", "")) or _NO_SUBJECT
        from_header = self._decode_header_value(msg.get("From", ""))
        sender_name, sender_email = self._parse_sender(from_header)
        date = self._parse_date(msg.get("Date", ""))
        list_unsubscribe = msg.get("List-Unsubscribe", "")

        body_text, body_html = self._extract_body(msg)

        unsubscribe_url = self._extract_unsubscribe_url(list_unsubscribe, body_html, body_text)
        has_unsubscribe_link = bool(unsubscribe_url or list_unsubscribe)

        snippet = body_text[:200].strip() if body_text else ""

        return EmailMessage(
            id=uid,
            subject=subject,
            sender_name=sender_name,
            sender_email=sender_email,
            date=date,
            snippet=snippet,
            body_text=body_text,
            body_html=body_html,
            list_unsubscribe=list_unsubscribe,
            has_unsubscribe_link=has_unsubscribe_link,
            unsubscribe_url=unsubscribe_url,
            provider="imap",
        )

    @staticmethod
    def _decode_header_value(value: str) -> str:
        """Decode RFC 2047-encoded header value to a plain string."""
        if not value:
            return ""
        decoded_parts: list[str] = []
        for part, charset in decode_header(value):
            if isinstance(part, bytes):
                decoded_parts.append(part.decode(charset or "utf-8", errors="replace"))
            else:
                decoded_parts.append(part)
        return "".join(decoded_parts)

    @staticmethod
    def _parse_sender(from_header: str) -> tuple[str, str]:
        """Parse a 'From' header into (name, email) tuple."""
        name, addr = parseaddr(from_header)
        return name or addr, addr.lower()

    @staticmethod
    def _parse_date(date_str: str) -> Optional[datetime]:
        """Parse an RFC 2822 date string into a datetime object."""
        if not date_str:
            return None
        try:
            return parsedate_to_datetime(date_str)
        except Exception:  # noqa: BLE001
            return None

    def _extract_body(self, msg: email.message.Message) -> tuple[str, str]:
        """Extract plain-text and HTML body from a MIME message."""
        body_text = ""
        body_html = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain" and not body_text:
                    body_text = self._decode_part(part)
                elif content_type == "text/html" and not body_html:
                    body_html = self._decode_part(part)
        else:
            content_type = msg.get_content_type()
            if content_type == "text/plain":
                body_text = self._decode_part(msg)
            elif content_type == "text/html":
                body_html = self._decode_part(msg)

        return body_text, body_html

    @staticmethod
    def _decode_part(part: email.message.Message) -> str:
        """Decode the payload of a message part to a string."""
        payload = part.get_payload(decode=True)
        if not payload:
            return ""
        charset = part.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")  # type: ignore[union-attr]

    @staticmethod
    def _extract_unsubscribe_url(list_unsubscribe: str, body_html: str, body_text: str) -> str:
        """Extract the best unsubscribe URL from available sources."""
        # Prefer List-Unsubscribe HTTP URL
        http_match = re.search(r"<(https?://[^>]+)>", list_unsubscribe)
        if http_match:
            return http_match.group(1)

        # Fallback: search body HTML for unsubscribe links
        if body_html:
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(body_html, "html.parser")
                for anchor in soup.find_all("a", href=True):
                    href: str = anchor["href"]
                    text: str = anchor.get_text(strip=True).lower()
                    if any(kw in text for kw in ("unsubscribe", "darse de baja", "cancelar suscripción", "opt-out")):
                        return href
            except Exception:  # noqa: BLE001
                pass

        # Fallback: plain text URL pattern near unsubscribe keyword
        url_pattern = re.compile(r"(https?://\S+)", re.IGNORECASE)
        for line in body_text.splitlines():
            if any(kw in line.lower() for kw in ("unsubscribe", "darse de baja", "opt-out")):
                match = url_pattern.search(line)
                if match:
                    return match.group(1)

        return ""

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def delete_emails(self, message_ids: list[str]) -> bool:
        """Mark emails as deleted and expunge them from the mailbox."""
        if self._conn is None:
            return False
        try:
            self._conn.select("INBOX")
            for msg_id in message_ids:
                self._conn.store(msg_id, "+FLAGS", "\\Deleted")
            self._conn.expunge()
            return True
        except imaplib.IMAP4.error as exc:
            print(f"[ImapProvider] Error al eliminar correos: {exc}")
            return False

    def block_sender(self, sender_email: str) -> bool:
        """
        IMAP does not support server-side filtering rules natively.
        Instructs the user to create a filter manually via the provider's web interface.
        """
        print(
            f"[ImapProvider] No es posible bloquear '{sender_email}' directamente mediante IMAP, "
            "ya que el protocolo no soporta la gestión de filtros/reglas. "
            "Para bloquear este remitente, crea un filtro manualmente desde la web de tu proveedor:\n"
            "  • Outlook/Hotmail: https://outlook.live.com -> Configuración -> Correo -> "
            "Correo no deseado -> Remitentes bloqueados\n"
            "  • Gmail: https://mail.google.com -> Configuración -> Filtros y direcciones bloqueadas\n"
            "  • Yahoo: https://mail.yahoo.com -> Configuración -> Seguridad y privacidad"
        )
        return False

    def get_provider_name(self) -> str:
        return "IMAP Universal"

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def logout(self) -> None:
        """Close the IMAP connection gracefully."""
        if self._conn is not None:
            try:
                self._conn.close()
                self._conn.logout()
            except Exception:  # noqa: BLE001
                pass
            finally:
                self._conn = None
