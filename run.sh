#!/bin/bash
# DistriCache System Startup Script
# Starts 1 Load Balancer, 1 Database, and 3 Cache Nodes

set -e

echo "========================================"
echo "DistriCache - Distributed Cache System"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
LB_PORT=8000
LB_HOST="127.0.0.1"
NODE1_PORT=8001
NODE2_PORT=8002
NODE3_PORT=8003
NODE_HOST="127.0.0.1"
CACHE_CAPACITY=100
DB_PATH="cache_db.sqlite"

echo -e "${YELLOW}Configuration:${NC}"
echo "  Load Balancer: http://$LB_HOST:$LB_PORT"
echo "  Node 1: http://$NODE_HOST:$NODE1_PORT"
echo "  Node 2: http://$NODE_HOST:$NODE2_PORT"
echo "  Node 3: http://$NODE_HOST:$NODE3_PORT"
echo "  Database: $DB_PATH"
echo "  Cache Capacity: $CACHE_CAPACITY"
echo ""

# Create logs directory
mkdir -p logs

# Check if Python is installed
if ! command -v python &> /dev/null; then
    echo -e "${RED}Error: Python is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}Starting DistriCache System...${NC}"
echo ""

# Start Load Balancer
echo -e "${YELLOW}Starting Load Balancer on port $LB_PORT...${NC}"
(cd backend && python -m src.proxy.lb_api --port $LB_PORT --host $LB_HOST --db $DB_PATH) > logs/lb.log 2>&1 &
LB_PID=$!
echo -e "${GREEN}Load Balancer started (PID: $LB_PID)${NC}"
sleep 2

# Start Cache Nodes
echo ""
echo -e "${YELLOW}Starting Cache Nodes...${NC}"

for PORT in $NODE1_PORT $NODE2_PORT $NODE3_PORT; do
    echo "  Starting Node on port $PORT..."
    (cd backend && python -m src.nodes.server --port $PORT --host $NODE_HOST --capacity $CACHE_CAPACITY) > logs/node_$PORT.log 2>&1 &
    NODE_PID=$!
    echo -e "  ${GREEN}Node started on port $PORT (PID: $NODE_PID)${NC}"
    sleep 1
done

echo ""
echo -e "${GREEN}All services started successfully!${NC}"
echo ""
echo -e "${YELLOW}Endpoints:${NC}"
echo "  Load Balancer:   http://$LB_HOST:$LB_PORT"
echo "  Cache Node 1:    http://$NODE_HOST:$NODE1_PORT"
echo "  Cache Node 2:    http://$NODE_HOST:$NODE2_PORT"
echo "  Cache Node 3:    http://$NODE_HOST:$NODE3_PORT"
echo ""
echo -e "${YELLOW}Logs:${NC}"
echo "  Load Balancer:   logs/lb.log"
echo "  Node 1:          logs/node_8001.log"
echo "  Node 2:          logs/node_8002.log"
echo "  Node 3:          logs/node_8003.log"
echo ""
echo -e "${YELLOW}To stop all services, press Ctrl+C${NC}"
echo ""

# Keep the script running
wait
