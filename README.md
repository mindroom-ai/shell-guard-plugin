# shell-guard

MindRoom plugin that blocks dangerous shell commands from being executed by agents.

## What it does

Hooks into `tool:pre_execute` to intercept shell commands before execution. Currently blocks agents from restarting, stopping, or disabling the `mindroom-chat` service via `systemctl`.

## Setup

1. Copy or symlink to `~/.mindroom-chat/plugins/shell-guard`
2. Add to `config.yaml`:
   ```yaml
   plugins:
     - path: plugins/shell-guard
   ```
3. Restart MindRoom.

## Blocked patterns

- `systemctl restart mindroom-chat`
- `systemctl stop mindroom-chat`
- `systemctl disable mindroom-chat`
- All of the above with `sudo` prefix