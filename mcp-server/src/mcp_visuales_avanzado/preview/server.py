"""HTTP + WebSocket server for PBIR live preview.

Architecture:
  - HTTP server on ``port`` serves the rendered HTML
  - WebSocket server on ``port + 1`` pushes "reload" on file changes
  - File watcher polls the definition folder and triggers broadcasts

Uses only stdlib ``http.server`` + optional ``websockets`` library.
"""

from __future__ import annotations

import asyncio
import http.server
import threading
from pathlib import Path
from typing import Any


def start_preview_server(
    definition_path: Path,
    port: int = 8080,
) -> dict[str, Any]:
    """Start the preview server (blocking).

    Returns a status dict (only reached if server is stopped).
    """
    # Check for websockets dependency
    try:
        import websockets
    except ImportError:
        return {
            "status": "error",
            "message": (
                "Preview requires the 'websockets' package. "
                "Install with: pip install -e \".[preview]\""
            ),
        }

    from mcp_visuales_avanzado.preview.renderer import render_report
    from mcp_visuales_avanzado.preview.watcher import PbirWatcher

    ws_port = port + 1
    ws_clients: set[Any] = set()

    # --- WebSocket server ---
    async def ws_handler(websocket: Any) -> None:
        ws_clients.add(websocket)
        try:
            async for _ in websocket:
                pass  # Keep connection alive
        finally:
            ws_clients.discard(websocket)

    async def broadcast_reload() -> None:
        if ws_clients:
            msg = "reload"
            await asyncio.gather(
                *[c.send(msg) for c in ws_clients],
                return_exceptions=True,
            )

    loop: asyncio.AbstractEventLoop | None = None

    def on_file_change() -> None:
        """Called by the watcher when files change."""
        if loop is not None:
            asyncio.run_coroutine_threadsafe(broadcast_reload(), loop)

    # --- HTTP server ---
    class PreviewHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            try:
                html = render_report(definition_path)
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.end_headers()
                self.wfile.write(html.encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(f"Error: {e}".encode())

        def log_message(self, format: str, *args: Any) -> None:
            pass  # Suppress default logging

    # --- Start everything ---
    import click

    click.echo("Starting preview server...", err=True)
    click.echo(f"  HTTP:      http://localhost:{port}", err=True)
    click.echo(f"  WebSocket: ws://localhost:{ws_port}", err=True)
    click.echo(f"  Watching:  {definition_path}", err=True)
    click.echo("  Press Ctrl+C to stop.", err=True)

    # Start file watcher in background thread
    watcher = PbirWatcher(definition_path, on_change=on_file_change)
    watcher_thread = threading.Thread(target=watcher.start, daemon=True)
    watcher_thread.start()

    # Start HTTP server in background thread
    httpd = http.server.HTTPServer(("127.0.0.1", port), PreviewHandler)
    http_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    http_thread.start()

    # Run WebSocket server on main thread's event loop
    async def run_ws() -> None:
        nonlocal loop
        loop = asyncio.get_running_loop()
        async with websockets.serve(ws_handler, "127.0.0.1", ws_port):
            await asyncio.Future()  # Run forever

    try:
        asyncio.run(run_ws())
    except KeyboardInterrupt:
        pass
    finally:
        watcher.stop()
        httpd.shutdown()

    return {
        "status": "stopped",
        "message": "Preview server stopped.",
    }
