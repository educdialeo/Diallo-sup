"""Tests de structure/syntaxe du plist launchd (sous-phase 3.4.B).

Valide le contenu sans dependre de launchctl (CI-safe) : parsing via plistlib.
"""

import plistlib
from pathlib import Path

import pytest

PLIST_PATH = Path(__file__).resolve().parents[1] / "ops" / "com.diallosup.uvicorn.plist"
REPO_DIR = "/Users/serveur/Projects/Diallo-sup"


@pytest.fixture(scope="module")
def plist() -> dict:
    with PLIST_PATH.open("rb") as fh:
        return plistlib.load(fh)


def test_plist_exists_and_parses(plist):
    assert isinstance(plist, dict)


def test_label(plist):
    assert plist["Label"] == "com.diallosup.uvicorn"


def test_program_arguments(plist):
    args = plist["ProgramArguments"]
    assert args[0] == f"{REPO_DIR}/.venv/bin/uvicorn"
    assert args[1] == "app.main:app"
    assert "--host" in args and args[args.index("--host") + 1] == "0.0.0.0"
    assert "--port" in args and args[args.index("--port") + 1] == "8000"


def test_working_directory_is_repo(plist):
    # Garde-fou : la base SQLite relative dependant du dossier de travail.
    assert plist["WorkingDirectory"] == REPO_DIR


def test_run_at_load_and_keepalive(plist):
    assert plist["RunAtLoad"] is True
    assert plist["KeepAlive"] is True


def test_process_type_interactive(plist):
    assert plist["ProcessType"] == "Interactive"


def test_environment_variables(plist):
    env = plist["EnvironmentVariables"]
    assert env["PYTHONUNBUFFERED"] == "1"
    assert env["PYTHONPATH"] == REPO_DIR


def test_logs_paths(plist):
    expected = "/Users/serveur/Library/Logs/diallosup-uvicorn.log"
    assert plist["StandardOutPath"] == expected
    assert plist["StandardErrorPath"] == expected
