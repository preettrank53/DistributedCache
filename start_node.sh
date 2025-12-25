#!/bin/bash
# Start a single DistriCache Node
# Usage: ./start_node.sh [PORT]
# Example: ./start_node.sh 8004

if [ -z "$1" ]; then
    echo "Usage: ./start_node.sh [PORT]"
    echo "Example: ./start_node.sh 8004"
    exit 1
fi

PORT=$1
HOST="127.0.0.1"
CAPACITY=100

echo "Starting Cache Node on port $PORT..."
cd backend
python3 -m src.nodes.server --port $PORT --host $HOST --capacity $CAPACITY
