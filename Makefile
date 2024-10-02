SHELL := /bin/bash

export ENVIRONMENT ?= dev
export APP_NAME := sonata-cell-position
export APP_VERSION := $(shell git describe --abbrev --dirty --always --tags)
export COMMIT_SHA := $(shell git rev-parse HEAD)
export IMAGE_NAME ?= $(APP_NAME)
export IMAGE_TAG ?= $(APP_VERSION)-$(ENVIRONMENT)


help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-23s\033[0m %s\n", $$1, $$2}'

compile-deps:  ## Create or update requirements.txt, without upgrading the version of the dependencies
	tox -e compile-requirements

upgrade-deps:  ## Create or update requirements.txt, using the latest version of the dependencies
	tox -e upgrade-requirements

check-deps:  ## Check that the dependencies in the existing requirements.txt are valid
	tox -e check-requirements

build:  ## Build the docker image
	docker compose --progress=plain build

run: build  ## Run the docker image
	docker compose up --remove-orphans

lint:  ## Run linters
	tox -e lint

format:  ## Run formatters
	tox -e format

test:  ## Run tests
	tox -e coverage
