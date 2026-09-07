"""Sandboxed laptop operations (spec section 16).

Every function re-validates the target path/command against the matched
PolicyRule itself — belt-and-suspenders on top of the classify() check
already done by the caller — because this module is the actual last line
before anything touches the filesystem or a subprocess, and it must never
assume its caller got that right.
"""

from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent.policy.engine import PolicyRule, is_within


class OperationDeniedError(Exception):
    """Raised when a request passed classify() but still fails this
    module's own re-check — should never normally happen, but if it does,
    deny rather than proceed."""


class OperationError(Exception):
    """A well-formed but failed operation (bad path, non-zero exit, etc.)."""


@dataclass
class OperationResult:
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    result: dict[str, Any] | None = None


def _require_within_allowed_paths(path_str: str, rule: PolicyRule) -> Path:
    if not rule.allowed_paths:
        raise OperationDeniedError(f"operation '{rule.operation}' has no allowed_paths configured")
    if not any(is_within(path_str, allowed) for allowed in rule.allowed_paths):
        raise OperationDeniedError(f"path '{path_str}' is outside allowed_paths for '{rule.operation}'")
    return Path(path_str).expanduser().resolve()


def _require_allowed_command(command: str, rule: PolicyRule) -> list[str]:
    if not rule.allowed_commands:
        raise OperationDeniedError(f"operation '{rule.operation}' has no allowed_commands configured")
    parts = shlex.split(command)
    if not parts or parts[0] not in rule.allowed_commands:
        raise OperationDeniedError(f"command '{command}' is not in allowed_commands for '{rule.operation}'")
    return parts


def read_file(parameters: dict[str, Any], rule: PolicyRule, max_bytes: int, **_: Any) -> OperationResult:
    path = _require_within_allowed_paths(str(parameters.get("path", "")), rule)
    if not path.is_file():
        raise OperationError(f"'{path}' is not a file")
    data = path.read_bytes()[: max_bytes + 1]
    if len(data) > max_bytes:
        raise OperationError(f"file exceeds max_read_file_bytes ({max_bytes})")
    return OperationResult(stdout=data.decode("utf-8", errors="replace"), exit_code=0,
                           result={"path": str(path), "bytes": len(data)})


def list_directory(parameters: dict[str, Any], rule: PolicyRule, **_: Any) -> OperationResult:
    path = _require_within_allowed_paths(str(parameters.get("path", "")), rule)
    if not path.is_dir():
        raise OperationError(f"'{path}' is not a directory")
    entries = sorted(
        (
            {"name": p.name, "type": "dir" if p.is_dir() else "file", "size": p.stat().st_size if p.is_file() else None}
            for p in path.iterdir()
        ),
        key=lambda e: e["name"],
    )
    return OperationResult(exit_code=0, result={"path": str(path), "entries": entries})


def write_file(parameters: dict[str, Any], rule: PolicyRule, **_: Any) -> OperationResult:
    path = _require_within_allowed_paths(str(parameters.get("path", "")), rule)
    content = parameters.get("content", "")
    mode = parameters.get("mode", "overwrite")
    if mode not in ("overwrite", "append"):
        raise OperationError(f"invalid write mode '{mode}' (must be 'overwrite' or 'append')")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a" if mode == "append" else "w", encoding="utf-8") as fh:
        written = fh.write(content)
    return OperationResult(exit_code=0, result={"path": str(path), "bytes_written": written, "mode": mode})


def _run_subprocess(argv: list[str], working_directory: Path, timeout: int) -> OperationResult:
    try:
        proc = subprocess.run(  # noqa: S603 - argv is shlex-split and command-whitelisted by the caller
            argv, cwd=str(working_directory), capture_output=True, text=True, timeout=timeout, shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise OperationError(f"command timed out after {timeout}s") from exc
    except OSError as exc:
        raise OperationError(f"failed to execute command: {exc}") from exc
    return OperationResult(stdout=proc.stdout, stderr=proc.stderr, exit_code=proc.returncode)


def run_command(parameters: dict[str, Any], rule: PolicyRule, timeout: int, **_: Any) -> OperationResult:
    command = str(parameters.get("command", ""))
    argv = _require_allowed_command(command, rule)
    working_directory = _require_within_allowed_paths(
        str(parameters.get("working_directory") or rule.allowed_paths[0]), rule,
    )
    return _run_subprocess(argv, working_directory, timeout)


def run_script(parameters: dict[str, Any], rule: PolicyRule, timeout: int, **_: Any) -> OperationResult:
    script_path = _require_within_allowed_paths(str(parameters.get("path", "")), rule)
    if not script_path.is_file():
        raise OperationError(f"script '{script_path}' does not exist")
    args = [str(a) for a in parameters.get("args", [])]
    return _run_subprocess([str(script_path), *args], script_path.parent, timeout)


def run_tests(parameters: dict[str, Any], rule: PolicyRule, timeout: int, **_: Any) -> OperationResult:
    # Same execution mechanics as run_command; kept as a distinct operation
    # purely so policies.yaml can classify test runs differently from
    # arbitrary commands (spec section 16 lists them separately).
    return run_command(parameters, rule, timeout)


OPERATIONS = {
    "read_file": read_file,
    "list_directory": list_directory,
    "write_file": write_file,
    "run_command": run_command,
    "run_script": run_script,
    "run_tests": run_tests,
}
