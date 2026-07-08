# Signaloid SD-Dev

This module provides tools to interface with the Signaloid SD-Dev and detect, reset, and power measure the connected Signaloid C0 compute modules.

## Usage

To use this module
1. Install the prerequisite packages
	```sh
	sudo apt update
	sudo apt install liblgpio-dev python3-dev swig build-essential -y
	```

2. Create a Python Virtual Environment, enable it, and install the required Python packages:
	```sh
	python3 -m venv .venv
	source .venv/bin/activate
	pip install -r requirements.txt
	```
