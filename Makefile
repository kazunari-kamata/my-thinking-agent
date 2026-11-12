.DEFAULT_GOAL := help

UV ?= uv
RUN_PYTHON = $(UV) run python

.PHONY: help doctor start status test mcp mcp-status private-list private-init configure-mcp update-mcp learning-add learning-remove learning-sources repl onboard onboard-status

help:
	@printf '%s\n' \
	  'my-thinking-agent commands:' \
	  '  make / make help                              この一覧を表示（同じ結果）' \
	  '  make doctor                                   最初に必要なcommandを確認（変更なし）' \
	  '  make start                                    はじめて使う人向けの順番案内（おすすめ）' \
	  '  make status                                   この端末の設定・MCP・sourceをまとめて表示' \
	  '  make onboard                                  初回設定・別端末設定の対話wizard' \
	  '  make repl                                     設定・learning sourceの対話REPL' \
	  '  make onboard-status                           この端末の設定状態を表示' \
	  '  make learning-add SOURCE=name=../path         sourceを追加または同名更新' \
	  '  make learning-sources                         source一覧と利用可否を表示' \
	  '  make learning-remove SOURCE=name              sourceを削除' \
	  '  make update-mcp                               生成済みMCP設定を更新' \
	  '  make mcp-status                               Codexに登録されたMCPと有効toolを表示' \
	  '  make private-list                              private recordのfile名を一覧（本文は非表示）' \
	  '  make test                                     testを実行' \
	  '  make mcp                                      上級者用: stdio MCP serverを直接起動' \
	  '  make private-init KNOWLEDGE_ROOT=/path        上級者用: 空のprivate rootを初期化' \
	  '  make configure-mcp KNOWLEDGE_ROOT=/path       上級者用: MCP設定を作成'

doctor:
	$(RUN_PYTHON) -m my_thinking_agent.doctor

test:
	$(RUN_PYTHON) -m unittest discover -s tests -v

mcp:
	@$(RUN_PYTHON) -m my_thinking_agent.mcp_server

mcp-status:
	@codex mcp get personal_knowledge

status:
	@printf '%s\n' '== この端末の設定とlearning source =='
	@$(RUN_PYTHON) -m my_thinking_agent.onboarding --status
	@printf '%s\n' '' '== CodexのMCP登録状態 =='
	@codex mcp get personal_knowledge

private-list:
	@$(RUN_PYTHON) -m my_thinking_agent.private_view

private-init:
	@test -n "$(KNOWLEDGE_ROOT)" || (echo "Set KNOWLEDGE_ROOT=/path/to/private-knowledge" >&2; exit 2)
	$(RUN_PYTHON) -m my_thinking_agent.bootstrap --knowledge-root "$(KNOWLEDGE_ROOT)" --initialize-knowledge-root

configure-mcp:
	@test -n "$(KNOWLEDGE_ROOT)" || (echo "Set KNOWLEDGE_ROOT=/path/to/private-knowledge" >&2; exit 2)
	$(RUN_PYTHON) -m my_thinking_agent.bootstrap --knowledge-root "$(KNOWLEDGE_ROOT)" --write-project-config

update-mcp:
ifneq ($(strip $(KNOWLEDGE_ROOT)),)
	$(RUN_PYTHON) -m my_thinking_agent.bootstrap --knowledge-root "$(KNOWLEDGE_ROOT)" --update-project-config
else
	$(RUN_PYTHON) -m my_thinking_agent.bootstrap --update-project-config
endif

learning-add:
	@test -n "$(SOURCE)" || (echo "Set SOURCE=name=relative-or-absolute-path" >&2; exit 2)
	$(RUN_PYTHON) -m my_thinking_agent.bootstrap --update-project-config --learning-source "$(SOURCE)"

learning-remove:
	@test -n "$(SOURCE)" || (echo "Set SOURCE=name" >&2; exit 2)
	$(RUN_PYTHON) -m my_thinking_agent.bootstrap --update-project-config --remove-learning-source "$(SOURCE)"

learning-sources:
	$(RUN_PYTHON) -m my_thinking_agent.bootstrap --list-learning-sources

start:
	$(RUN_PYTHON) -m my_thinking_agent.repl --guided

repl:
	$(RUN_PYTHON) -m my_thinking_agent.repl

onboard:
	$(RUN_PYTHON) -m my_thinking_agent.onboarding

onboard-status:
	$(RUN_PYTHON) -m my_thinking_agent.onboarding --status
