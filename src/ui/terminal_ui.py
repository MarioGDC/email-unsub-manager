from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich import box

from src.models.email_message import EmailAction, SenderGroup

console = Console()

_ACTION_MAP: dict[str, EmailAction] = {
    "d": EmailAction.DELETE,
    "b": EmailAction.BLOCK,
    "u": EmailAction.UNSUBSCRIBE,
    "s": EmailAction.NONE,  # skip
}

_ACTION_LABELS: dict[EmailAction, str] = {
    EmailAction.DELETE: "[red]Eliminar[/red]",
    EmailAction.BLOCK: "[yellow]Bloquear[/yellow]",
    EmailAction.UNSUBSCRIBE: "[green]Desuscribirse[/green]",
    EmailAction.NONE: "[dim]Omitir[/dim]",
}


class TerminalUI:
    """Rich-powered terminal interface for the Email Unsubscribe Manager."""

    # ------------------------------------------------------------------
    # Welcome / Provider selection
    # ------------------------------------------------------------------

    def show_welcome(self) -> None:
        console.print(
            Panel.fit(
                "[bold cyan]📧 Email Unsubscribe Manager[/bold cyan]\n"
                "[dim]Detecta y gestiona correos de spam, marketing y newsletters[/dim]",
                border_style="cyan",
            )
        )

    def select_provider(self) -> str:
        """Ask the user which email provider to use. Returns 'gmail' or 'outlook'."""
        console.print("\n[bold]Selecciona tu proveedor de correo:[/bold]")
        console.print("  [cyan]1[/cyan] Gmail")
        console.print("  [cyan]2[/cyan] Outlook / Microsoft 365")
        choice = Prompt.ask("Opción", choices=["1", "2"], default="1")
        return "gmail" if choice == "1" else "outlook"

    # ------------------------------------------------------------------
    # Progress spinners
    # ------------------------------------------------------------------

    def scanning_progress(self, max_emails: int) -> Progress:
        """Return a Rich Progress object for the scanning phase."""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[cyan]{task.completed}[/cyan]/[cyan]{task.total}[/cyan]"),
            console=console,
        )

    def show_scan_start(self, provider_name: str) -> None:
        console.print(f"\n[bold]Conectando a [cyan]{provider_name}[/cyan]...[/bold]")

    def show_scan_complete(self, total: int, spam_count: int) -> None:
        console.print(
            f"\n✅ Escaneados [cyan]{total}[/cyan] correos. "
            f"Detectados [red]{spam_count}[/red] posibles spam/marketing."
        )

    # ------------------------------------------------------------------
    # Display groups
    # ------------------------------------------------------------------

    def show_groups(self, groups: list[SenderGroup]) -> None:
        """Display a summary table of detected sender groups."""
        if not groups:
            console.print("[green]No se detectaron correos de spam o marketing.[/green]")
            return

        table = Table(
            title="📬 Remitentes detectados",
            box=box.ROUNDED,
            show_lines=True,
            highlight=True,
        )
        table.add_column("#", style="dim", width=4)
        table.add_column("Remitente", style="bold")
        table.add_column("Email", style="cyan")
        table.add_column("Correos", justify="right")
        table.add_column("Score", justify="right")
        table.add_column("Desuscribir", justify="center")
        table.add_column("Muestra de asuntos")

        for idx, group in enumerate(groups, start=1):
            table.add_row(
                str(idx),
                group.display_name,
                group.sender_email,
                str(group.email_count),
                f"{group.avg_spam_score:.1f}",
                "✅" if group.has_unsubscribe else "❌",
                " | ".join(group.sample_subjects[:2]),
            )

        console.print(table)

    # ------------------------------------------------------------------
    # Interactive action selection
    # ------------------------------------------------------------------

    def select_actions(self, groups: list[SenderGroup]) -> list[SenderGroup]:
        """
        Ask the user what to do with each sender group.
        Updates group.action in place and returns the list.
        """
        if not groups:
            return groups

        console.print(
            "\n[bold]Para cada remitente, elige:[/bold] "
            "[red]d[/red]=eliminar  [yellow]b[/yellow]=bloquear  "
            "[green]u[/green]=desuscribirse  [dim]s[/dim]=omitir\n"
        )

        for idx, group in enumerate(groups, start=1):
            unsub_hint = " (tiene enlace de baja)" if group.has_unsubscribe else ""
            label = (
                f"[{idx}] [bold]{group.display_name}[/bold] "
                f"<{group.sender_email}> ({group.email_count} correos){unsub_hint}"
            )
            console.print(label)
            choice = Prompt.ask(
                "  Acción",
                choices=list(_ACTION_MAP.keys()),
                default="s",
            )
            group.action = _ACTION_MAP[choice]

        return groups

    def confirm_actions(self, groups: list[SenderGroup]) -> bool:
        """Show a summary of chosen actions and ask for confirmation."""
        actioned = [g for g in groups if g.action != EmailAction.NONE]
        if not actioned:
            console.print("[dim]No se seleccionaron acciones.[/dim]")
            return False

        console.print("\n[bold]Resumen de acciones:[/bold]")
        for group in actioned:
            console.print(
                f"  • {group.sender_email}: {_ACTION_LABELS[group.action]}"
            )

        return Confirm.ask("\n¿Confirmar y ejecutar?", default=False)

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------

    def show_results(self, summary: dict[str, int]) -> None:
        """Display a results panel after executing actions."""
        lines = [
            f"🗑️  Correos eliminados: [red]{summary.get('deleted', 0)}[/red]",
            f"🚫 Remitentes bloqueados: [yellow]{summary.get('blocked', 0)}[/yellow]",
            f"📭 Desuscripciones iniciadas: [green]{summary.get('unsubscribed', 0)}[/green]",
        ]
        console.print(
            Panel(
                "\n".join(lines),
                title="[bold green]✅ Proceso completado[/bold green]",
                border_style="green",
            )
        )

    def show_error(self, message: str) -> None:
        console.print(f"[bold red]❌ Error:[/bold red] {message}")

    def show_info(self, message: str) -> None:
        console.print(f"[cyan]ℹ️  {message}[/cyan]")
