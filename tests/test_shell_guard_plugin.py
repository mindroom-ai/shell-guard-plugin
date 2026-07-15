# ruff: noqa: INP001
"""Behavior tests for shell-guard plugin."""

from __future__ import annotations

import sys
from importlib import util
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from mindroom.hooks import ToolBeforeCallContext
from mindroom.hooks.decorators import get_hook_metadata

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


def _context(tool_name: str, args: list[str]) -> ToolBeforeCallContext:
    return ToolBeforeCallContext(
        tool_name=tool_name,
        arguments={"args": args},
        agent_name="code",
        room_id="!room:localhost",
        thread_id="$thread-root",
        requester_id="@user:localhost",
        session_id="session-1",
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
        ["systemctl", "restart", "mindroom-chat"],
        ["sudo", "systemctl", "stop", "mindroom-chat"],
        ["bash", "-lc", "systemctl disable mindroom-chat"],
    ],
)
@pytest.mark.asyncio
async def test_dangerous_commands_are_declined(args: list[str]) -> None:
    """Direct, sudo, and wrapped service mutations should all be blocked."""
    ctx = _context("run_shell_command", args)

    await hooks.guard_shell_commands(ctx)

    assert ctx.declined is True
    assert "🚫 BLOCKED" in ctx.decline_reason
    assert "mindroom-chat" in ctx.decline_reason


@pytest.mark.asyncio
async def test_safe_shell_command_is_allowed() -> None:
    """Unrelated shell commands should remain executable."""
    ctx = _context("run_shell_command", ["systemctl", "status", "mindroom-chat"])

    await hooks.guard_shell_commands(ctx)

    assert ctx.declined is False
    assert ctx.decline_reason == ""


@pytest.mark.asyncio
async def test_non_shell_tool_is_ignored() -> None:
    """Blocked-looking arguments on another tool should not be declined."""
    ctx = _context("other_tool", ["systemctl", "restart", "mindroom-chat"])

    await hooks.guard_shell_commands(ctx)

    assert ctx.declined is False
