# my-thinking-agent-private

Japanese: [README.ja.md](README.ja.md).

This is the private companion repository for `my-thinking-agent`. Keep real
decision principles, learning records, and optional private operational notes
here—not in the public project.

The public repository ships this directory as a safe, empty template. It
contains no real conversation, work history, credentials, or personal data.

## Layout

| Path | Purpose |
| --- | --- |
| `decision-principles.md` | Durable, generalized decision criteria |
| `decisions/` | Private learning and decision records created through the MCP |
| `operations/` | Optional concise private handovers; never required for learning |
| `AGENTS.md` | Private-repository safety and synchronization rules |

Use `make onboard` in the public project and choose option 3 to create a new
private GitHub repository. That workflow is opt-in and asks for exact
confirmation before it creates a repository or pushes a template.

## Safety

Private visibility is not encryption. Confirm access controls, disk encryption,
and backups before adding information. Never store passwords, API keys, private
keys, raw conversations, or directly identifying information. The MCP is local
only and never commits, pushes, or sends data externally.

## Inspecting contents

From the public project directory, `make private-list` lists this repository's
decision-principles file, active-record filenames, and archived-record filenames
without displaying record bodies. To inspect a body, open the private-knowledge-
root path shown by `make status` in a file manager or editor.
