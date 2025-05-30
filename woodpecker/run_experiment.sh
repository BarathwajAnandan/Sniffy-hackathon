#!/bin/bash

# Activate virtual environment and run the woodpecker experiment
cd "$(dirname "$0")"
source venv/bin/activate
python woodpeck.py "$@" 