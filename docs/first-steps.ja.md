# はじめて使う

English: [first-steps.md](first-steps.md).

このprojectは、過去のやりとりから「次にどう答えるとよいか」を思い出すための道具です。最初は難しい設定を覚える必要はありません。以下を上から順に行ってください。

## 1. Terminalを開き、projectを用意する

TerminalでPython 3.11以上、`uv`、Git、`make`、`codex` commandが使えることを確認します。まだprojectをcloneしていない場合は、次を入力します。

```bash
git clone https://github.com/kazunari-kamata/my-thinking-agent.git ~/my-thinking-agent
cd ~/my-thinking-agent
```

すでにclone済みなら、`cd`の行だけを入力します。続けて、案内に必要なcommandが使えることを確認します。

```bash
make doctor
```

設定は変更しません。不足したcommandが表示された場合は、それをinstallしてからもう一度`make doctor`を入力します。`jj`と`gh`は、複数のPCでprivate repositoryを使う場合だけ必要です。

## 2. 順番案内を始める

次の1行を入力します。

```bash
make start
```

画面の質問に答えるだけです。

- 初めてこのPCで使うなら、表示されたonboardingで `1` を選びます。
- 別のPCですでに使っているprivate repositoryをつなぐなら、`2` を選びます。
- source folderを聞かれたら、最初は `N` で飛ばしても大丈夫です。後から追加できます。`Y`を選んだ場合は、続けて複数のfolderを登録できます。

`make start` は、あなたの代わりにrepositoryを公開したり、sourceを勝手に登録したりしません。確認が必要な場面では止まります。

## 3. Codexを始める

順番案内が終わったら、`my-thinking-agent`をcloneしたproject folder（例: `~/my-thinking-agent`）で次を入力します。source folderやprivate repositoryのfolderではありません。

```bash
codex
```

普段どおり日本語で相談します。大切な依頼では、過去のprivate learning recordを検索してから答えや次の手順を提案します。分からないことや判断が分かれることは質問します。

削除、公開、外部送信、password変更などは、学習内容だけを理由に実行しません。対象を示した明示指示が必要です。

## 4. 作業folderを後から使う

作業記録があるfolderを学びの参考にしたい場合は、次を入力します。

```bash
make repl
```

menuの `4` を選び、短い名前（例: `kvnc`）とfolderのpathを入力します。pathは `../kvnc` のように書けます。さらに追加したいときは、もう一度 `4` を選びます。登録したfolder以外は読みません。

## 困ったとき

```bash
make help
```

`make`と`make help`は、どちらも同じcommand一覧を表示します。`make`は短い書き方、`make help`は「助けを表示する」意味が明確な書き方です。現在のsource folderを確認するだけなら、次です。

```bash
make learning-sources
```

CodexにMCPが登録されていることと、有効なtoolの一覧を確認する場合は、次を入力します。

```bash
make mcp-status
```

これは設定の確認です。実際にMCPを使えるか試すには、Codexで「personal-knowledgeを使って判断原則を一覧にしてください。fileは変更しないでください。」と依頼します。

local設定、source path、CodexへのMCP登録を一度に確認する場合は、`make status`を使います。

private knowledgeの判断原則、active record、archive済みrecordの**file名だけ**を確認する場合は、次を使います。record本文は表示・変更しません。

```bash
make private-list
```

本文を確認したいときは、表示された`private knowledge root`をfile managerまたはeditorで開きます。macOSでは、そのdirectoryへ移動して`open .`と入力するとFinderで開けます。
