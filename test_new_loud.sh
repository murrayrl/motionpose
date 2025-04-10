#!/bin/bash

# Check if a file argument is provided
if [ $# -ne 1 ]; then
    echo "Usage: $0 <filename.wav>"
    echo "Example: $0 sounds/SkeletonVisual.wav"
    exit 1
fi

# Input file
INPUT_FILE="$1"
SOUNDS_DIR="sounds"

# Verify the file exists in the sounds directory
if [ ! -f "$INPUT_FILE" ] || [[ "$INPUT_FILE" != "$SOUNDS_DIR"/*.wav ]]; then
    echo "Error: '$INPUT_FILE' not found in '$SOUNDS_DIR' or invalid file."
    exit 1
fi

# Temporary file for testing
TEMP_FILE="temp_adjusted.wav"

# Initial loudness target (-12 LUFS)
LOUDNESS=-12

# Function to normalize and play the file
adjust_loudness() {
    local target=$1
    echo "Normalizing to $target LUFS..."
    ffmpeg -i "$INPUT_FILE" -af loudnorm=I=$target:TP=-1:LRA=11 -ar 44100 -y "$TEMP_FILE" 2>/dev/null
    echo "Playing for 10 seconds..."
    ffplay -nodisp -autoexit -t 10 "$TEMP_FILE" 2>/dev/null
}

# Main loop
while true; do
    # Normalize and play the current loudness
    adjust_loudness $LOUDNESS

    # Prompt user for adjustment
    echo "Current loudness: $LOUDNESS LUFS"
    read -p "Do you want it louder (l), softer (s), or keep it (k)? " choice

    case $choice in
        l|L)
            LOUDNESS=$(echo "$LOUDNESS + 5" | bc)
            echo "Increasing to $LOUDNESS LUFS..."
            ;;
        s|S)
            LOUDNESS=$(echo "$LOUDNESS - 10" | bc)
            echo "Decreasing to $LOUDNESS LUFS..."
            ;;
        k|K)
            echo "Keeping loudness at $LOUDNESS LUFS."
            read -p "Save this version to sounds/ (y/n)? " save_choice
            if [ "$save_choice" = "y" ] || [ "$save_choice" = "Y" ]; then
                OUTPUT_FILE="$SOUNDS_DIR/$(basename "$INPUT_FILE" .wav)_adjusted.wav"
                mv "$TEMP_FILE" "$OUTPUT_FILE"
                echo "Saved as $OUTPUT_FILE"
            else
                rm "$TEMP_FILE"
                echo "Temporary file discarded."
            fi
            exit 0
            ;;
        *)
            echo "Invalid choice. Use 'l' (louder), 's' (softer), or 'k' (keep)."
            ;;
    esac
done
