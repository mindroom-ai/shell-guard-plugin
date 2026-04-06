# Shell Guard

[![Docs](https://img.shields.io/badge/docs-plugins-blue)](https://docs.mindroom.chat/plugins/)
[![Hooks](https://img.shields.io/badge/docs-hooks-blue)](https://docs.mindroom.chat/hooks/)

<img src="https://media.githubusercontent.com/media/mindroom-ai/mindroom/refs/heads/main/frontend/public/logo.png" alt="MindRoom Logo" align="right" width="120" />

Block specific tool calls to prevent [MindRoom](https://github.com/mindroom-ai/mindroom) agents from running dangerous commands.

MindRoom is frequently used to develop MindRoom itself — agents can run shell commands, edit source files, and manage services. This plugin ensures the agent can do *anything* except restart its own service, which would kill all active sessions and conversations.

## How it works

1. Agent invokes `run_shell_command` with some arguments
2. The `tool:before_call` hook checks the arguments against a list of blocked patterns
3. If a match is found, the call is declined with a message explaining why

Blocked by default: `systemctl restart/stop/disable mindroom-chat` (with or without `sudo`). Add your own patterns to `_BLOCKED_PATTERNS` in `hooks.py`.

## Hooks

| Hook | Event | Purpose |
|------|-------|---------|
| `shell_guard` | `tool:before_call` | Intercept and block dangerous shell commands |

## Setup

1. Copy to `~/.mindroom/plugins/shell-guard`
2. Add to `config.yaml`:
   ```yaml
   plugins:
     - path: plugins/shell-guard
   ```
3. Restart MindRoom