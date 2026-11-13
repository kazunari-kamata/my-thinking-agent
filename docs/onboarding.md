# 対話的onboarding

`personal-knowledge-onboard`は、初回設定や別端末への引継ぎを質問形式で行うlocal commandです。毎回READMEからpathやcommandを探す必要はありません。

```bash
cd ~/my-thinking-agent
make onboard

# uvでentry pointを使う場合
uv run personal-knowledge-onboard
```

表示される選択肢は次のとおりです。

| 選択 | 使う場面 | 行うこと |
| --- | --- | --- |
| 1 | この端末だけで試す | emptyなlocal private rootと、この端末の`.codex/config.toml`を作成 |
| 2 | 別端末へ引継ぐ、または既存repositoryを使う | private repository URLからcloneするか、既存cloneを接続してlocal configを作成 |
| 3 | 複数端末用のprivate repositoryをまだ作っていない | empty `main`、private GitHub repository、JJ設定、initial template用PRを順に作成 |
| 4 | 状態確認だけ | local MCP設定の有無を表示。file・Git remoteは変更しない |

## 安全な確認点

onboardingは次の操作を自動では実行しません。該当する操作の直前に対象を表示し、完全一致のconfirmationを求めます。

| 操作 | 必須confirmation | 影響範囲 |
| --- | --- | --- |
| private rootのtemplate初期化 | `INITIALIZE PRIVATE ROOT` | 指定したempty directoryだけ |
| private repositoryを別端末へclone | `CLONE PRIVATE REPOSITORY` | 指定した端末の指定directoryだけ |
| private GitHub repositoryの新規作成 | `CREATE PRIVATE REPOSITORY` | GitHub accountと指定directory |
| initial templateのPR push | `PUSH INITIAL TEMPLATE` | 空のtemplateだけをprivate remoteへpush |

選択3では、GitHub repositoryの作成に`gh`、JJ運用に`jj`、empty `main`の作成に`git`を使います。GitHubへloginしていない場合やGit authorが未設定の場合は、commandが停止して理由を表示します。credentialをinputやversion controlへ保存することはありません。

initial templateに含まれるのは`decision-principles.md`の雛形と`decisions/README.md`だけです。実際の判断recordは自動uploadされません。MCPでrecordを作成・更新した後は、内容をreviewしてから通常のJJ Pull Request workflowで同期します。

## 別端末での最短手順

新しい端末では、まずpublic projectだけをcloneしてからonboardingを実行します。選択2でprivate repository URLを入力すれば、その端末用のprivate cloneと`.codex/config.toml`を作れます。

```bash
git clone https://github.com/kazunari-kamata/my-thinking-agent.git ~/my-thinking-agent
cd ~/my-thinking-agent
uv sync
make onboard
```

onboardingの完了後はCodexを起動し、`/mcp`で`personal-knowledge`が有効であることを確認します。private repositoryの内容を最新化する操作は意図的に自動化されません。更新済みrecordを使う前に、`jj git fetch --remote origin`と`jj new main@origin`を実行します。詳細は[更新・同期・設定](update-operations.md)を参照してください。

## 状態だけを確認する

```bash
cd ~/my-thinking-agent
make onboard-status
```

このcommandは`.codex/config.toml`の有無と、bootstrapが生成した設定かどうかだけを表示します。private record、token、remoteの内容を表示・変更しません。
