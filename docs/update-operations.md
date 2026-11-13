# 更新・同期・設定

このprojectに**自動で判断記録を変更・同期・公開する機能はありません**。MCPは明示的なtool callを受けた現在の端末だけを変更し、Git/JJ・GitHub・別端末への反映は利用者がreviewして実行します。

```mermaid
flowchart LR
  MCP[MCP: 明示承認付きのrecord変更] --> Local[現在の端末のprivate clone]
  Local --> Review[jj statusでreview]
  Review --> PR[JJ bookmarkをpushしてPR]
  PR --> Merge[人がreview・merge]
  Merge --> Fetch[別端末でjj git fetch]
  Fetch --> Ready[Codexを起動して利用]
```

## 何が更新されるか

| 更新対象 | 自動か | 必要な設定 | 反映範囲 |
| --- | --- | --- | --- |
| 判断recordのCreate / Update / Archive / Restore | いいえ。tool approvalと完全一致confirmationが必要 | private rootへ接続する`.codex/config.toml` | 現在の端末のprivate cloneだけ |
| private knowledgeの別端末への同期 | いいえ。PRのreview・mergeと各端末のfetchが必要 | private Git remote、GitHub認証、JJ | merge後に取得した端末 |
| `my-thinking-agent`のcode / document更新 | いいえ。public projectのPRをmerge後に取得 | public repositoryのcloneとJJ | 取得した端末 |
| `.codex/config.toml`のMCP設定 | いいえ。端末ごとにbootstrapで生成・更新 | absolute path、trusted project | 設定した端末だけ |
| Python environment | いいえ。source更新後に`uv sync`を実行 | `uv` | 実行した端末だけ |

したがって、cron、常駐process、GitHub Actions、auto-pull、auto-pushを設定する必要はありません。実際の判断記録は変更内容を確認してから同期する設計です。

初回設定・別端末へのprivate clone・new private repositoryの作成は、質問形式の`make onboard`で行えます。これはrecordの更新や同期を自動化するものではありません。詳細は[対話的onboarding](onboarding.md)を参照してください。

## 初回に端末ごと必要な設定

private knowledgeを使う端末では、次を一度だけ行います。

1. public projectと、必要ならprivate knowledge repositoryをcloneする。
2. 各cloneで`jj git init --colocate`を行い、`jj bookmark track main@origin`で`main`を追跡する。
3. public projectでbootstrapを実行し、private rootのabsolute pathを持つ`.codex/config.toml`を生成する。
4. Codexでprojectをtrustedにし、再起動後に`/mcp`で`personal-knowledge`を確認する。

```bash
cd ~/my-thinking-agent
uv run --directory "$PWD" python -m my_thinking_agent.bootstrap \
  --knowledge-root ~/my-thinking-agent-private \
  --write-project-config
```

`default_tools_approval_mode = "approve"`と操作ごとの`CREATE <id>`などのconfirmationは、安全のため維持します。自動化のために緩和する設定はありません。

## 判断recordを更新して別端末へ反映する

### 1. 現在の端末でMCP更新を行う

Codexに変更案を表示させ、内容をreviewした後に同じ会話で承認します。

```text
内容を確認しました。更新を承認します。
UPDATE vendor-selection-2026-01
```

これは現在のprivate cloneの`decisions/`だけを更新します。ほかの端末、GitHub、外部serviceにはまだ反映されません。

### 2. private repositoryのPRを作る

変更内容を確認し、bookmarkをpushしてPull Requestを作ります。`jj bookmark set`は新規作成と既存bookmarkの更新の両方に使えます。

```bash
cd ~/my-thinking-agent-private
jj status
jj diff
jj describe -m "knowledge: update vendor selection record"
jj bookmark set knowledge/vendor-selection -r @
jj git push --bookmark knowledge/vendor-selection
gh pr create --base main --head knowledge/vendor-selection \
  --title "knowledge: 委託先選定recordを更新"
```

Pull Requestをreview・mergeするまでは、他端末へ反映されません。MCPはGit commit、push、PR作成を行いません。

### 3. 別端末で受け取る

作業中の変更がないことを`jj status`で確認してから、remoteの`main`を取得します。

```bash
cd ~/my-thinking-agent-private
jj status
jj git fetch --remote origin
jj log -r main@origin
jj new main@origin
jj status
```

`jj new main@origin`は、取得済みの`main`を親にした新しい空のworking-copy changeへ移動し、fileをその状態にします。作業中のrecordがある場合は先にPRへ送るか、別のchangeとして保持してから実行してください。競合が表示された場合は、人が内容をreviewして解決するまでMCPでrecordを更新しません。

## program本体を更新する

公開projectのPull Requestがmergeされた後、各端末でsourceを取得し、dependencyとMCPを確認します。

```bash
cd ~/my-thinking-agent
jj status
jj git fetch --remote origin
jj log -r main@origin
jj new main@origin
uv sync
make test
```

MCP toolの一覧やgenerated configurationが変更されたreleaseでは、bootstrapが生成したconfigだけを安全に更新できます。

```bash
cd ~/my-thinking-agent
make update-mcp KNOWLEDGE_ROOT=~/my-thinking-agent-private
```

手書きの`.codex/config.toml`は上書きされません。`config/codex-mcp-config.toml.example`と比較して必要な差分を手動で反映し、Codexを再起動して`/mcp`を確認してください。

## 更新頻度の目安

- 判断record: 判断が変わったときだけ。毎回、完全なrecordをreviewして明示承認する。
- private knowledgeの同期: 別端末で使う前、またはreview・merge後に手動で行う。
- program本体: 必要な修正・新機能がmergeされたときに手動で行う。
- MCP設定: private rootのpath変更、tool一覧の変更、別端末追加のときだけ行う。

自動更新は利便性を上げますが、未reviewの判断記録を別端末へ広げたり、想定外のconfigurationを有効化したりするおそれがあります。このprojectでは、更新箇所と承認者が分かる手動のJJ Pull Request workflowを標準とします。
