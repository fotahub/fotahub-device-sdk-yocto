#!/bin/bash

if [ "$1" == "--setup" ]; then
    # Set up prerequisites
    sudo apt update && sudo apt install gcc libgirepository1.0-dev libcairo2-dev pkg-config python3-dev gir1.2-gtk-3.0
    python -m pip install --upgrade pip wheel setuptools venv pytest
fi

# Create Python venv
# (see https://python.land/virtual-environments/virtualenv for details)
python3 -m venv venv
source venv/bin/activate

# Install package under development and its dependencies
python -m pip install --editable .

# Run tests
python test_fotahub.py

# Deactivate Python venv
deactivate