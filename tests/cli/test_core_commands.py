import os
import sys
from pathlib import Path
from typing import Callable, Generator, List, Optional
from unittest.mock import MagicMock

import pytest
from _pytest.monkeypatch import MonkeyPatch
from click.testing import CliRunner
from pytest_mock import MockerFixture

from litestar import __version__ as litestar_version
from litestar.cli.main import litestar_group as cli_command
from litestar.exceptions import LitestarWarning
from tests.cli import (
    CREATE_APP_FILE_CONTENT,
    GENERIC_APP_FACTORY_FILE_CONTENT,
    GENERIC_APP_FACTORY_FILE_CONTENT_STRING_ANNOTATION,
)
from tests.cli.conftest import CreateAppFileFixture

project_base = Path(__file__).parent.parent.parent


@pytest.fixture()
def mock_subprocess_run(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("litestar.cli.commands.core.subprocess.run")


@pytest.fixture()
def mock_uvicorn_run(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("litestar.cli.commands.core.uvicorn.run")


@pytest.fixture()
def mock_show_app_info(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("litestar.cli.commands.core.show_app_info")


@pytest.mark.parametrize("set_in_env", [True, False])
@pytest.mark.parametrize("custom_app_file", [Path("my_app.py"), None])
@pytest.mark.parametrize("host", ["0.0.0.0", None])
@pytest.mark.parametrize("port", [8081, None])
@pytest.mark.parametrize("reload", [True, False, None])
@pytest.mark.parametrize("web_concurrency", [2, None])
@pytest.mark.parametrize("app_dir", ["custom_subfolder", None])
@pytest.mark.parametrize("reload_dir", [[".", "../somewhere_else"], None])
def test_run_command(
    mocker: MockerFixture,
    runner: CliRunner,
    monkeypatch: MonkeyPatch,
    reload: Optional[bool],
    port: Optional[int],
    host: Optional[str],
    web_concurrency: Optional[int],
    app_dir: Optional[str],
    reload_dir: Optional[List[str]],
    custom_app_file: Optional[Path],
    create_app_file: CreateAppFileFixture,
    set_in_env: bool,
    mock_subprocess_run: MagicMock,
    mock_uvicorn_run: MagicMock,
    tmp_project_dir: Path,
) -> None:
    mock_show_app_info = mocker.patch("litestar.cli.commands.core.show_app_info")
    args = []
    if custom_app_file:
        args.extend(["--app", f"{custom_app_file.stem}:app"])
    if app_dir is not None:
        args.extend(["--app-dir", str(Path(tmp_project_dir / app_dir))])
    args.extend(["run"])

    if reload:
        if set_in_env:
            monkeypatch.setenv("LITESTAR_RELOAD", "true")
        else:
            args.append("--reload")
    else:
        reload = False

    if port:
        if set_in_env:
            monkeypatch.setenv("LITESTAR_PORT", str(port))
        else:
            args.extend(["--port", str(port)])
    else:
        port = 8000

    if host:
        if set_in_env:
            monkeypatch.setenv("LITESTAR_HOST", host)
        else:
            args.extend(["--host", host])
    else:
        host = "127.0.0.1"

    if web_concurrency is not None:
        if set_in_env:
            monkeypatch.setenv("WEB_CONCURRENCY", str(web_concurrency))
        else:
            args.extend(["--web-concurrency", str(web_concurrency)])
    else:
        web_concurrency = 1

    if reload_dir is not None:
        if set_in_env:
            monkeypatch.setenv("LITESTAR_RELOAD_DIRS", ",".join(reload_dir))
        else:
            args.extend([f"--reload-dir={s}" for s in reload_dir])

    path = create_app_file(custom_app_file or "app.py", subdir=app_dir)

    result = runner.invoke(cli_command, args)

    assert result.exception is None
    assert result.exit_code == 0

    if reload or reload_dir or web_concurrency > 1:
        expected_args = [sys.executable, "-m", "uvicorn", f"{path.stem}:app", f"--host={host}", f"--port={port}"]
        if reload or reload_dir:
            expected_args.append("--reload")
        if web_concurrency:
            expected_args.append(f"--workers={web_concurrency}")
        if reload_dir:
            expected_args.extend([f"--reload-dir={s}" for s in reload_dir])
        mock_subprocess_run.assert_called_once()
        assert sorted(mock_subprocess_run.call_args_list[0].args[0]) == sorted(expected_args)
    else:
        mock_subprocess_run.assert_not_called()
        mock_uvicorn_run.assert_called_once_with(app=f"{path.stem}:app", host=host, port=port, factory=False)

    mock_show_app_info.assert_called_once()


@pytest.mark.parametrize(
    "file_name,file_content,factory_name",
    [
        ("_create_app.py", CREATE_APP_FILE_CONTENT, "create_app"),
        ("_generic_app_factory.py", GENERIC_APP_FACTORY_FILE_CONTENT, "any_name"),
        ("_generic_app_factory_string_ann.py", GENERIC_APP_FACTORY_FILE_CONTENT_STRING_ANNOTATION, "any_name"),
    ],
    ids=["create-app", "generic", "generic-string-annotated"],
)
def test_run_command_with_autodiscover_app_factory(
    runner: CliRunner,
    mock_uvicorn_run: MagicMock,
    file_name: str,
    file_content: str,
    factory_name: str,
    patch_autodiscovery_paths: Callable[[List[str]], None],
    create_app_file: CreateAppFileFixture,
) -> None:
    patch_autodiscovery_paths([file_name])
    path = create_app_file(file_name, content=file_content)
    result = runner.invoke(cli_command, "run")

    assert result.exception is None
    assert result.exit_code == 0

    mock_uvicorn_run.assert_called_once_with(
        app=f"{path.stem}:{factory_name}",
        host="127.0.0.1",
        port=8000,
        factory=True,
    )


def test_run_command_with_app_factory(
    runner: CliRunner, mock_uvicorn_run: MagicMock, create_app_file: CreateAppFileFixture
) -> None:
    path = create_app_file("_create_app_with_path.py", content=CREATE_APP_FILE_CONTENT)
    app_path = f"{path.stem}:create_app"
    result = runner.invoke(cli_command, ["--app", app_path, "run"])

    assert result.exception is None
    assert result.exit_code == 0

    mock_uvicorn_run.assert_called_once_with(
        app=str(app_path),
        host="127.0.0.1",
        port=8000,
        factory=True,
    )


@pytest.fixture()
def unset_env() -> Generator[None, None, None]:
    initial_env = {**os.environ}
    yield
    for key in os.environ.keys() - initial_env.keys():
        del os.environ[key]

    os.environ.update(initial_env)


@pytest.mark.usefixtures("mock_uvicorn_run", "unset_env")
def test_run_command_debug(
    app_file: Path, runner: CliRunner, monkeypatch: MonkeyPatch, create_app_file: CreateAppFileFixture
) -> None:
    monkeypatch.delenv("LITESTAR_DEBUG", raising=False)
    path = create_app_file("_create_app_with_path.py", content=CREATE_APP_FILE_CONTENT)
    app_path = f"{path.stem}:create_app"
    result = runner.invoke(cli_command, ["--app", app_path, "run", "--debug"])

    assert result.exit_code == 0
    assert os.getenv("LITESTAR_DEBUG") == "1"


@pytest.mark.usefixtures("mock_uvicorn_run", "unset_env")
def test_run_command_pdb(
    app_file: Path,
    runner: CliRunner,
    monkeypatch: MonkeyPatch,
    create_app_file: CreateAppFileFixture,
) -> None:
    monkeypatch.delenv("LITESTAR_PDB", raising=False)
    path = create_app_file("_create_app_with_path.py", content=CREATE_APP_FILE_CONTENT)
    app_path = f"{path.stem}:create_app"

    with pytest.warns(LitestarWarning):
        result = runner.invoke(cli_command, ["--app", app_path, "run", "--pdb"])

    assert result.exit_code == 0
    assert os.getenv("LITESTAR_PDB") == "1"


@pytest.mark.parametrize("short", [True, False])
def test_version_command(short: bool, runner: CliRunner) -> None:
    result = runner.invoke(cli_command, "version --short" if short else "version")

    assert result.output.strip() == litestar_version.formatted(short=short)
