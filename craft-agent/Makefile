# craft-agent. Run `make help`.
SHELL := /bin/bash
PYTHON ?= python3
DAYS ?= 30
TOOL ?=
ALL_TOOLS := cad design effect fig film grid light pdf photo sound vector word
TOOLS = $(if $(filter all,$(TOOL)),$(ALL_TOOLS),$(TOOL))

.PHONY: help check test generate build build-app mark-reviewed smoke install uninstall clean-jobs

help:
	@echo "make install CRAFT_HOME=<dir>     set up folders and symlinks (default dir: ~/craft)"
	@echo "make mark-reviewed TOOL=<tool>    record the reviewed commit of a tool's repository"
	@echo "make build TOOL=<tool>|all        build the *-cli binary (needs a reviewed commit)"
	@echo "make build-app TOOL=<tool>|all    build the desktop app for live mode"
	@echo "make smoke [TOOL=<tool>]          start built servers and run one call each"
	@echo "make test | check | generate      development"
	@echo "make clean-jobs DAYS=30           delete old job folders"
	@echo "make uninstall                    remove the symlinks (keeps CRAFT_HOME)"

generate:
	$(PYTHON) scripts/generate.py

check:
	$(PYTHON) scripts/generate.py --check
	shellcheck -x -P SCRIPTDIR bin/craft-mcp bin/craft-stage bin/craft-app bin/craft-guard bin/lib/craft-common.sh scripts/*.sh
	scripts/check-confidentiality.sh

test:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

build:
	@test -n "$(TOOL)" || { echo "usage: make build TOOL=<tool>|all"; exit 2; }
	@for t in $(TOOLS); do scripts/build.sh $$t cli || exit $$?; done

build-app:
	@test -n "$(TOOL)" || { echo "usage: make build-app TOOL=<tool>|all"; exit 2; }
	@for t in $(TOOLS); do scripts/build.sh $$t app || exit $$?; done

mark-reviewed:
	@test -n "$(TOOL)" || { echo "usage: make mark-reviewed TOOL=<tool>"; exit 2; }
	scripts/mark-reviewed.sh $(TOOL)

smoke:
	$(PYTHON) tests/smoke.py $(TOOL)

install:
	scripts/install.sh "$(if $(CRAFT_HOME),$(CRAFT_HOME),$(HOME)/craft)"

uninstall:
	scripts/uninstall.sh

clean-jobs:
	scripts/clean-jobs.sh $(DAYS)
