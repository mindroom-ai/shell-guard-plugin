# ruff: noqa: INP001
"""Behavior tests for shell-guard plugin."""

from __future__ import annotations

import sys
from importlib import util
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from mindroom.constants import resolve_runtime_paths
from mindroom.hooks.decorators import get_hook_metadata
from mindroom.plugin_api import Config, ToolBeforeCallContext

if TYPE_CHECKING:
    from types import ModuleType


def _load_hooks_module() -> ModuleType:
    hooks_path = Path(__file__).resolve().parents[1] / "hooks.py"
    module_name = "mindroom_test_shell_guard_hooks"
    spec = util.spec_from_file_location(module_name, hooks_path)
    assert spec is not None
    assert spec.loader is not None
    module = util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


hooks = _load_hooks_module()
# The runtime paths a before-call context carries; the guard never reads them.
_RUNTIME_PATHS = resolve_runtime_paths(config_path=Path("/nonexistent/shell-guard/config.yaml"), process_env={})


def _context(
    tool_name: str,
    args: list[str] | str,
    *,
    settings: dict[str, Any] | None = None,
) -> ToolBeforeCallContext:
    return ToolBeforeCallContext(
        tool_name=tool_name,
        arguments={"args": args},
        agent_name="code",
        room_id="!room:localhost",
        thread_id="$thread-root",
        requester_id="@user:localhost",
        session_id="session-1",
        config=Config(),
        runtime_paths=_RUNTIME_PATHS,
        correlation_id="corr-shell-guard",
        settings=settings or {},
    )


def test_hook_metadata_targets_tool_preflight() -> None:
    """Guard should remain a fast tool pre-call hook."""
    metadata = get_hook_metadata(hooks.guard_shell_commands)

    assert metadata is not None
    assert metadata.event_name == "tool:before_call"
    assert metadata.hook_name == "shell-guard"
    assert metadata.timeout_ms == 1000


@pytest.mark.parametrize(
    "args",
    [
        ["systemctl", "stop", "mindroom-chat"],
        "systemctl stop mindroom-chat",
        ["sudo", "systemctl", "stop", "mindroom-chat"],
        "sudo systemctl stop mindroom-chat",
        ["bash", "-lc", "systemctl disable mindroom-chat"],
    ],
)
@pytest.mark.asyncio
async def test_dangerous_commands_are_declined(args: list[str] | str) -> None:
    """Direct, sudo, and wrapped service mutations should all be blocked."""
    ctx = _context("run_shell_command", args)

    await hooks.guard_shell_commands(ctx)

    assert ctx.declined is True
    assert "🚫 BLOCKED" in ctx.decline_reason
    command = args if isinstance(args, str) else " ".join(args)
    assert f"You attempted `{command}`" in ctx.decline_reason


@pytest.mark.parametrize(
    "args",
    [
        ["systemctl", "status", "mindroom-chat"],
        ["systemctl", "restart", "mindroom-chat"],
        "systemctl restart mindroom-chat",
        ["sudo", "systemctl", "restart", "mindroom-chat"],
        ["bash", "-lc", "systemctl restart mindroom-chat"],
    ],
)
@pytest.mark.asyncio
async def test_safe_shell_command_is_allowed(args: list[str] | str) -> None:
    """Read-only commands and restarts should remain executable by default."""
    ctx = _context("run_shell_command", args)

    await hooks.guard_shell_commands(ctx)

    assert ctx.declined is False
    assert ctx.decline_reason == ""


@pytest.mark.asyncio
async def test_non_shell_tool_is_ignored() -> None:
    """Blocked-looking arguments on another tool should not be declined."""
    ctx = _context("other_tool", ["systemctl", "stop", "mindroom-chat"])

    await hooks.guard_shell_commands(ctx)

    assert ctx.declined is False


@pytest.mark.asyncio
async def test_custom_blocked_patterns_and_reason() -> None:
    """Custom settings override default patterns and decline reason."""
    settings = {
        "blocked_patterns": [r"systemctl\s+(restart|stop)\s+my-service", r"rm\s+-rf\s+/"],
        "reason": "Ask an operator before touching my-service.",
    }

    blocked = _context("run_shell_command", "sudo systemctl restart my-service", settings=settings)
    await hooks.guard_shell_commands(blocked)
    assert blocked.declined is True
    assert "Ask an operator before touching my-service." in blocked.decline_reason

    # Default mindroom-chat pattern is replaced when blocked_patterns is set.
    replaced = _context("run_shell_command", "systemctl stop mindroom-chat", settings=settings)
    await hooks.guard_shell_commands(replaced)
    assert replaced.declined is False


@pytest.mark.asyncio
async def test_empty_blocked_patterns_allows_everything() -> None:
    """An explicit empty blocked_patterns list disables blocking."""
    ctx = _context("run_shell_command", "systemctl stop mindroom-chat", settings={"blocked_patterns": []})

    await hooks.guard_shell_commands(ctx)

    assert ctx.declined is False


@pytest.mark.parametrize(
    "bad_settings",
    [
        {"blocked_patterns": "not-a-list"},
        {"blocked_patterns": ["[unclosed-regex"]},
        {"blocked_patterns": [123, "   "]},
    ],
)
@pytest.mark.asyncio
async def test_invalid_blocked_patterns_falls_back_to_defaults(bad_settings: dict[str, Any]) -> None:
    """Malformed blocked_patterns settings should fail safe to default rules."""
    ctx = _context("run_shell_command", "systemctl stop mindroom-chat", settings=bad_settings)

    await hooks.guard_shell_commands(ctx)

    assert ctx.declined is True


@pytest.mark.asyncio
async def test_partial_invalid_blocked_patterns_keeps_valid_ones() -> None:
    """Valid patterns in blocked_patterns still apply when another entry is invalid."""
    settings = {"blocked_patterns": ["[unclosed-regex", r"docker\s+stop"]}

    blocked = _context("run_shell_command", "docker stop db", settings=settings)
    await hooks.guard_shell_commands(blocked)
    assert blocked.declined is True
