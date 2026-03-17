from __future__ import annotations

import base64
import os
import pickle
import re
from datetime import datetime
from email.utils import parseaddr, parsedate_to_datetime

from src.models.email_message import EmailMessage
from src.providers.base_provider import BaseEmailProvider


_NO_SUBJECT = "(sin asunto)"


class GmailProvider(BaseEmailProvider):
    """Gmail provider using the Gmail REST API with OAuth 2.0."""

    def __init__(self) -> None:
        self._service = None

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def authenticate(self) -> bool:
        """Authenticate via OAuth 2.0, reusing cached token when possible."""
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build

            from config.settings import settings

            creds: Credentials | None = None

            # Load cached token
            if os.path.exists(settings.GMAIL_TOKEN_FILE):
                with open(settings.GMAIL_TOKEN_FILE, "rb") as token_file:
                    creds = pickle.load(token_file)

            # Refresh or obtain new credentials
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(settings.GMAIL_CREDENTIALS_FILE):
                        raise FileNotFoundError(
                            f"Gmail credentials file not found: {settings.GMAIL_CREDENTIALS_FILE}"
                        )
                    flow = InstalledAppFlow.from_client_secrets_file(
                        settings.GMAIL_CREDENTIALS_FILE,
                        settings.GMAIL_SCOPES,
                    )
                    creds = flow.run_local_server(port=0)

                # Persist the token for future runs
                with open(settings.GMAIL_TOKEN_FILE, "wb") as token_file:
                    pickle.dump(creds, token_file)

            self._service = build("gmail", "v1", credentials=creds)
            return True

        except Exception as exc:  # noqa: BLE001
            print(f"[GmailProvider] Authentication error: {exc}")
            return False

    # ------------------------------------------------------------------
    # Fetch emails
    # ------------------------------------------------------------------

    def fetch_emails(self, max_results: int = 500) -> list[EmailMessage]:
        """Fetch emails from the inbox using pagination."""
        if self._service is None:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        messages: list[EmailMessage] = []
        page_token: str | None = None

        while len(messages) < max_results:
            batch_size = min(100, max_results - len(messages))
            kwargs: dict = {
                "userId": "me",
                "maxResults": batch_size,
                "labelIds": ["INBOX"],
            }
            if page_token:
                kwargs["pageToken"] = page_token

            result = self._service.users().messages().list(**kwargs).execute()  # type: ignore[union-attr]
            items = result.get("messages", [])
            if not items:
                break

            for item in items:
                msg = self._fetch_full_message(item["id"])
                if msg:
                    messages.append(msg)

            page_token = result.get("nextPageToken")
            if not page_token:
                break

        return messages

    def _fetch_full_message(self, message_id: str) -> EmailMessage | None:
        """Fetch and parse a single message by ID."""
        try:
            raw = (
                self._service.users()  # type: ignore[union-attr]
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
            return self._parse_gmail_message(raw)
        except Exception as exc:  # noqa: BLE001
            print(f"[GmailProvider] Could not fetch message {message_id}: {exc}")
            return None

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse_gmail_message(self, raw: dict) -> EmailMessage:
        """Parse a raw Gmail API message dict into an EmailMessage."""
        headers: dict[str, str] = {
            h["name"].lower(): h["value"]
            for h in raw.get("payload", {}).get("headers", [])
        }

        subject = headers.get("subject", _NO_SUBJECT)
        from_header = headers.get("from", "")
        sender_name, sender_email = self._parse_sender(from_header)
        date = self._parse_date(headers.get("date", ""))
        list_unsubscribe = headers.get("list-unsubscribe", "")

        body_text, body_html = self._extract_body(raw.get("payload", {}))

        unsubscribe_url = self._extract_unsubscribe_url(list_unsubscribe, body_html, body_text)
        has_unsubscribe_link = bool(unsubscribe_url or list_unsubscribe)

        return EmailMessage(
            id=raw.get("id", ""),
            subject=subject,
            sender_name=sender_name,
            sender_email=sender_email,
            date=date,
            snippet=raw.get("snippet", ""),
            body_text=body_text,
            body_html=body_html,
            list_unsubscribe=list_unsubscribe,
            has_unsubscribe_link=has_unsubscribe_link,
            unsubscribe_url=unsubscribe_url,
            provider="gmail",
        )

    def _extract_body(self, payload: dict) -> tuple[str, str]:
        """Recursively extract plain-text and HTML body from a MIME payload."""
        body_text = ""
        body_html = ""
        mime_type: str = payload.get("mimeType", "")

        if mime_type == "text/plain":
            body_text = self._decode_body_data(payload.get("body", {}).get("data", ""))
        elif mime_type == "text/html":
            body_html = self._decode_body_data(payload.get("body", {}).get("data", ""))
        elif mime_type.startswith("multipart/"):
            for part in payload.get("parts", []):
                t, h = self._extract_body(part)
                body_text = body_text or t
                body_html = body_html or h

        return body_text, body_html

    @staticmethod
    def _decode_body_data(data: str) -> str:
        """Decode base64url-encoded body data."""
        if not data:
            return ""
        try:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            return ""

    @staticmethod
    def _parse_sender(from_header: str) -> tuple[str, str]:
        """Parse a 'From' header into (name, email) tuple."""
        name, email = parseaddr(from_header)
        return name or email, email.lower()

    @staticmethod
    def _parse_date(date_str: str) -> datetime | None:
        """Parse an RFC 2822 date string into a datetime object."""
        if not date_str:
            return None
        try:
            return parsedate_to_datetime(date_str)
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _extract_unsubscribe_url(list_unsubscribe: str, body_html: str, body_text: str) -> str:
        """Extract the best unsubscribe URL from available sources."""
        # Prefer List-Unsubscribe HTTP URL
        http_match = re.search(r"<(https?://[^>]+)>", list_unsubscribe)
        if http_match:
            return http_match.group(1)

        # Fallback: search body HTML for unsubscribe links
        if body_html:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(body_html, "html.parser")
            for anchor in soup.find_all("a", href=True):
                href: str = anchor["href"]
                text: str = anchor.get_text(strip=True).lower()
                if any(kw in text for kw in ("unsubscribe", "darse de baja", "cancelar suscripción", "opt-out")):
                    return href

        # Fallback: plain text URL pattern near unsubscribe keyword
        url_pattern = re.compile(
            r"(https?://\S+)",
            re.IGNORECASE,
        )
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
        """Move emails to trash (Gmail does not permanently delete by default)."""
        if self._service is None:
            return False
        try:
            for msg_id in message_ids:
                self._service.users().messages().trash(userId="me", id=msg_id).execute()  # type: ignore[union-attr]
            return True
        except Exception as exc:  # noqa: BLE001
            print(f"[GmailProvider] Delete error: {exc}")
            return False

    def block_sender(self, sender_email: str) -> bool:
        """
        Block a sender by creating a Gmail filter that deletes future emails.
        Note: Gmail API filter creation requires 'gmail.settings.basic' scope.
        """
        if self._service is None:
            return False
        try:
            filter_body = {
                "criteria": {"from": sender_email},
                "action": {"removeLabelIds": ["INBOX"], "addLabelIds": ["TRASH"]},
            }
            self._service.users().settings().filters().create(  # type: ignore[union-attr]
                userId="me", body=filter_body
            ).execute()
            return True
        except Exception as exc:  # noqa: BLE001
            print(f"[GmailProvider] Block sender error: {exc}")
            return False

    def get_provider_name(self) -> str:
        return "Gmail"
