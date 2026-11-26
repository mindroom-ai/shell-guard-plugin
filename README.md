# Shell Guard

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/mindroom-ai/shell-guard-plugin/actions/workflows/plugin-ci.yml/badge.svg)](https://github.com/mindroom-ai/shell-guard-plugin/actions/workflows/plugin-ci.yml)
[![Docs](https://img.shields.io/badge/docs-plugins-blue)](https://docs.mindroom.chat/plugins/)
[![Hooks](https://img.shields.io/badge/docs-hooks-blue)](https://docs.mindroom.chat/hooks/)

<picture>
  <source media="(prefers-reduced-motion: no-preference)" srcset="https://raw.githubusercontent.com/mindroom-ai/mindroom/main/assets/logo/logo-mark-animated.svg" />
  <img src="https://raw.githubusercontent.com/mindroom-ai/mindroom/main/assets/logo/logo-mark.svg" alt="MindRoom Logo" align="right" width="120" />
</picture>

A [MindRoom](https://github.com/mindroom-ai/mindroom) hook plugin that blocks agents from running dangerous shell commands matching configured regex patterns (by default, stopping or disabling the `mindroom-chat` systemd service).

When an agent invokes `run_shell_command` with a blocked command, the hook intercepts it before execution and declines the call with an explicit explanation:

```text
run_shell_command(args=["systemctl", "stop", "mindroom-chat"])
→ 🚫 BLOCKED: You attempted `systemctl stop mindroom-chat` which matches forbidden pattern `systemctl\s+(stop|disable)\s+mindroom-chat`. Agents must NEVER stop or disable the mindroom-chat service — doing so leaves the service offline or disabled until a human manually intervenes. Do NOT retry this command or attempt workarounds.
```

- **Pre-execution check:** intercepts `run_shell_command` on `tool:before_call` (1-second hook timeout) before anything runs.
- **Catches common variants:** matches direct commands, `sudo` invocations, and shell wrappers such as `bash -lc`.
- **Configurable in YAML:** customize `blocked_patterns` and `reason` via plugin `settings:` without forking `hooks.py`.
- **Allowed commands pass through:** commands like `systemctl status mindroom-chat`, `systemctl restart mindroom-chat`, and all other tools run normally by default.

## Quick start

```bash
mindroom plugins install shell-guard-plugin
```

```yaml
plugins:
  - path: plugins/shell-guard-plugin
    required: true  # refuse to start with the guard skipped
```

Update later with `mindroom plugins update shell-guard-plugin`.
Needs MindRoom v2026.11.187 or later (plugin API 1.2).

## Settings

All settings are optional. With no `settings:` block, the guard blocks `systemctl stop mindroom-chat` and `systemctl disable mindroom-chat` (direct, with `sudo`, or inside a shell wrapper) and allows `systemctl restart mindroom-chat`.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `blocked_patterns` | `list[str]` | `['systemctl\s+(stop\|disable)\s+mindroom-chat']` | Regex patterns checked via `re.search` against the command text. Replaces the default list when set; pass `[]` to disable blocking. Invalid entries in a mixed list are skipped while valid ones still apply; a non-list value or a non-empty list with no valid patterns falls back to the defaults. |
| `reason` | `str` | Built-in warning | Custom explanation appended to the decline message. |

```yaml
plugins:
  - path: plugins/shell-guard-plugin
    required: true
    settings:
      blocked_patterns:
        - 'systemctl\s+(restart|stop|disable)\s+my-mindroom-service'
        - 'rm\s+-rf\s+/'
      reason: "Ask an operator before running destructive service or filesystem commands."
```

<details>
<summary><b>Scope limits</b></summary>

- **Accidental-footgun guardrail, not a security sandbox:** the hook runs a case-sensitive regex substring check (`re.Pattern.search`) against `run_shell_command`'s `args` argument (joined with spaces when passed as a list).
- **Single tool only:** only `run_shell_command` is inspected; other tools, indirect scripts, or altered invocations (flags between `systemctl` and the subcommand, shell variables, alternate unit names, `kill`, etc.) are not matched unless covered by your configured patterns.

</details>

## Hooks

| Hook | Event | Purpose |
|------|-------|---------|
| `shell-guard` | `tool:before_call` | Inspect `run_shell_command` arguments and decline matching commands before execution |
