# MCP tool呼び出し例

この例では、架空recordのID `tutorial-project-priority` を使います。Codex利用時は、通常は下の「Codexへの依頼」のように自然言語で指示します。CodexがMCP toolを選んだときの引数が「tool引数」です。

`make mcp` が起動するstdio serverへ、terminalからJSONを手入力する必要はありません。Codexへ登録して`/mcp`で有効化した後に利用してください。

## Read: 判断原則と検索

Codexへの依頼:

```text
personal-knowledgeを使い、まず判断原則を読んでください。
次に「優先順位 可逆性」で判断記録を検索し、record IDと要約だけを示してください。
fileは変更しないでください。
```

`search_decisions`のtool引数:

```json
{
  "query": "優先順位 可逆性",
  "max_results": 5
}
```

詳細が必要なrecordだけを開きます。

```json
{
  "id": "tutorial-project-priority"
}
```

## Create: recordを保存する

最初の依頼では、下書き表示だけを求めます。

```text
添付の架空sampleと同じformatで、新しい判断記録の下書きを作ってください。
保存はまだ行わず、事実・仮定・選択肢・判断・要約が揃っているか確認してください。
```

内容をreviewした後、同じ会話で明示承認します。

```text
内容を確認しました。private knowledgeへの保存を承認します。
CREATE tutorial-project-priority
```

`create_decision`は、次のように完全なMarkdownとIDを受け取ります。`content`には[架空の判断記録sample](tutorial-project-priority.md)全体を入れます。

```json
{
  "id": "tutorial-project-priority",
  "content": "---\\nid: tutorial-project-priority\\ntitle: 架空projectの優先順位を可逆な調査から始める\\ndate: 2026-11-13\\nclassification: internal\\ntags: tutorial, 優先順位, 可逆性\\n---\\n\\n（完全なMarkdown本文）",
  "confirmation": "CREATE tutorial-project-priority"
}
```

`id`、front matterの`id`、file名は一致しなければなりません。`content`を省略した部分だけで保存することはできません。

## Update: reviewした完全版で置換する

部分的な差分ではなく、更新後のrecord全体を表示・reviewします。

```text
tutorial-project-priority の現在内容を読み、結果だけを更新した完全版を表示してください。
まだ更新しないでください。

（内容を確認後）
UPDATE tutorial-project-priority
```

```json
{
  "id": "tutorial-project-priority",
  "content": "---\\nid: tutorial-project-priority\\n...（review済みの完全なMarkdown）",
  "confirmation": "UPDATE tutorial-project-priority"
}
```

## Archiveと復元

archiveは通常の検索対象から外すrecoverableな移動であり、完全消去ではありません。

```text
tutorial-project-priority をarchiveする前に、対象・理由・復元方法を表示してください。

（内容を確認後）
ARCHIVE tutorial-project-priority
```

```json
{
  "id": "tutorial-project-priority",
  "confirmation": "ARCHIVE tutorial-project-priority"
}
```

次に`list_archived_decisions`で返った`archive_id`を指定して復元します。`archive_id`にはtimestampが含まれるため、推測せずMCPの結果をそのまま使います。

```text
archive済みrecordを一覧にし、tutorial-project-priority の archive_id を示してください。
そのrecordの復元を承認します。
RESTORE tutorial-project-priority
```

```json
{
  "id": "tutorial-project-priority",
  "archive_id": "tutorial-project-priority--YYYYMMDDTHHMMSSZ.md",
  "confirmation": "RESTORE tutorial-project-priority"
}
```

active recordが既に存在する場合、復元は上書きせず失敗します。内容を失わないための仕様です。
