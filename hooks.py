"""Shell command guard — blocks dangerous commands.

Blocks agents from restarting the mindroom-chat service.
"""

from __future__ import annotations

import logging
import re

from mindroom.hooks import ToolBeforeCallContext, hook

_log = logging.getLogger(__name__)

# Only block direct service restarts of mindroom-chat
_BLOCKED_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"systemctl\s+(restart|stop|disable)\s+mindroom-chat"),
    re.compile(r"sudo\s+systemctl\s+(restart|stop|disable)\s+mindroom-chat"),
]


def _is_blocked(args_list: list[str]) -> str | None:
    """Check if a command matches any blocked pattern.

    Returns the matched pattern string if blocked, None otherwise.
    """
    cmd = " ".join(str(a) for a in args_list)
    for pattern in _BLOCKED_PATTERNS:
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

    matched = _is_blocked(args)
    if matched:
        reason = (
            f"🚫 BLOCKED: You attempted `{' '.join(str(a) for a in args)}` "
            f"which matches forbidden pattern `{matched}`. "
            f"Agents must NEVER restart, stop, or disable the mindroom-chat "
            f"service — doing so kills your own process and leaves the system "
            f"unrecoverable until Bas manually intervenes. "
            f"Only Bas should restart this service by hand. "
            f"Do NOT retry this command or attempt workarounds."
        )
        _log.warning(
            "Shell guard blocked command: args=%s, pattern=%s, agent=%s",
            args,
            matched,
            ctx.agent_name,
        )
        ctx.decline(reason)
