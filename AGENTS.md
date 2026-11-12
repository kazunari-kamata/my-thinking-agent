# my-thinking-agent

このrepositoryは、ローカル優先の個人向け判断支援projectである。明示的に提供された判断原則と事例を基に考察を支援するものであり、利用者本人を名乗ったり、利用者に代わって決定したりしない。

## 安全境界

- knowledge/private/ と、knowledge/decisions/ の架空sample以外のすべての資料を私的情報として扱う。利用者がその資料を対象にするよう明示しない限り、追加、表示、commit、upload、引用をしてはならない。
- password、API key、OAuth token、private key、生の私的会話をversion control対象のfileへ置かない。
- 内蔵MCP serverはprivate knowledge root内でのみ、作成・更新・recoverableなarchive/restoreを行える。各変更には、同一message内の明示承認とtoolの完全一致confirmationを必須とする。外部送信、公開、account変更、Git commit/pushは行わない。
- `make start` と `make onboard` は端末初期設定を対話的に補助する。private repositoryのclone、repository作成、templateのpushは、表示された対象を確認し完全一致confirmationを得た場合だけ行う。判断記録そのものを自動でuploadしない。
- 事実、仮定、推奨を分ける。根拠が不足するときは補完せず、不足を明示する。

## 作業規約

- 長期的な判断profileは knowledge/decision-principles.md に簡潔かつ一般化して置く。具体的な先例は個別の判断記録に保存する。
- 各判断記録のfront matterにある classification を正確に保つ。MCP serverは設定した最大分類を超える記録を返さない。
- 実質的な依頼で推奨・計画を示す前には、現在の依頼の要点で `search_decisions` を使い、必要なrecordだけを読む。類似先例がない場合は、その不在を明示して推測で先例を作らない。
- 会話から学習する場合、利用者の依頼、回答・実施結果、利用者の訂正または追加依頼を、現在の会話から簡潔に匿名化して要約する。利用者にMarkdown recordを手入力させない。
- 設定済みのlearning source rootがある場合は、まず `list_learning_sources`、`search_learning_sources`、必要時に `read_learning_source` を使い、参照したfileを学習候補へ付ける。MCPは会話履歴や未設定directoryを自動取得しない。
- `prepare_conversation_learning` が不足情報を質問として返した場合だけ、その質問を利用者へ伝える。候補を表示して明示confirmationを得るまで `save_conversation_learning` を呼ばない。
- 長期的に残す学び、適用すべきsource、または判断基準が曖昧・矛盾している場合は、保存せずに利用者へ要点を絞って再質問する。
- 削除、archive、外部送信、公開、credential変更、支出、契約、不可逆な操作は、推測や学習記録を根拠に実行せず、対象を示した利用者の明示指示を待つ。
- Python code、MCPの振る舞い、sample dataを変更した後は make test を実行する。
- 変更は jj で管理し、mainへ直接commit/pushしない。Pull Requestを作成して検証・reviewを経由する。
