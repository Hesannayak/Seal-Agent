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


if __name__ == "__main__":
    app()
