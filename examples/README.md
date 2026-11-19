# examples

このdirectoryの内容は、MCPと判断記録のformatを試すための**架空のdata**です。個人名、会社名、顧客情報、credential、実際の判断内容は含めません。

- [tutorial-project-priority.md](tutorial-project-priority.md) は、`create_decision` と `update_decision` に渡す完全なrecordの例です。
- [mcp-tool-calls.md](mcp-tool-calls.md) は、Codexでの依頼文とMCP tool引数の例です。

実運用では、recordをprivate knowledge repositoryの`decisions/`にだけ作成してください。MCPのCreate / Update / Archive / Restoreは現在の端末のprivate cloneだけを変更し、Git commitやpushは行いません。
