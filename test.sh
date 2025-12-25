#!/bin/bash
# DistriCache - Test Runner Script
# Runs all unit tests and integration tests

set -e

echo "========================================"
echo "DistriCache - Test Suite"
echo "========================================"
echo ""

# Set PYTHONPATH to include current directory
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if pytest is installed
if ! python -m pytest --version > /dev/null 2>&1; then
    echo -e "${YELLOW}Installing pytest...${NC}"
    pip install pytest pytest-asyncio
fi

echo -e "${GREEN}Running Unit Tests...${NC}"
echo ""

# Run tests
echo -e "${YELLOW}Test Suite 1: LRU Cache${NC}"
python -m pytest backend/tests/test_lru_cache.py -v

echo ""
echo -e "${YELLOW}Test Suite 2: Consistent Hash Ring${NC}"
python -m pytest backend/tests/test_consistent_hash.py -v

echo ""
echo -e "${YELLOW}Test Suite 3: Database Manager${NC}"
python -m pytest backend/tests/test_database.py -v

echo ""
echo -e "${YELLOW}Test Suite 4: Cache Node Server${NC}"
python -m pytest backend/tests/test_cache_node_server.py -v

echo ""
echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}All Tests Completed!${NC}"
echo -e "${GREEN}=====================================${NC}"
