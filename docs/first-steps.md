# First steps

Japanese: [first-steps.ja.md](first-steps.ja.md).

This project helps Codex remember reviewed guidance from earlier conversations.
You do not need to memorize setup commands. Follow these steps in order.

## 1. Open a terminal and get the project

You need Python 3.11 or later, `uv`, Git, `make`, and the Codex command available in
your terminal. If you have not cloned the project yet, run:

```bash
git clone https://github.com/kazunari-kamata/my-thinking-agent.git ~/my-thinking-agent
cd ~/my-thinking-agent
```

If you cloned it earlier, only run the `cd` line. Then check that the commands
needed for the guide are ready:

```bash
make doctor
```

It changes nothing. If it reports a missing command, install that command first
and run `make doctor` again. `jj` and `gh` are needed only when you create or
use a shared private repository on multiple computers.

## 2. Start the guided setup

Run this one command:

```bash
make start
```

Answer the questions on screen.

- Choose `1` in onboarding when this is the first use on this computer.
- Choose `2` only when connecting a private repository already used on another computer.
- You may answer `N` when asked to register a source folder. It can be added later. If you choose `Y`, the guide lets you register more than one folder.

`make start` never publishes a repository or registers a source folder without
your selection and required confirmation.

## 3. Start Codex

When the guide finishes, run this in the `my-thinking-agent` project folder
(for example, `~/my-thinking-agent`). This is not the source-folder path or
the private-repository folder:

```bash
codex
```

Use ordinary language. For material requests, Codex searches relevant private
learning records before proposing an answer or next step. It asks a question
when the guidance is unclear or conflicts.

Learned guidance never authorizes deletion, publication, external sending,
password changes, or other irreversible actions. Those require a separate,
explicit instruction that identifies the target.

## 4. Add a work folder later

To use a folder containing work notes as local reference material, run:

```bash
make repl
```

Choose menu item `4`, then enter a short name such as `kvnc` and the folder
path. A path like `../kvnc` is accepted. Choose `4` again for each additional
folder. No unregistered folder is read.

## If you get stuck

```bash
make help
```

`make` and `make help` show the same command list. `make` is the shorter form;
`make help` makes the intent explicit. To check only the currently registered
source folders, run:

```bash
make learning-sources
```

To see whether Codex registered the MCP and which tools are enabled, run:

```bash
make mcp-status
```

This checks registration rather than running a tool. To exercise the MCP, ask
Codex: “Use personal-knowledge to list the decision principles. Do not modify
files.”

To see local configuration, source paths, and Codex MCP registration together,
run `make status`.

To list only the filenames of private decision principles, active records, and
archived records without displaying or changing their bodies, run:

```bash
make private-list
```

To inspect a body, open the displayed private-knowledge-root path in your file
manager or editor. On macOS, change to that directory and run `open .` to open
it in Finder.
