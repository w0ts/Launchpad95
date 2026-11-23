"""Live logs a compile-time SyntaxWarning (e.g. `value is 0`) as a RemoteScriptError line:
every script module must compile without one."""
import warnings
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
MODULES = sorted(REPO.glob("*.py"))


@pytest.mark.parametrize("path", MODULES, ids=lambda p: p.name)
def test_module_compiles_without_syntax_warnings(path):
	with warnings.catch_warnings():
		warnings.simplefilter("error", SyntaxWarning)
		compile(path.read_text(), str(path), "exec")
