#!/bin/bash
# Log wrapper that adds service name prefix to each line

SERVICE_NAME="$1"
shift

# Run the command and prefix each line with service name
"$@" 2>&1 | while IFS= read -r line; do
    echo "[$SERVICE_NAME] $line"
done
