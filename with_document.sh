#!/bin/bash

# Create a temporary file
TEMP_FILE=$(mktemp)

# Open vi with the temporary file
vi "$TEMP_FILE"

# Output the contents of the file to the command specified by arguments
cat "$TEMP_FILE" | "$@"

# Clean up the temporary file
rm "$TEMP_FILE" 