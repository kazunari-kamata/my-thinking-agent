.DEFAULT_GOAL := test

PYTHON ?= python3

.PHONY: test mcp private-init configure-mcp update-mcp onboard onboard-status

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

mcp:
	PYTHONPATH=src $(PYTHON) -m my_thinking_agent.mcp_server

private-init:
	@test -n "$(KNOWLEDGE_ROOT)" || (echo "Set KNOWLEDGE_ROOT=/path/to/private-knowledge" >&2; exit 2)
	PYTHONPATH=src $(PYTHON) -m my_thinking_agent.bootstrap --knowledge-root "$(KNOWLEDGE_ROOT)" --initialize-knowledge-root

configure-mcp:
	@test -n "$(KNOWLEDGE_ROOT)" || (echo "Set KNOWLEDGE_ROOT=/path/to/private-knowledge" >&2; exit 2)
	PYTHONPATH=src $(PYTHON) -m my_thinking_agent.bootstrap --knowledge-root "$(KNOWLEDGE_ROOT)" --write-project-config

update-mcp:
	@test -n "$(KNOWLEDGE_ROOT)" || (echo "Set KNOWLEDGE_ROOT=/path/to/private-knowledge" >&2; exit 2)
	PYTHONPATH=src $(PYTHON) -m my_thinking_agent.bootstrap --knowledge-root "$(KNOWLEDGE_ROOT)" --update-project-config

onboard:
	PYTHONPATH=src $(PYTHON) -m my_thinking_agent.onboarding

onboard-status:
	PYTHONPATH=src $(PYTHON) -m my_thinking_agent.onboarding --status
