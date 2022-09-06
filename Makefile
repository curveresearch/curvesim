.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo ""
	@echo "venv                   create python virtual env"
	@echo "requirements           generate requirements file from base requirements"
	@echo ""
	@echo "changelog_entry"       create changelog entry
	@echo "changelog_update"      update changelog from recent entries
	@echo ""
	@echo "hooks                  install Git hooks"
	@echo ""

VENV_NAME := CurveSim
VENV_PATH := $(HOME)/.virtualenvs/$(VENV_NAME)

.PHONY: venv
venv:
	python3 -m venv $(VENV_PATH)
	$(VENV_PATH)/bin/pip install -r requirements.txt

.PHONY: requirements
requirements:
	@echo "Generating requirements.txt from core dependencies in requirements_base.txt ..."
	python3 -m venv temp_venv
	temp_venv/bin/pip install --upgrade pip
	temp_venv/bin/pip install -r requirements_base.txt
	echo '# generated via "make requirements"' > requirements.txt
	temp_venv/bin/pip freeze -r requirements_base.txt >> requirements.txt
	rm -rf temp_venv
	@echo "requirements.txt has been updated 🍉"

.PHONY: hooks
hooks:
	@echo "Installing git hooks..."
	cp ./git_hooks/{commit-msg,pre-commit*} .git/hooks/
	chmod +x .git/hooks/*
	@echo "Hooks installed"

.PHONY: changelog_entry
changelog_entry:
	scriv create

.PHONY: changelog_update
changelog_update:
	scriv collect
