#!/bin/bash
# 同步 isA_common 到 isa_common_local

SOURCE_DIR="/Users/xenodennis/Documents/Fun/isA_Cloud/isA_common"
TARGET_DIR="./isa_common_local"

if [ ! -d "$SOURCE_DIR" ]; then
    echo "Error: Source directory $SOURCE_DIR does not exist"
    exit 1
fi

echo "Syncing $SOURCE_DIR to $TARGET_DIR..."
rsync -av --delete "$SOURCE_DIR/" "$TARGET_DIR/"
echo "Sync completed!"
