#!/bin/bash

# Media Service Gallery Features Test Script
# 测试幻灯片播放列表、照片缓存、轮播计划等功能

BASE_URL="http://localhost"
USER_ID="test_user_$(date +%s)"
FRAME_ID="frame_$(date +%s)"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# Function to print test result
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASSED${NC}: $2"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAILED${NC}: $2"
        ((TESTS_FAILED++))
    fi
}

echo "=========================================="
echo "Storage Service - Gallery Features Test"
echo "=========================================="
echo ""
echo "User ID: $USER_ID"
echo "Frame ID: $FRAME_ID"
echo ""

# Test 1: List Gallery Albums
echo -e "${YELLOW}Test 1: List Gallery Albums${NC}"
response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/media/gallery/albums?user_id=$USER_ID&limit=10")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    print_result 0 "List gallery albums"
    echo "Response: $body"
else
    print_result 1 "List gallery albums (HTTP $http_code)"
fi
echo ""

# Test 2: Create Playlist (Manual)
echo -e "${YELLOW}Test 2: Create Manual Playlist${NC}"
response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/media/gallery/playlists" \
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
    PLAYLIST_ID=$(echo "$body" | grep -o '"playlist_id":"[^"]*' | cut -d'"' -f4)
    print_result 0 "Create manual playlist (ID: $PLAYLIST_ID)"
    echo "Response: $body"
else
    print_result 1 "Create manual playlist (HTTP $http_code)"
    echo "Response: $body"
fi
echo ""

# Test 3: Create Smart Playlist
echo -e "${YELLOW}Test 3: Create Smart Playlist (Favorites)${NC}"
response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/media/gallery/playlists" \
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
    SMART_PLAYLIST_ID=$(echo "$body" | grep -o '"playlist_id":"[^"]*' | cut -d'"' -f4)
    print_result 0 "Create smart playlist (ID: $SMART_PLAYLIST_ID)"
else
    print_result 1 "Create smart playlist (HTTP $http_code)"
fi
echo ""

# Test 4: List User Playlists
echo -e "${YELLOW}Test 4: List User Playlists${NC}"
response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/media/gallery/playlists?user_id=$USER_ID")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    print_result 0 "List user playlists"
    echo "Response: $body"
else
    print_result 1 "List user playlists (HTTP $http_code)"
fi
echo ""

# Test 5: Get Playlist Details
if [ ! -z "$PLAYLIST_ID" ]; then
    echo -e "${YELLOW}Test 5: Get Playlist Details${NC}"
    response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/media/gallery/playlists/$PLAYLIST_ID?user_id=$USER_ID")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "200" ]; then
        print_result 0 "Get playlist details"
        echo "Response: $body"
    else
        print_result 1 "Get playlist details (HTTP $http_code)"
    fi
    echo ""
fi

# Test 6: Get Random Photos
echo -e "${YELLOW}Test 6: Get Random Photos${NC}"
response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/media/gallery/photos/random?user_id=$USER_ID&count=5")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    print_result 0 "Get random photos"
    echo "Response: $body"
else
    print_result 1 "Get random photos (HTTP $http_code)"
fi
echo ""

# Test 7: Get Random Photos with Criteria
echo -e "${YELLOW}Test 7: Get Random Photos (Favorites Only)${NC}"
response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/media/gallery/photos/random?user_id=$USER_ID&count=10&favorites_only=true")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    print_result 0 "Get random photos (favorites only)"
    echo "Response: $body"
else
    print_result 1 "Get random photos (favorites only) (HTTP $http_code)"
fi
echo ""

# Test 8: Preload Images to Cache
echo -e "${YELLOW}Test 8: Preload Images to Cache${NC}"
response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/media/gallery/cache/preload" \
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
    print_result 0 "Preload images to cache"
    echo "Response: $body"
else
    print_result 1 "Preload images to cache (HTTP $http_code)"
fi
echo ""

# Test 9: Get Cache Stats
echo -e "${YELLOW}Test 9: Get Cache Stats${NC}"
response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/media/gallery/cache/$FRAME_ID/stats")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    print_result 0 "Get cache stats"
    echo "Response: $body"
else
    print_result 1 "Get cache stats (HTTP $http_code)"
fi
echo ""

# Test 10: Update Photo Metadata
echo -e "${YELLOW}Test 10: Update Photo Metadata${NC}"
response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/media/gallery/photos/metadata?user_id=$USER_ID" \
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
    print_result 0 "Update photo metadata (404 expected if photo doesn't exist)"
    echo "Response: $body"
else
    print_result 1 "Update photo metadata (HTTP $http_code)"
fi
echo ""

# Test 11: Create Rotation Schedule
if [ ! -z "$PLAYLIST_ID" ]; then
    echo -e "${YELLOW}Test 11: Create Rotation Schedule${NC}"
    response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/media/gallery/schedules" \
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
        SCHEDULE_ID=$(echo "$body" | grep -o '"schedule_id":"[^"]*' | cut -d'"' -f4)
        print_result 0 "Create rotation schedule (ID: $SCHEDULE_ID)"
        echo "Response: $body"
    else
        print_result 1 "Create rotation schedule (HTTP $http_code)"
        echo "Response: $body"
    fi
    echo ""
fi

# Test 12: Get Frame Schedules
echo -e "${YELLOW}Test 12: Get Frame Schedules${NC}"
response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/media/gallery/schedules/$FRAME_ID")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    print_result 0 "Get frame schedules"
    echo "Response: $body"
else
    print_result 1 "Get frame schedules (HTTP $http_code)"
fi
echo ""

# Test 13: Get Frame Playlists
echo -e "${YELLOW}Test 13: Get Frame Playlists${NC}"
response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/media/gallery/frames/$FRAME_ID/playlists")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    print_result 0 "Get frame playlists"
    echo "Response: $body"
else
    print_result 1 "Get frame playlists (HTTP $http_code)"
fi
echo ""

# Test 14: Update Playlist
if [ ! -z "$PLAYLIST_ID" ]; then
    echo -e "${YELLOW}Test 14: Update Playlist${NC}"
    response=$(curl -s -w "\n%{http_code}" -X PUT "$BASE_URL/api/v1/media/gallery/playlists/$PLAYLIST_ID" \
      -H "Content-Type: application/json" \
      -d '{
        "name": "Family Memories (Updated)",
        "transition_duration": 10
      }')

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "200" ]; then
        print_result 0 "Update playlist"
        echo "Response: $body"
    else
        print_result 1 "Update playlist (HTTP $http_code)"
    fi
    echo ""
fi

# Test 15: Clear Cache
echo -e "${YELLOW}Test 15: Clear Expired Cache${NC}"
response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/media/gallery/cache/$FRAME_ID/clear?days_old=30")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    print_result 0 "Clear expired cache"
    echo "Response: $body"
else
    print_result 1 "Clear expired cache (HTTP $http_code)"
fi
echo ""

# Test 16: Delete Playlist
if [ ! -z "$PLAYLIST_ID" ]; then
    echo -e "${YELLOW}Test 16: Delete Playlist${NC}"
    response=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL/api/v1/media/gallery/playlists/$PLAYLIST_ID")
    http_code=$(echo "$response" | tail -n1)

    if [ "$http_code" = "204" ]; then
        print_result 0 "Delete playlist"
    else
        print_result 1 "Delete playlist (HTTP $http_code)"
    fi
    echo ""
fi

echo ""
echo "======================================================================"
echo -e "${BLUE}Test Summary${NC}"
echo "======================================================================"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
TOTAL=$((TESTS_PASSED + TESTS_FAILED))
echo "Total: $TOTAL"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All gallery features tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Please review the output above.${NC}"
    exit 1
fi

