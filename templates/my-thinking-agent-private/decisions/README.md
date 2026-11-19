# 判断・学習記録

各recordをMarkdown fileとしてこのdirectoryへ保存します。公開repositoryではなく、このprivate knowledge rootだけに置いてください。

MCPが会話から作るrecordには、要約、実施結果、利用者のfeedback、参照したsource fileが含まれます。生の会話をそのまま保存せず、将来の判断に必要な匿名化済みの情報だけを残してください。

必須front matter:

```md
---
id: short-stable-id
title: 機微情報を含まない短いtitle
date: YYYY-MM-DD
classification: internal
tags: comma, separated, terms
---
```

`classification` には `public`、`internal`、`confidential` のいずれかを指定します。通常のMCP serverは `internal` までしか返しません。
