# Shell Guard

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-plugins-blue)](https://docs.mindroom.chat/plugins/)
[![Hooks](https://img.shields.io/badge/docs-hooks-blue)](https://docs.mindroom.chat/hooks/)

<img src="https://media.githubusercontent.com/media/mindroom-ai/mindroom/refs/heads/main/frontend/public/logo.png" alt="MindRoom Logo" align="right" width="120" />

Block specific tool calls so [MindRoom](https://github.com/mindroom-ai/mindroom) agents cannot run dangerous shell commands.

MindRoom is often used to develop and operate MindRoom itself. That means agents may legitimately run shell commands, edit files, and inspect services. This plugin narrows one critical safety gap: it prevents an agent from restarting, stopping, or disabling the `mindroom-chat` service that it is currently running inside.

## Features

- Intercepts `run_shell_command` before the shell command executes
- Blocks `systemctl restart`, `stop`, and `disable` for `mindroom-chat`
- Catches both direct and `sudo` variants of those commands
- Declines the tool call with an explicit explanation instead of failing silently
- Keeps the blocked command list local and easy to extend in `_BLOCKED_PATTERNS`

## How It Works

1. An agent invokes `run_shell_command`.
2. The `shell-guard` hook inspects the tool arguments during `tool:before_call`.
3. If the command matches a blocked regex, the hook declines the call immediately.
4. If nothing matches, the shell tool proceeds normally.

## Hooks

| Hook | Event | Purpose |
|------|-------|---------|
| `shell-guard` | `tool:before_call` | Intercept and block dangerous shell commands before execution |

## Customization

Blocked by default:

- `systemctl restart mindroom-chat`
- `systemctl stop mindroom-chat`
- `systemctl disable mindroom-chat`
- The same commands prefixed with `sudo`

To block additional commands, add more regex patterns to `_BLOCKED_PATTERNS` in [hooks.py](hooks.py).

## Setup

1. Copy this plugin to `~/.mindroom/plugins/shell-guard`.
2. Add the plugin to `config.yaml`:
   ```yaml
   plugins:
     - path: plugins/shell-guard
   ```
3. Restart MindRoom.

No agent tools or plugin settings are required.
