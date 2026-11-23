# Shell Guard

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/mindroom-ai/shell-guard-plugin/actions/workflows/plugin-ci.yml/badge.svg)](https://github.com/mindroom-ai/shell-guard-plugin/actions/workflows/plugin-ci.yml)
[![Docs](https://img.shields.io/badge/docs-plugins-blue)](https://docs.mindroom.chat/plugins/)
[![Hooks](https://img.shields.io/badge/docs-hooks-blue)](https://docs.mindroom.chat/hooks/)

<picture>
  <source media="(prefers-reduced-motion: no-preference)" srcset="https://raw.githubusercontent.com/mindroom-ai/mindroom/main/assets/logo/logo-mark-animated.svg" />
  <img src="https://raw.githubusercontent.com/mindroom-ai/mindroom/main/assets/logo/logo-mark.svg" alt="MindRoom Logo" align="right" width="120" />
</picture>

A [MindRoom](https://github.com/mindroom-ai/mindroom) hook plugin that stops agents from accidentally restarting, stopping, or disabling the `mindroom-chat` systemd service they run inside.

When an agent invokes `run_shell_command` with a blocked command, the hook intercepts it before execution and declines the call with an explicit explanation:

```text
run_shell_command(args=["systemctl", "restart", "mindroom-chat"])
→ 🚫 BLOCKED: You attempted `systemctl restart mindroom-chat` which matches forbidden pattern `systemctl\s+(restart|stop|disable)\s+mindroom-chat`. Agents must NEVER restart, stop, or disable the mindroom-chat service — doing so kills your own process and leaves the system unrecoverable until Bas manually intervenes. Only Bas should restart this service by hand. Do NOT retry this command or attempt workarounds.
```

- **Pre-execution check:** intercepts `run_shell_command` on `tool:before_call` (1-second hook timeout) before anything runs.
- **Catches common variants:** matches direct commands, `sudo` invocations, and shell wrappers such as `bash -lc`.
- **Safe commands pass through:** read-only commands like `systemctl status mindroom-chat` and all other tools run normally.

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

This plugin does not read YAML `settings:` yet—no extra config keys or agent tools are needed. The default unit name (`mindroom-chat`), regex patterns (`_BLOCKED_PATTERNS`), and decline message live directly in [hooks.py](hooks.py).

Blocked by default (direct, with `sudo`, or inside a shell wrapper):

- `systemctl restart mindroom-chat`
- `systemctl stop mindroom-chat`
- `systemctl disable mindroom-chat`

<details>
<summary><b>Customization and limits</b></summary>

### Customizing rules and message

If your service uses a different unit name or you want to block other commands, edit `_BLOCKED_PATTERNS` and the `reason` string in [hooks.py](hooks.py) (in your installed `plugins/shell-guard-plugin/` directory, or a manual checkout placed at `plugins/shell-guard-plugin` next to your `config.yaml`):

```python
_BLOCKED_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"systemctl\s+(restart|stop|disable)\s+my-mindroom-service"),
    re.compile(r"sudo\s+systemctl\s+(restart|stop|disable)\s+my-mindroom-service"),
]
```

Running `mindroom plugins update shell-guard-plugin` replaces the vendored copy from upstream, so keep custom rules in your own fork or manual checkout.

### Scope limits

- **Accidental-footgun guardrail, not a security sandbox:** the hook runs a case-sensitive regex substring check (`re.Pattern.search`) against `run_shell_command`'s `args` argument (joined with spaces when passed as a list).
- **Single tool only:** only `run_shell_command` is inspected; other tools, indirect scripts, or altered invocations (flags between `systemctl` and the subcommand, shell variables, alternate unit names, `kill`, etc.) are not matched by the default patterns.

</details>

## Hooks

| Hook | Event | Purpose |
|------|-------|---------|
| `shell-guard` | `tool:before_call` | Inspect `run_shell_command` arguments and decline matching commands before execution |
