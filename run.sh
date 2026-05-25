#!/bin/bash
# prima di usare questo script seguire le istruzioni di installazione nel README.
# se si usa un virtualenv deve chiamarsi "venv" o ".venv" e trovarsi nella cartella del progetto.

cd "$(dirname "$0")"

if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

python main.py #esegue
