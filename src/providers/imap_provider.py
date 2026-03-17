import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
from datetime import datetime

from src.models.email_message import EmailMessage
from src.providers.base_provider import BaseEmailProvider
from config.settings import settings


class ImapProvider(BaseEmailProvider):
    """Universal IMAP provider - works with any email provider using just email + password."""

    def __init__(self, email_address: str = "", password: str = "", server: str = "", port: int = 993):
        self.email_address = email_address or settings.IMAP_EMAIL
        self.password = password or settings.IMAP_PASSWORD
        self.server = server or settings.IMAP_SERVER
        self.port = port or settings.IMAP_PORT
        self.connection: imaplib.IMAP4_SSL | None = None

        # Auto-detect server if not specified
        if not self.server and self.email_address:
            self.server = self._detect_server(self.email_address)

    def _detect_server(self, email_addr: str) -> str:
        """Auto-detect IMAP server from email domain."""
        domain = email_addr.split("@")[-1].lower()
        return settings.IMAP_SERVERS.get(domain, "")

    def authenticate(self) -> bool:
        """Connect and authenticate via IMAP SSL."""
        if not self.server:
            raise ValueError(
                "No se pudo detectar el servidor IMAP automáticamente. "
                "Por favor, especifica el servidor IMAP manualmente."
            )
        if not self.email_address or not self.password:
            raise ValueError("Email y contraseña son obligatorios.")

        try:
            self.connection = imaplib.IMAP4_SSL(self.server, self.port)
            self.connection.login(self.email_address, self.password)
            return True
        except imaplib.IMAP4.error as e:
            error_msg = str(e)
            if "AUTHENTICATIONFAILED" in error_msg.upper() or "LOGIN" in error_msg.upper():
                raise RuntimeError(
                    "❌ Contraseña incorrecta o acceso denegado.\n"
                    "   Si tienes verificación en 2 pasos (2FA), necesitas usar una contraseña de aplicación.\n"
                    "   Outlook: https://account.microsoft.com/security\n"
                    "   Gmail: https://myaccount.google.com/apppasswords"
                )
            raise RuntimeError(f"Error de autenticación IMAP: {error_msg}")
        except Exception as e:
            raise RuntimeError(
                f"No se pudo conectar al servidor {self.server}:{self.port}.\n"
                f"   Verifica que IMAP esté habilitado en tu cuenta de correo.\n"
                f"   Error: {e}"
            )

    def fetch_emails(self, max_results: int = 500) -> list[EmailMessage]:
        """Fetch emails from INBOX using IMAP."""
        if not self.connection:
            raise RuntimeError("No autenticado. Llama a authenticate() primero.")

        self.connection.select("INBOX")
        status, data = self.connection.search(None, "ALL")

        if status != "OK":
            return []

        message_ids = data[0].split()
        # Get most recent emails first
        message_ids = list(reversed(message_ids))[:max_results]

        emails: list[EmailMessage] = []
        for msg_id in message_ids:
            try:
                status, msg_data = self.connection.fetch(msg_id, "(RFC822)")
                if status != "OK" or not msg_data or not msg_data[0]:
                    continue

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                parsed = self._parse_message(msg, msg_id.decode())
                if parsed:
                    emails.append(parsed)
            except Exception as e:
                print(f"  ⚠ Error procesando mensaje: {e}")

        return emails

    def _parse_message(self, msg: email.message.Message, msg_id: str) -> EmailMessage | None:
        """Parse an email.message.Message into an EmailMessage."""
        # Decode subject
        subject = self._decode_header(msg.get("Subject", ""))

        # Parse sender
        from_raw = self._decode_header(msg.get("From", ""))
        sender_name, sender_email = self._parse_sender(from_raw)

        # Parse date
        date = None
        date_str = msg.get("Date", "")
        if date_str:
            try:
                date = parsedate_to_datetime(date_str)
            except Exception:
                date = None

        # Extract body
        body_text, body_html = self._extract_body(msg)

        # List-Unsubscribe header
        list_unsub = msg.get("List-Unsubscribe", "")

        # Snippet from body text
        snippet = (body_text or "")[:200].strip()

        return EmailMessage(
            id=msg_id,
            subject=subject or "(sin asunto)",
            sender_name=sender_name,
            sender_email=sender_email,
            date=date,
            snippet=snippet,
            body_text=body_text,
            body_html=body_html,
            list_unsubscribe=list_unsub,
            provider="imap",
        )

    @staticmethod
    def _decode_header(value: str) -> str:
        """Decode RFC 2047 encoded header."""
        if not value:
            return ""
        decoded_parts = decode_header(value)
        result = []
        for part, charset in decoded_parts:
            if isinstance(part, bytes):
                result.append(part.decode(charset or "utf-8", errors="replace"))
            else:
                result.append(part)
        return " ".join(result)

    @staticmethod
    def _parse_sender(from_raw: str) -> tuple[str, str]:
        """Parse 'Name <email>' into (name, email)."""
        if "<" in from_raw and ">" in from_raw:
            name = from_raw.split("<")[0].strip().strip('"')
            addr = from_raw.split("<")[1].split(">")[0].strip()
        else:
            name = ""
            addr = from_raw.strip()
        return name, addr.lower()

    @staticmethod
    def _extract_body(msg: email.message.Message) -> tuple[str, str]:
        """Extract text and HTML body from email message."""
        text = ""
        html = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                try:
                    payload = part.get_payload(decode=True)
                    if payload is None:
                        continue
                    charset = part.get_content_charset() or "utf-8"
                    decoded = payload.decode(charset, errors="replace")

                    if content_type == "text/plain" and not text:
                        text = decoded
                    elif content_type == "text/html" and not html:
                        html = decoded
                except Exception:
                    continue
        else:
            content_type = msg.get_content_type()
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or "utf-8"
                    decoded = payload.decode(charset, errors="replace")
                    if content_type == "text/plain":
                        text = decoded
                    elif content_type == "text/html":
                        html = decoded
            except Exception:
                pass

        return text, html

    def delete_emails(self, message_ids: list[str]) -> bool:
        """Delete emails by marking them as Deleted and expunging."""
        if not self.connection:
            return False

        self.connection.select("INBOX")
        success = True
        for msg_id in message_ids:
            try:
                self.connection.store(msg_id.encode(), "+FLAGS", "\\Deleted")
            except Exception as e:
                print(f"  ⚠ Error eliminando mensaje {msg_id}: {e}")
                success = False

        try:
            self.connection.expunge()
        except Exception:
            success = False

        return success

    def block_sender(self, sender_email: str) -> bool:
        """IMAP doesn't support filters/rules natively."""
        print(f"  ⚠ IMAP no soporta bloquear remitentes directamente.")
        print(f"  ℹ Para bloquear a {sender_email}, crea un filtro manualmente:")
        print(f"    • Outlook: Configuración → Correo → Reglas")
        print(f"    • Gmail: Configuración → Filtros y direcciones bloqueadas")
        return False

    def get_provider_name(self) -> str:
        return f"IMAP ({self.server})"

    def __del__(self):
        """Close IMAP connection on cleanup."""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
            except Exception:
                pass
