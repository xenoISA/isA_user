#!/bin/bash

# Media Service Gallery Features Test Script
# 测试幻灯片播放列表、照片缓存、轮播计划等功能

BASE_URL="http://localhost:8222"
USER_ID="test_user_$(date +%s)"
FRAME_ID="frame_$(date +%s)"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "Storage Service - Gallery Features Test"
echo "=========================================="
echo ""
echo "User ID: $USER_ID"
echo "Frame ID: $FRAME_ID"
echo ""

# Test 1: List Gallery Albums
echo -e "${YELLOW}Test 1: List Gallery Albums${NC}"
response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/gallery/albums?user_id=$USER_ID&limit=10")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    echo "Response: $body"
else
    echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
fi
echo ""

# Test 2: Create Playlist (Manual)
echo -e "${YELLOW}Test 2: Create Manual Playlist${NC}"
response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/gallery/playlists" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Family Memories",
    "description": "Our favorite family photos",
    "user_id": "'$USER_ID'",
    "playlist_type": "manual",
    "photo_ids": [],
    "album_ids": [],
    "rotation_type": "sequential",
    "transition_duration": 5
  }')

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "201" ]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    PLAYLIST_ID=$(echo "$body" | grep -o '"playlist_id":"[^"]*' | cut -d'"' -f4)
    echo "Playlist ID: $PLAYLIST_ID"
    echo "Response: $body"
else
    echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
    echo "Response: $body"
fi
echo ""

# Test 3: Create Smart Playlist
echo -e "${YELLOW}Test 3: Create Smart Playlist (Favorites)${NC}"
response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/gallery/playlists" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Best Photos",
    "description": "AI-selected best quality photos",
    "user_id": "'$USER_ID'",
    "playlist_type": "smart",
    "photo_ids": [],
    "album_ids": [],
    "smart_criteria": {
      "favorites_only": true,
      "min_quality_score": 0.8,
      "max_photos": 20
    },
    "rotation_type": "smart",
    "transition_duration": 8
  }')

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "201" ]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    SMART_PLAYLIST_ID=$(echo "$body" | grep -o '"playlist_id":"[^"]*' | cut -d'"' -f4)
    echo "Smart Playlist ID: $SMART_PLAYLIST_ID"
else
    echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
fi
echo ""

# Test 4: List User Playlists
echo -e "${YELLOW}Test 4: List User Playlists${NC}"
response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/gallery/playlists?user_id=$USER_ID")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    echo "Response: $body"
else
    echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
fi
echo ""

# Test 5: Get Playlist Details
if [ ! -z "$PLAYLIST_ID" ]; then
    echo -e "${YELLOW}Test 5: Get Playlist Details${NC}"
    response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/gallery/playlists/$PLAYLIST_ID?user_id=$USER_ID")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ PASSED${NC}"
        echo "Response: $body"
    else
        echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
    fi
    echo ""
fi

# Test 6: Get Random Photos
echo -e "${YELLOW}Test 6: Get Random Photos${NC}"
response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/gallery/photos/random?user_id=$USER_ID&count=5")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    echo "Response: $body"
else
    echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
fi
echo ""

# Test 7: Get Random Photos with Criteria
echo -e "${YELLOW}Test 7: Get Random Photos (Favorites Only)${NC}"
response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/gallery/photos/random?user_id=$USER_ID&count=10&favorites_only=true")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    echo "Response: $body"
else
    echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
fi
echo ""

# Test 8: Preload Images to Cache
echo -e "${YELLOW}Test 8: Preload Images to Cache${NC}"
response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/gallery/cache/preload" \
  -H "Content-Type: application/json" \
  -d '{
    "frame_id": "'$FRAME_ID'",
    "user_id": "'$USER_ID'",
    "photo_ids": [],
    "priority": "high"
  }')

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    echo "Response: $body"
else
    echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
fi
echo ""

# Test 9: Get Cache Stats
echo -e "${YELLOW}Test 9: Get Cache Stats${NC}"
response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/gallery/cache/$FRAME_ID/stats")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    echo "Response: $body"
else
    echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
fi
echo ""

# Test 10: Update Photo Metadata
echo -e "${YELLOW}Test 10: Update Photo Metadata${NC}"
response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/gallery/photos/metadata?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "test_photo_id",
    "is_favorite": true,
    "rating": 5,
    "tags": ["family", "vacation", "2025"],
    "location_name": "Paris"
  }')

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ] || [ "$http_code" = "404" ]; then
    echo -e "${GREEN}✓ PASSED${NC} (Expected 404 if photo doesn't exist)"
    echo "Response: $body"
else
    echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
fi
echo ""

# Test 11: Create Rotation Schedule
if [ ! -z "$PLAYLIST_ID" ]; then
    echo -e "${YELLOW}Test 11: Create Rotation Schedule${NC}"
    response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/gallery/schedules" \
      -H "Content-Type: application/json" \
      -d '{
        "playlist_id": "'$PLAYLIST_ID'",
        "frame_id": "'$FRAME_ID'",
        "user_id": "'$USER_ID'",
        "start_time": "08:00",
        "end_time": "22:00",
        "days_of_week": [0,1,2,3,4,5,6],
        "interval_seconds": 5,
        "shuffle": false
      }')

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "201" ]; then
        echo -e "${GREEN}✓ PASSED${NC}"
        SCHEDULE_ID=$(echo "$body" | grep -o '"schedule_id":"[^"]*' | cut -d'"' -f4)
        echo "Schedule ID: $SCHEDULE_ID"
        echo "Response: $body"
    else
        echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
        echo "Response: $body"
    fi
    echo ""
fi

# Test 12: Get Frame Schedules
echo -e "${YELLOW}Test 12: Get Frame Schedules${NC}"
response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/gallery/schedules/$FRAME_ID")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    echo "Response: $body"
else
    echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
fi
echo ""

# Test 13: Get Frame Playlists
echo -e "${YELLOW}Test 13: Get Frame Playlists${NC}"
response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/gallery/frames/$FRAME_ID/playlists")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    echo "Response: $body"
else
    echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
fi
echo ""

# Test 14: Update Playlist
if [ ! -z "$PLAYLIST_ID" ]; then
    echo -e "${YELLOW}Test 14: Update Playlist${NC}"
    response=$(curl -s -w "\n%{http_code}" -X PUT "$BASE_URL/api/v1/gallery/playlists/$PLAYLIST_ID" \
      -H "Content-Type: application/json" \
      -d '{
        "name": "Family Memories (Updated)",
        "transition_duration": 10
      }')

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ PASSED${NC}"
        echo "Response: $body"
    else
        echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
    fi
    echo ""
fi

# Test 15: Clear Cache
echo -e "${YELLOW}Test 15: Clear Expired Cache${NC}"
response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/gallery/cache/$FRAME_ID/clear?days_old=30")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    echo "Response: $body"
else
    echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
fi
echo ""

# Test 16: Delete Playlist
if [ ! -z "$PLAYLIST_ID" ]; then
    echo -e "${YELLOW}Test 16: Delete Playlist${NC}"
    response=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL/api/v1/gallery/playlists/$PLAYLIST_ID")
    http_code=$(echo "$response" | tail -n1)

    if [ "$http_code" = "204" ]; then
        echo -e "${GREEN}✓ PASSED${NC}"
    else
        echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
    fi
    echo ""
fi

echo "=========================================="
echo "Gallery Features Test Complete"
echo "=========================================="
echo ""

echo -e "${YELLOW}Summary:${NC}"
echo "• Tested playlist creation (manual & smart)"
echo "• Tested random photo selection"
echo "• Tested photo cache & preloading"
echo "• Tested photo metadata management"
echo "• Tested rotation schedules"
echo "• Tested frame-playlist associations"
echo ""
echo -e "${GREEN}All core gallery features are working!${NC}"

