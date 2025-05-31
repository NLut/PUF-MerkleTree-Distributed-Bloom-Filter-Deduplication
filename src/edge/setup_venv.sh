#!/bin/bash

# Name your virtual environment directory
VENV_DIR=".venv"

echo "📦 Creating Python virtual environment in ./$VENV_DIR"
python3 -m venv $VENV_DIR

echo "✅ Activating virtual environment"
source $VENV_DIR/bin/activate

echo "📄 Installing required libraries from requirements.txt"
pip install --upgrade pip
pip install -r requirements.txt

echo "🎉 Setup complete. Virtual environment is ready."

