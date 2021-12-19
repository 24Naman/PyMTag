SHELL := /bin/bash

all: install create

create: requirements.txt
	python3 -m pip install --upgrade virtualenv
	rm -rf venv
	python3 -m virtualenv venv

install: create
	source venv/bin/activate
	pip install -r requirements.txt
