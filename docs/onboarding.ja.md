# 対話的onboarding

English: [onboarding.md](onboarding.md).

`make start`は、初回設定や別端末への引継ぎを質問形式で案内する、最初に使うcommandです。このPCで設定が必要なときだけonboardingを開き、次にすることを順番に表示します。

```bash
cd ~/my-thinking-agent
make start
```

設定の選択肢を直接開くときは`make onboard`、既存のlearning source管理と生成済みlocal configurationの更新も同じmenuで行うときは`make repl`を実行します。menu項目を選択するまでsource追加、configuration変更、external operationは行いません。

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

選択3では、GitHub repositoryの作成に`gh`、JJ運用に`jj`、empty `main`の作成に`git`を使います。repository名の既定値は`my-thinking-agent-private`ですが、通常の初期設定で自動作成されるわけではなく、完全一致confirmation後だけ作成されます。GitHubへloginしていない場合やGit authorが未設定の場合は、commandが停止して理由を表示します。credentialをinputやversion controlへ保存することはありません。

initial templateには、公開projectの[templates/my-thinking-agent-private](../templates/my-thinking-agent-private/)と同じデータなしの構成（private repository向けの案内、`decision-principles.md`、実recordを含まない`decisions/`の案内、optional operation向けの案内）が含まれます。実際の判断recordは自動uploadされません。MCPでrecordを作成・更新した後は、内容をreviewしてから通常のJJ Pull Request workflowで同期します。

## 別端末での最短手順

新しい端末では、まずpublic projectだけをcloneしてからonboardingを実行します。選択2でprivate repository URLを入力すれば、その端末用のprivate cloneと`.codex/config.toml`を作れます。

```bash
git clone https://github.com/kazunari-kamata/my-thinking-agent.git ~/my-thinking-agent
cd ~/my-thinking-agent
make start
```

案内では`2`を選び、既存private repositoryのURLを入力します。完了後は`make mcp-status`で`personal-knowledge`と有効toolを確認してからCodexを起動します。private repositoryの内容を最新化する操作は意図的に自動化されません。更新済みrecordを使う前に、`jj git fetch --remote origin`と`jj new main@origin`を実行します。詳細は[更新・同期・設定](update-operations.ja.md)を参照してください。

## 状態だけを確認する

```bash
cd ~/my-thinking-agent
make onboard-status
```

このcommandは`.codex/config.toml`の有無、案内が生成した設定かどうか、private knowledge rootのpath、登録済みsource pathと利用可否を表示します。private record本文、token、remoteの内容は表示・変更しません。CodexへのMCP登録状態と有効toolもまとめて確認したい場合は、`make status`を実行します。
