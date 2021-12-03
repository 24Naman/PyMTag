SHELL := /bin/bash

all: install create

create: requirements.txt
	rm -rf venv
	python3 -m virtualenv venv

install: create
	source venv/bin/activate
	pip install -r requirements.txt
