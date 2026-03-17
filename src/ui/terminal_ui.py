import getpass
from contextlib import contextmanager

from rich.console import Console
from rich.prompt import IntPrompt, Prompt
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.models.email_message import EmailAction, SenderGroup

console = Console()


class TerminalUI:
    """Rich-based terminal user interface."""

    def show_banner(self) -> None:
        console.print()
        console.print("[bold cyan]╔══════════════════════════════════════╗[/bold cyan]")
        console.print("[bold cyan]║   📧 Email Unsubscribe Manager       ║[/bold cyan]")
        console.print("[bold cyan]╚══════════════════════════════════════╝[/bold cyan]")
        console.print()

    def show_info(self, message: str) -> None:
        console.print(f"[blue]ℹ[/blue] {message}")

    def show_success(self, message: str) -> None:
        console.print(f"[green]✅[/green] {message}")

    def show_error(self, message: str) -> None:
        console.print(f"[red]❌ Error:[/red] {message}")

    @contextmanager
    def show_scanning_progress(self):
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            yield progress

    def select_provider(self) -> tuple[str, dict]:
        """Let user configure IMAP connection interactively."""
        console.print("\n[bold]📧 Configuración de conexión[/bold]\n")
        console.print("  [bold]Proveedores soportados:[/bold]")
        console.print("  [1] 📬 Outlook / Hotmail / Live")
        console.print("  [2] 📫 Gmail")
        console.print("  [3] 📧 Yahoo")
        console.print("  [4] 🔧 Otro (servidor IMAP personalizado)")
        console.print("  [5] ❌ Salir\n")

        choice = Prompt.ask("Selecciona tu proveedor", choices=["1", "2", "3", "4", "5"], default="1")

        if choice == "5":
            return "exit", {}

        # Map choice to IMAP server
        servers = {
            "1": "outlook.office365.com",
            "2": "imap.gmail.com",
            "3": "imap.mail.yahoo.com",
        }

        server = servers.get(choice, "")
        if choice == "4":
            server = Prompt.ask("Servidor IMAP")
            port = IntPrompt.ask("Puerto", default=993)
        else:
            port = 993

        # Ask for credentials
        email_addr = Prompt.ask("\n📧 Tu email")

        console.print("[dim]  (Si tienes 2FA, usa una contraseña de aplicación)[/dim]")
        password = getpass.getpass("🔑 Contraseña: ")

        return "imap", {
            "email_address": email_addr,
            "password": password,
            "server": server,
            "port": port,
        }

    def show_results_table(self, groups: list[SenderGroup]) -> None:
        """Display a table of sender groups with spam scores."""
        if not groups:
            console.print("\n[yellow]⚠[/yellow] No se encontraron remitentes de spam/marketing.\n")
            return

        table = Table(title=f"\n📊 Remitentes detectados ({len(groups)} grupos)", show_lines=True)
        table.add_column("#", style="dim", width=4)
        table.add_column("Remitente", style="cyan")
        table.add_column("Emails", justify="right")
        table.add_column("Score", justify="right")
        table.add_column("Último asunto", style="dim")

        for i, group in enumerate(groups, 1):
            score = group.avg_spam_score
            score_color = "red" if score >= 70 else "yellow" if score >= 40 else "green"
            latest = group.latest_email
            if latest and len(latest.subject) > 50:
                subject = latest.subject[:50] + "…"
            elif latest:
                subject = latest.subject
            else:
                subject = ""
            table.add_row(
                str(i),
                f"{group.sender_name or ''}\n[dim]{group.sender_email}[/dim]",
                str(group.email_count),
                f"[{score_color}]{score:.0f}[/{score_color}]",
                subject,
            )

        console.print(table)

    def get_user_actions(self, groups: list[SenderGroup]) -> list[SenderGroup]:
        """Interactively ask the user what action to take for each sender group."""
        console.print("\n[bold]🎯 Selecciona acción para cada remitente:[/bold]")
        console.print("  [d] Eliminar todos sus correos")
        console.print("  [u] Desuscribir (usar header List-Unsubscribe)")
        console.print("  [b] Bloquear remitente")
        console.print("  [s] Omitir (no hacer nada)\n")

        action_map = {
            "d": EmailAction.DELETE,
            "u": EmailAction.UNSUBSCRIBE,
            "b": EmailAction.BLOCK,
            "s": EmailAction.SKIP,
        }

        for i, group in enumerate(groups, 1):
            label = group.sender_name or group.sender_email
            choice = Prompt.ask(
                f"  [{i}] {label} ({group.email_count} emails, score {group.avg_spam_score:.0f})",
                choices=["d", "u", "b", "s"],
                default="s",
            )
            group.action = action_map[choice]

        return groups

    def confirm_actions(self, groups: list[SenderGroup]) -> bool:
        """Show a summary of pending actions and ask for confirmation."""
        pending = [g for g in groups if g.action != EmailAction.SKIP]
        if not pending:
            console.print("\n[yellow]No hay acciones pendientes.[/yellow]")
            return False

        console.print("\n[bold]📋 Resumen de acciones:[/bold]")
        for group in pending:
            action_label = {
                EmailAction.DELETE: "🗑 Eliminar",
                EmailAction.UNSUBSCRIBE: "📤 Desuscribir",
                EmailAction.BLOCK: "🚫 Bloquear",
            }.get(group.action, "?")
            console.print(f"  {action_label}: {group.sender_email} ({group.email_count} emails)")

        return Prompt.ask("\n¿Confirmas estas acciones?", choices=["s", "n"], default="n") == "s"

    def show_execution_summary(self, summary: dict) -> None:
        """Display the results after executing actions."""
        console.print("\n[bold green]✅ Acciones completadas:[/bold green]")
        console.print(f"  🗑 Eliminados: {summary.get('deleted', 0)} correos")
        console.print(f"  📤 Desuscripciones: {summary.get('unsubscribed', 0)}")
        console.print(f"  🚫 Bloqueados: {summary.get('blocked', 0)}")
        console.print(f"  ⏭ Omitidos: {summary.get('skipped', 0)}")

        errors = summary.get("errors", [])
        if errors:
            console.print("\n[bold red]⚠ Errores:[/bold red]")
            for err in errors:
                console.print(f"  • {err}")
