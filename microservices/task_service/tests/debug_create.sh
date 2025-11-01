#!/bin/bash

# Get token
TOKEN=$(curl -s -X POST "http://localhost:8201/api/v1/auth/dev-token" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user_weather", "email": "test@example.com", "expires_in": 3600}' | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])")

echo "Token: ${TOKEN:0:50}..."
echo ""

# Test weather task
echo "Creating weather task..."
curl -s -X POST "http://localhost:8211/api/v1/tasks" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Test Task - Daily Weather",
    "description": "Automated daily weather report",
    "task_type": "daily_weather",
    "priority": "high",
    "config": {
      "location": "San Francisco",
      "units": "celsius",
      "include_forecast": true
    },
    "schedule": {
      "type": "cron",
      "cron_expression": "0 8 * * *",
      "timezone": "America/Los_Angeles"
    },
    "credits_per_run": 1.5,
    "tags": ["weather", "daily", "automated"],
    "metadata": {
      "category": "automation",
      "source": "test_script"
    },
    "due_date": "2025-12-31T23:59:59Z"
  }' | python3 -m json.tool
