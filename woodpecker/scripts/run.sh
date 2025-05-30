#!/bin/bash

woodpecker experiment run -f experiments/llm-data-leakage-with-prompt-injection_1.yaml

woodpecker experiment verify -f experiments/llm-data-leakage-with-prompt-injection_1.yaml -o json >results/llm-data-leakage-with-prompt-injection_1.json