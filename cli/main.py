"""Seal-Agent CLI — Command-line interface for interacting with the agent."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.panel import Panel

app = typer.Typer(name="seal", help="Seal-Agent: The Claude of Sales")
console = Console()


@app.command()
def start() -> None:
    """Start the Seal-Agent server."""
    import uvicorn

    from seal_agent.config import settings

    console.print(
        Panel.fit(
            "[bold blue]Seal-Agent[/bold blue] — The Claude of Sales\n"
            f"Starting on {settings.api_host}:{settings.api_port}",
            title="Starting",
        )
    )

    uvicorn.run(
        "seal_agent.api.app:create_app",
        factory=True,
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )


@app.command()
def chat(message: str = typer.Argument(help="Message to send to the agent")) -> None:
    """Send a message to the agent via CLI."""
    import httpx

    from seal_agent.config import settings

    url = f"http://{settings.api_host}:{settings.api_port}/api/agent/chat"

    try:
        response = httpx.post(url, json={"message": message})
        data = response.json()
        console.print(Panel(data["response"], title="Seal-Agent", border_style="blue"))
    except httpx.ConnectError:
        console.print("[red]Error: Seal-Agent server is not running. Start it with: seal start[/red]")


@app.command()
def status() -> None:
    """Check the agent's status."""
    import httpx

    from seal_agent.config import settings

    url = f"http://{settings.api_host}:{settings.api_port}/api/agent/status"

    try:
        response = httpx.get(url)
        data = response.json()
        console.print(Panel(str(data), title="Agent Status", border_style="green"))
    except httpx.ConnectError:
        console.print("[red]Agent is not running.[/red]")


@app.command()
def soul() -> None:
    """View the agent's soul configuration."""
    from seal_agent.core.soul_engine import SoulEngine

    engine = SoulEngine()
    asyncio.run(engine.load())

    console.print(Panel(engine.identity, title="Soul — Identity", border_style="magenta"))


@app.command()
def worker(
    concurrency: int = typer.Option(4, help="Number of worker processes"),
    queues: str = typer.Option("default", help="Comma-separated queue names"),
) -> None:
    """Start a Celery background worker."""
    from seal_agent.tasks.celery_app import celery_app

    console.print(
        Panel.fit(
            f"[bold blue]Seal-Agent Worker[/bold blue]\n"
            f"Concurrency: {concurrency} | Queues: {queues}",
            title="Starting Worker",
        )
    )

    celery_app.worker_main([
        "worker",
        f"--concurrency={concurrency}",
        f"--queues={queues}",
        "--loglevel=info",
    ])


@app.command()
def beat() -> None:
    """Start the Celery beat scheduler for periodic tasks."""
    from seal_agent.tasks.celery_app import celery_app

    console.print(
        Panel.fit(
            "[bold blue]Seal-Agent Beat Scheduler[/bold blue]\n"
            "Running periodic tasks on schedule",
            title="Starting Beat",
        )
    )

    celery_app.Beat(loglevel="info").run()


@app.command()
def db(
    action: str = typer.Argument(help="Migration action: upgrade, downgrade, current, history"),
    revision: str = typer.Argument("head", help="Target revision (default: head)"),
) -> None:
    """Run database migrations."""
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config("alembic.ini")

    if action == "upgrade":
        console.print(f"[blue]Upgrading database to {revision}...[/blue]")
        command.upgrade(alembic_cfg, revision)
        console.print("[green]Database upgraded successfully.[/green]")
    elif action == "downgrade":
        console.print(f"[yellow]Downgrading database to {revision}...[/yellow]")
        command.downgrade(alembic_cfg, revision)
        console.print("[green]Database downgraded successfully.[/green]")
    elif action == "current":
        command.current(alembic_cfg, verbose=True)
    elif action == "history":
        command.history(alembic_cfg, verbose=True)
    else:
        console.print(f"[red]Unknown action: {action}. Use: upgrade, downgrade, current, history[/red]")


if __name__ == "__main__":
    app()
