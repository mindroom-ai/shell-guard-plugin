# Shell Guard

**Example of how to deny specific tool calls in MindRoom.** Use this as a template for building your own tool-call guards.

MindRoom is frequently used to develop MindRoom itself — agents can run shell commands, edit source files, and manage services. This plugin ensures the agent can do *anything* except restart itself. An agent that restarts its own service kills all active sessions, ongoing conversations, and streaming responses across every room.

## What it demonstrates

- Hooking `tool:before_call` to intercept tool invocations before execution
- Pattern-matching on tool arguments to selectively block dangerous commands
- Returning a decline message that explains *why* the call was blocked

## Blocked patterns

- `systemctl restart mindroom-chat`
- `systemctl stop mindroom-chat`
- `systemctl disable mindroom-chat`
- All of the above with `sudo` prefix

## Extending

Add your own patterns to `_BLOCKED_PATTERNS` in `hooks.py`. For example, you could block `rm -rf /`, `DROP TABLE`, or any other command you want to prevent agents from running.

## Setup

1. Copy to `~/.mindroom-chat/plugins/shell-guard`
2. Add to `config.yaml`:
   ```yaml
   plugins:
     - path: plugins/shell-guard
   ```
3. Restart MindRoom