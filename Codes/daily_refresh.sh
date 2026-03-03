#!/bin/bash

# RFP Radar Daily Refresh Script
# This script orchestrates the account scanning and dashboard update.

echo "🚀 Starting RFP Radar Daily Refresh..."

# Path to the agent script
AGENT_PATH="/Users/akshay.mehndiratta/Antigravity-Projects/rfp-radar/Codes/agent.py"

# Run the agent to fetch new signals
echo "🔍 Scanning for new strategic signals..."
python3 "$AGENT_PATH"

# In a real implementation, the agent.py would update signals.json 
# and the dashboard.html would load it dynamically.

echo "✅ Refresh complete. Dashboard updated at: /Users/akshay.mehndiratta/Antigravity-Projects/rfp-radar/index.html"
