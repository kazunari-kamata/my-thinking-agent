# my-thinking-agent-private

English: [README.md](README.md).

これは `my-thinking-agent` の private companion repository です。実際の判断原則、学習記録、必要な場合だけの private な作業引継ぎはここに置き、公開 project には置きません。

公開repositoryには、このdirectoryを匿名化済みの空templateとして同梱しています。実際の会話、作業履歴、credential、個人情報は含みません。

## 構成

| path | 用途 |
| --- | --- |
| `decision-principles.md` | 長期的かつ一般化した判断基準 |
| `decisions/` | MCPから作成するprivateな学習・判断record |
| `operations/` | 必要なときだけの簡潔なprivate引継ぎ。学習には必須ではありません。 |
| `AGENTS.md` | private repositoryの安全・同期規約 |

公開projectで `make onboard` を実行し、選択肢 3 を選ぶと新しい private GitHub repository を作成できます。このflowは opt-in であり、repository作成とtemplateのpush前には完全一致のconfirmationを求めます。

## 安全性

private visibilityは暗号化ではありません。情報を追加する前にaccess control、disk encryption、backupを確認してください。password、API key、private key、生の会話、個人を直接識別できる情報は保存しません。MCPはlocalだけを操作し、commit、push、外部送信を行いません。

## 内容を確認する

公開projectのdirectoryで`make private-list`を実行すると、このrepositoryの判断原則、active record、archive済みrecordのfile名だけを一覧できます。本文を確認する場合は、`make status`が表示するprivate knowledge rootをfile managerまたはeditorで開いてください。
