#!/usr/bin/env bash
set -e

sudo apt update

sudo apt install -y \
    python3 \
    python3-venv \
    python3-pip \
    libportaudio2 \
    portaudio19-dev

python3 -m venv .venv

source .venv/bin/activate

python -m pip install --upgrade pip

pip install -r requirements.txt

echo
echo "Tradutor Sonoro v0.7 instalado."
echo
echo "Execute:"
echo "source .venv/bin/activate"
echo "python app.py"
