#!/bin/bash

echo "=== USB Audio Test Script (Card 2 - KM_B2) ==="

CARD_ID=2
CONTROL="PCM"

# Step 1: Set PCM volume to 100%
echo "Setting $CONTROL volume to 100%..."
amixer -c $CARD_ID sset "$CONTROL" 100%

# Step 2: Show mixer state
echo "=== Mixer Status ==="
amixer -c $CARD_ID sget "$CONTROL"

# Step 3: Play test tone
echo "Playing 1 kHz sine wave on USB speaker..."
speaker-test -D hw:$CARD_ID,0 -t sine -f 1000 -c 2 -l 1

echo "=== Done ==="

