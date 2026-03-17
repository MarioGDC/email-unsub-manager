from __future__ import annotations

import webbrowser

import requests

from src.models.email_message import EmailAction, SenderGroup
from src.providers.base_provider import BaseEmailProvider


class EmailActions:
    """Executes user-selected actions (delete, block, unsubscribe) on email groups."""

    def __init__(self, provider: BaseEmailProvider) -> None:
        self._provider = provider

    def execute(self, groups: list[SenderGroup]) -> dict[str, int]:
        """
        Execute the chosen action for each SenderGroup.

        Returns a summary dict: {"deleted": N, "blocked": N, "unsubscribed": N}.
        """
        summary: dict[str, int] = {"deleted": 0, "blocked": 0, "unsubscribed": 0}

        for group in groups:
            if group.action == EmailAction.DELETE:
                if self._provider.delete_emails(group.message_ids):
                    summary["deleted"] += group.email_count

            elif group.action == EmailAction.BLOCK:
                if self._provider.block_sender(group.sender_email):
                    summary["blocked"] += 1
                # Also delete the emails after blocking
                self._provider.delete_emails(group.message_ids)

            elif group.action == EmailAction.UNSUBSCRIBE:
                self._unsubscribe(group)
                summary["unsubscribed"] += 1

        return summary

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _unsubscribe(self, group: SenderGroup) -> None:
        """
        Attempt to unsubscribe using the best available method:
        1. HTTP POST/GET to List-Unsubscribe URL
        2. Open the URL in the browser as a fallback
        """
        url = group.unsubscribe_url
        if not url:
            print(f"[EmailActions] No unsubscribe URL available for {group.sender_email}")
            return

        try:
            response = requests.post(url, timeout=10)
            if response.ok:
                return
            # Try GET if POST did not succeed
            response = requests.get(url, timeout=10)
            if not response.ok:
                print(
                    f"[EmailActions] HTTP {response.status_code} from unsubscribe URL "
                    f"{url} — opening in browser."
                )
                webbrowser.open(url)
        except Exception as exc:  # noqa: BLE001
            print(f"[EmailActions] Request error for unsubscribe URL {url}: {exc} — opening in browser.")
            # Open in browser as last resort
            try:
                webbrowser.open(url)
            except Exception as open_exc:  # noqa: BLE001
                print(f"[EmailActions] Could not open unsubscribe URL: {url} ({open_exc})")
