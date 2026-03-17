import re
from urllib.parse import urlparse

import urllib.request

from src.models.email_message import EmailAction, EmailMessage, SenderGroup
from src.providers.base_provider import BaseEmailProvider


class EmailActionExecutor:
    """Executes user-requested actions on groups of emails."""

    def __init__(self, provider: BaseEmailProvider):
        self.provider = provider

    def execute_actions(self, groups: list[SenderGroup]) -> dict:
        """Execute all requested actions and return a summary."""
        summary = {
            "deleted": 0,
            "unsubscribed": 0,
            "blocked": 0,
            "skipped": 0,
            "errors": [],
        }

        for group in groups:
            action = group.action
            if action == EmailAction.SKIP:
                summary["skipped"] += group.email_count
                continue

            if action == EmailAction.DELETE:
                ids = [e.id for e in group.emails]
                ok = self.provider.delete_emails(ids)
                if ok:
                    summary["deleted"] += group.email_count
                else:
                    summary["errors"].append(f"Error eliminando correos de {group.sender_email}")

            elif action == EmailAction.UNSUBSCRIBE:
                ok = self._unsubscribe(group)
                if ok:
                    summary["unsubscribed"] += 1
                else:
                    summary["errors"].append(f"No se pudo desuscribir de {group.sender_email}")

            elif action == EmailAction.BLOCK:
                ok = self.provider.block_sender(group.sender_email)
                if ok:
                    summary["blocked"] += 1
                else:
                    summary["errors"].append(f"No se pudo bloquear a {group.sender_email}")

        return summary

    def _unsubscribe(self, group: SenderGroup) -> bool:
        """Attempt to unsubscribe using the List-Unsubscribe header."""
        # Find an email with a List-Unsubscribe header
        unsub_header = ""
        for email_msg in group.emails:
            if email_msg.list_unsubscribe:
                unsub_header = email_msg.list_unsubscribe
                break

        if not unsub_header:
            return False

        # Extract URLs and mailto links
        urls = re.findall(r"<(https?://[^>]+)>", unsub_header)
        mailto = re.findall(r"<mailto:([^>]+)>", unsub_header)

        # Try HTTP unsubscribe first
        for url in urls:
            try:
                parsed = urlparse(url)
                if parsed.scheme in ("http", "https"):
                    req = urllib.request.Request(
                        url,
                        headers={"User-Agent": "Mozilla/5.0"},
                        method="GET",
                    )
                    with urllib.request.urlopen(req, timeout=10):
                        pass
                    return True
            except Exception:
                continue

        # No HTTP URL succeeded and no mailto link available
        return False
