#!/bin/bash

# Ensure dependencies are installed
npm install

# Add src to PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)/src

# Start the Flask HTTP server
python3 src/http_server.py 