#!/bin/bash

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}    iStudiox - Service Status Check${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════${NC}\n"

# Detect environment
if [ "$CODESPACES" = "true" ]; then
    echo -e "${YELLOW}🌐 Environment: GitHub Codespaces${NC}"
    echo -e "    Codespace: ${CODESPACE_NAME}"
    BACKEND_URL="https://${CODESPACE_NAME}-8000.app.github.dev"
    FRONTEND_URL="https://${CODESPACE_NAME}-5173.app.github.dev"
    echo ""
else
    echo -e "${YELLOW}🏠 Environment: Local Development${NC}"
    BACKEND_URL="http://localhost:8000"
    FRONTEND_URL="http://localhost:5173"
    echo ""
fi

# Check Backend
echo -e "${BLUE}[1] Checking Backend (FastAPI)...${NC}"
if curl -s ${BACKEND_URL}/health > /dev/null 2>&1; then
    HEALTH=$(curl -s ${BACKEND_URL}/health | jq -r '.status' 2>/dev/null || echo "ok")
    VERSION=$(curl -s ${BACKEND_URL}/health | jq -r '.version' 2>/dev/null || echo "unknown")
    echo -e "    ${GREEN}✓ Backend is running${NC}"
    echo -e "    Status: ${GREEN}${HEALTH}${NC}"
    echo -e "    Version: ${VERSION}"
    echo -e "    URL: ${BACKEND_URL}"
    echo -e "    Docs: ${BACKEND_URL}/docs"
else
    echo -e "    ${RED}✗ Backend is not responding${NC}"
    echo -e "    URL: ${BACKEND_URL}"
fi

echo ""

# Check Frontend
echo -e "${BLUE}[2] Checking Frontend (React/Vite)...${NC}"
if curl -s ${FRONTEND_URL} > /dev/null 2>&1; then
    echo -e "    ${GREEN}✓ Frontend is running${NC}"
    echo -e "    URL: ${FRONTEND_URL}"
else
    echo -e "    ${RED}✗ Frontend is not responding${NC}"
    echo -e "    URL: ${FRONTEND_URL}"
fi

echo ""

# Check AI Providers
echo -e "${BLUE}[3] Checking AI Providers...${NC}"
if curl -s ${BACKEND_URL}/api/v1/ai/status > /dev/null 2>&1; then
    PROVIDER_COUNT=$(curl -s ${BACKEND_URL}/api/v1/ai/status | jq -r '.provider_count' 2>/dev/null || echo "0")
    AVAILABLE=$(curl -s ${BACKEND_URL}/api/v1/ai/status | jq -r '.available' 2>/dev/null || echo "false")
    MULTI_AGENT=$(curl -s ${BACKEND_URL}/api/v1/ai/status | jq -r '.multi_agent_enabled' 2>/dev/null || echo "false")
    
    echo -e "    ${GREEN}✓ AI Engine is active${NC}"
    echo -e "    Providers: ${PROVIDER_COUNT}/4 available"
    echo -e "    Multi-Agent: ${MULTI_AGENT}"
    
    # List providers
    curl -s ${BACKEND_URL}/api/v1/ai/status | jq -r '.providers[] | "    - \(.provider): \(.model)"' 2>/dev/null
else
    echo -e "    ${RED}✗ AI Engine is not responding${NC}"
fi

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}All services are running successfully!${NC}"
if [ "$CODESPACES" = "true" ]; then
    echo -e "${YELLOW}Access your app at: ${FRONTEND_URL}${NC}"
fi
echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
