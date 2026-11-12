# Interactive onboarding

Japanese: [onboarding.ja.md](onboarding.ja.md).

`make start` is the recommended first-use guide. It opens onboarding only when
this computer still needs setup, then explains the next step in plain language.

```bash
cd ~/my-thinking-agent
make start
```

Use `make onboard` when you want to open the setup choices directly. For an
interactive menu that also manages existing learning sources and updates
the generated local configuration, run `make repl`. It does not add a source,
modify configuration, or perform an external operation until you choose the
corresponding menu item.

| Choice | Use it when | Effect |
| --- | --- | --- |
| 1 | Trying one device only | Creates an empty local private root and this device's `.codex/config.toml` |
| 2 | Using an existing private repository or another device | Clones/connects the private root and creates local configuration |
| 3 | Creating a new multi-device private repository | Creates empty `main`, a private GitHub repository, JJ setup, and an initial-template PR |
| 4 | Checking state only | Reports local MCP setup; changes no files or remotes |

## Explicit safety checkpoints

Onboarding displays its target and asks for an exact confirmation before any
material change.

| Operation | Confirmation | Scope |
| --- | --- | --- |
| Initialize the private-root template | `INITIALIZE PRIVATE ROOT` | The specified empty directory only |
| Clone a private repository | `CLONE PRIVATE REPOSITORY` | The specified directory on this device |
| Create a private GitHub repository | `CREATE PRIVATE REPOSITORY` | Your GitHub account and the specified directory |
| Push the initial-template PR | `PUSH INITIAL TEMPLATE` | The empty template only |

Choice 3 uses `gh` to create the repository, `jj` for the workflow, and `git`
only for the empty initial commit. Missing GitHub login or Git author settings
stop the command with an explanation. Credentials are never stored in input or
version-controlled files. Its proposed repository name is
`my-thinking-agent-private`; it is created only after the exact confirmation,
not as part of normal setup.

The initial template is the data-free
[`templates/my-thinking-agent-private`](../templates/my-thinking-agent-private/)
layout: private-repository guidance, `decision-principles.md`, `decisions/`
guidance without real records, and optional-operation guidance. It never uploads real
records. Review MCP-created records and synchronize them through the normal JJ
Pull Request workflow.

## Another device

```bash
git clone https://github.com/kazunari-kamata/my-thinking-agent.git ~/my-thinking-agent
cd ~/my-thinking-agent
make start
```

Choose option 2 to clone/connect the private repository. Then run
`make mcp-status` to verify `personal-knowledge` and its enabled tools before
starting Codex. Synchronization remains manual: fetch and move to the updated
main before using newer records.

```bash
cd ~/my-thinking-agent-private
jj git fetch --remote origin
jj new main@origin
```

## Status only

```bash
cd ~/my-thinking-agent
make onboard-status
```

This displays whether `.codex/config.toml` exists, whether guided setup generated
it, the private-knowledge-root path, and configured source paths with their
availability. It never displays or changes private record contents, tokens, or
remotes. Run `make status` when you also want Codex's MCP-registration state
and enabled tools.
