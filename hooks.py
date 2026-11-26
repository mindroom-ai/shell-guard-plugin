# ruff: noqa: INP001
"""Shell command guard — blocks dangerous commands.

Blocks agents from running shell commands matching configured regex patterns
(by default, stopping or disabling the mindroom-chat service).
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import TYPE_CHECKING

from mindroom.plugin_api import ToolBeforeCallContext, hook

if TYPE_CHECKING:
    from collections.abc import Mapping

_log = logging.getLogger(__name__)

# Default patterns block stopping or disabling mindroom-chat (restarts are allowed).
_DEFAULT_BLOCKED_PATTERN_STRINGS: tuple[str, ...] = (r"systemctl\s+(stop|disable)\s+mindroom-chat",)
_DEFAULT_REASON = (
    "Agents must NEVER stop or disable the mindroom-chat service — "
    "doing so leaves the service offline or disabled until a human manually intervenes. "
    "Do NOT retry this command or attempt workarounds."
)


@lru_cache(maxsize=256)
def _compile_pattern(pattern: str) -> re.Pattern[str]:
    """Compile and cache one regex pattern."""
    return re.compile(pattern)


_DEFAULT_BLOCKED_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    _compile_pattern(pattern) for pattern in _DEFAULT_BLOCKED_PATTERN_STRINGS
)


def _blocked_patterns(settings: Mapping[str, object] | None) -> tuple[re.Pattern[str], ...]:
    """Return compiled blocked patterns from plugin settings, or the defaults."""
    if not settings or "blocked_patterns" not in settings or settings["blocked_patterns"] is None:
        return _DEFAULT_BLOCKED_PATTERNS

    raw = settings["blocked_patterns"]
    if not isinstance(raw, (list, tuple)):
        _log.warning("shell-guard: blocked_patterns must be a list of regex strings; using defaults")
        return _DEFAULT_BLOCKED_PATTERNS
    if not raw:
        return ()

    compiled: list[re.Pattern[str]] = []
    for entry in raw:
        if not isinstance(entry, str) or not entry.strip():
            _log.warning("shell-guard: ignoring invalid blocked_patterns entry %r", entry)
            continue
        try:
            compiled.append(_compile_pattern(entry))
        except re.error as exc:
            _log.warning("shell-guard: ignoring invalid regex %r: %s", entry, exc)

    if not compiled:
        _log.warning("shell-guard: no valid patterns in blocked_patterns; falling back to defaults")
        return _DEFAULT_BLOCKED_PATTERNS
    return tuple(compiled)


def _decline_detail(settings: Mapping[str, object] | None) -> str:
    """Return the configured decline reason suffix, or the default message."""
    if settings:
        configured = settings.get("reason")
        if isinstance(configured, str) and configured.strip():
            return configured.strip()
    return _DEFAULT_REASON


def _command_text(args_list: list[str] | str) -> str:
    """Return one readable command string from supported shell arguments."""
    return args_list if isinstance(args_list, str) else " ".join(str(a) for a in args_list)


def _is_blocked(
    args_list: list[str] | str,
    patterns: tuple[re.Pattern[str], ...] = _DEFAULT_BLOCKED_PATTERNS,
) -> str | None:
    """Check if a command matches any blocked pattern.

    Returns the matched pattern string if blocked, None otherwise.
    """
    cmd = _command_text(args_list)
    for pattern in patterns:
        if pattern.search(cmd):
            return pattern.pattern
    return None


@hook(
    event="tool:before_call",
    name="shell-guard",
    timeout_ms=1000,
)
async def guard_shell_commands(ctx: ToolBeforeCallContext) -> None:
    """Block dangerous shell commands before execution."""
    if ctx.tool_name != "run_shell_command":
        return

    args = ctx.arguments.get("args", [])
    if not args:
        return

    patterns = _blocked_patterns(ctx.settings)
    matched = _is_blocked(args, patterns)
    if matched:
        command = _command_text(args)
        detail = _decline_detail(ctx.settings)
        reason = f"🚫 BLOCKED: You attempted `{command}` which matches forbidden pattern `{matched}`. {detail}"
        _log.warning(
            "Shell guard blocked command: args=%s, pattern=%s, agent=%s",
            args,
            matched,
            ctx.agent_name,
        )
        ctx.decline(reason)
