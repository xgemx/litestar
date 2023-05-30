from __future__ import annotations

import inspect
import multiprocessing
import os
import subprocess
import sys
from typing import TYPE_CHECKING, Any, cast

import click
import uvicorn
from click import Context, command, option
from rich.tree import Tree

from litestar.cli._utils import LitestarEnv, console, show_app_info
from litestar.routes import HTTPRoute, WebSocketRoute
from litestar.utils.helpers import unwrap_partial

__all__ = ("info_command", "routes_command", "run_command")

if TYPE_CHECKING:
    from litestar import Litestar


def _convert_uvicorn_args(args: dict[str, Any]) -> list[str]:
    process_args = []
    for arg, value in args.items():
        if isinstance(value, bool):
            if value:
                process_args.append(f"--{arg}")
        elif isinstance(value, tuple):
            for item in value:
                process_args.append(f"--{arg}={item}")
        else:
            process_args.append(f"--{arg}={value}")

    return process_args


@command(name="version")
@option("-s", "--short", help="Exclude release level and serial information", is_flag=True, default=False)
def version_command(short: bool) -> None:
    from litestar import __version__

    click.echo(__version__.formatted(short=short))


@command(name="info")
def info_command(app: Litestar) -> None:
    """Show information about the detected Litestar app."""

    show_app_info(app)


@command(name="run")
@option("-r", "--reload", help="Reload server on changes", default=False, is_flag=True)
@option("-p", "--port", help="Serve under this port", type=int, default=8000, show_default=True)
@option(
    "-wc",
    "--web-concurrency",
    help="The number of HTTP workers to launch",
    type=click.IntRange(min=1, max=multiprocessing.cpu_count() + 1),
    show_default=True,
    default=1,
)
@option("--host", help="Server under this host", default="127.0.0.1", show_default=True)
@option("--debug", help="Run app in debug mode", is_flag=True)
@option("--pdb", "use_pdb", help="Drop into PDB on an exception", is_flag=True)
@option("--reload-dir", help="Directories to watch for file changes", multiple=True)
def run_command(
    reload: bool,
    port: int,
    web_concurrency: int,
    host: str,
    debug: bool,
    reload_dir: tuple[str, ...],
    use_pdb: bool,
    ctx: Context,
) -> None:
    """Run a Litestar app.

    The app can be either passed as a module path in the form of <module name>.<submodule>:<app instance or factory>,
    set as an environment variable LITESTAR_APP with the same format or automatically discovered from one of these
    canonical paths: app.py, asgi.py, application.py or app/__init__.py. When auto-discovering application factories,
    functions with the name ``create_app`` are considered, or functions that are annotated as returning a ``Litestar``
    instance.
    """

    if debug:
        os.environ["LITESTAR_DEBUG"] = "1"

    if use_pdb:
        os.environ["LITESTAR_PDB"] = "1"

    env = cast(LitestarEnv, ctx.obj())
    app = env.app

    reload_dirs = env.reload_dirs or reload_dir

    host = env.host or host
    port = env.port or port
    reload = env.reload or reload or bool(reload_dirs)
    workers = env.web_concurrency or web_concurrency

    console.rule("[yellow]Starting server process", align="left")

    show_app_info(app)

    if workers == 1 and not reload:
        uvicorn.run(
            app=env.app_path,
            host=env.host or host,
            port=env.port or port,
            factory=env.is_app_factory,
        )
    else:
        # invoke uvicorn in a subprocess to be able to use the --reload flag. see
        # https://github.com/litestar-org/litestar/issues/1191 and https://github.com/encode/uvicorn/issues/1045
        if sys.gettrace() is not None:
            console.print(
                "[yellow]Debugger detected. Breakpoints might not work correctly inside route handlers when running"
                " with the --reload or --workers options[/]"
            )

        process_args = {"reload": reload, "host": host, "port": port, "workers": workers, "factory": env.is_app_factory}

        if reload_dirs:
            process_args["reload-dir"] = reload_dirs

        subprocess.run(
            [sys.executable, "-m", "uvicorn", env.app_path, *_convert_uvicorn_args(process_args)],  # noqa: S603
            check=True,
        )


@command(name="routes")
def routes_command(app: Litestar) -> None:  # pragma: no cover
    """Display information about the application's routes."""

    tree = Tree("", hide_root=True)

    for route in sorted(app.routes, key=lambda r: r.path):
        if isinstance(route, HTTPRoute):
            branch = tree.add(f"[green]{route.path}[/green] (HTTP)")
            for handler in route.route_handlers:
                handler_info = [
                    f"[blue]{handler.name or handler.handler_name}[/blue]",
                ]

                if inspect.iscoroutinefunction(unwrap_partial(handler.fn.value)):
                    handler_info.append("[magenta]async[/magenta]")
                else:
                    handler_info.append("[yellow]sync[/yellow]")

                handler_info.append(f'[cyan]{", ".join(sorted(handler.http_methods))}[/cyan]')

                if len(handler.paths) > 1:
                    for path in handler.paths:
                        branch.add(" ".join([f"[green]{path}[green]", *handler_info]))
                else:
                    branch.add(" ".join(handler_info))

        else:
            route_type = "WS" if isinstance(route, WebSocketRoute) else "ASGI"
            branch = tree.add(f"[green]{route.path}[/green] ({route_type})")
            branch.add(f"[blue]{route.route_handler.name or route.route_handler.handler_name}[/blue]")

    console.print(tree)
