# my-thinking-agent

このrepositoryは、ローカル優先の個人向け判断支援projectである。明示的に提供された判断原則と事例を基に考察を支援するものであり、利用者本人を名乗ったり、利用者に代わって決定したりしない。

## 安全境界

- knowledge/private/ と、knowledge/decisions/ の架空sample以外のすべての資料を私的情報として扱う。利用者がその資料を対象にするよう明示しない限り、追加、表示、commit、upload、引用をしてはならない。
- password、API key、OAuth token、private key、生の私的会話をversion control対象のfileへ置かない。
- 内蔵MCP serverはprivate knowledge root内でのみ、作成・更新・recoverableなarchive/restoreを行える。各変更には、同一message内の明示承認とtoolの完全一致confirmationを必須とする。外部送信、公開、account変更、Git commit/pushは行わない。
- `personal-knowledge-onboard` は端末初期設定を対話的に補助する。private repositoryのclone、repository作成、templateのpushは、表示された対象を確認し完全一致confirmationを得た場合だけ行う。判断記録そのものを自動でuploadしない。
- 事実、仮定、推奨を分ける。根拠が不足するときは補完せず、不足を明示する。

## 作業規約

- 長期的な判断profileは knowledge/decision-principles.md に簡潔かつ一般化して置く。具体的な先例は個別の判断記録に保存する。
- 各判断記録のfront matterにある classification を正確に保つ。MCP serverは設定した最大分類を超える記録を返さない。
- Python code、MCPの振る舞い、sample dataを変更した後は make test を実行する。
- 作業完了前に SESSION.md を更新し、実施内容、未完了task、次回作業を記録する。
- 変更は jj で管理し、mainへ直接commit/pushしない。Pull Requestを作成して検証・reviewを経由する。
