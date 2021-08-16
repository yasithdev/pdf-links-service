#!/usr/bin/env sh

export FLASK_ENV=development
export FLASK_APP=main.py
export CONFIG_DIR=config

flask run --host=0.0.0.0 --port=8000
