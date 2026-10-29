.DEFAULT_GOAL := help

DOCKER ?= docker
POETRY ?= poetry
IMAGE ?= restful-booker-tests:local
PYTEST_ARGS ?=
BOOKER_BASE_URL ?= https://restful-booker.herokuapp.com
BOOKER_TIMEOUT ?= 10

PYTHON_SOURCES := constants.py tests checkers helpers
CONTAINER := $(DOCKER) run --rm --init
LOCAL_RUN := VIRTUAL_ENV="$(CURDIR)/.venv" $(POETRY) run

.PHONY: help build test lint format test-local lint-local format-local

help:
	@printf '%s\n' \
		'make build   Build the test image' \
		'make test    Build the image and run pytest (PYTEST_ARGS="..." for options)' \
		'make lint    Build the image and check imports, formatting and flake8' \
		'make format  Build the image and format the source files on the host' \
		'make test-local    Run pytest in the local .venv using Poetry' \
		'make lint-local    Check imports, formatting and flake8 in the local .venv' \
		'make format-local  Format the source files in the local .venv'

build:
	$(DOCKER) build --tag "$(IMAGE)" .

test: build
	$(CONTAINER) \
		--env BOOKER_BASE_URL="$(BOOKER_BASE_URL)" \
		--env BOOKER_TIMEOUT="$(BOOKER_TIMEOUT)" \
		"$(IMAGE)" pytest $(PYTEST_ARGS)

lint: build
	$(CONTAINER) "$(IMAGE)" sh -c \
		'isort --check-only $(PYTHON_SOURCES) && yapf --diff --recursive $(PYTHON_SOURCES) && flake8 $(PYTHON_SOURCES)'

format: build
	$(CONTAINER) --user "$(shell id -u):$(shell id -g)" \
		--mount 'type=bind,source=$(CURDIR),target=/app' \
		"$(IMAGE)" sh -c 'isort $(PYTHON_SOURCES) && yapf --in-place --recursive $(PYTHON_SOURCES)'

test-local:
	BOOKER_BASE_URL="$(BOOKER_BASE_URL)" BOOKER_TIMEOUT="$(BOOKER_TIMEOUT)" \
		$(LOCAL_RUN) pytest $(PYTEST_ARGS)

lint-local:
	$(LOCAL_RUN) isort --check-only $(PYTHON_SOURCES)
	$(LOCAL_RUN) yapf --diff --recursive $(PYTHON_SOURCES)
	$(LOCAL_RUN) flake8 $(PYTHON_SOURCES)

format-local:
	$(LOCAL_RUN) isort $(PYTHON_SOURCES)
	$(LOCAL_RUN) yapf --in-place --recursive $(PYTHON_SOURCES)
