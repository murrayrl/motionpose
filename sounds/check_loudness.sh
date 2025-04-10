#!/bin/bash

check_loudness() {
    file="$1"
    echo "🔍 Checking loudness for: $file"

    LUFS=$(ffmpeg -i "$file" -filter_complex loudnorm=print_format=json -f null - 2>&1 | \
           grep 'input_i' | sed 's/[^0-9\.\-]*//g')

    echo "    ➤ Integrated Loudness: ${LUFS} LUFS"
}

# If an argument is provided, check that file only
if [ "$#" -eq 1 ]; then
    if [ -f "$1" ]; then
        check_loudness "$1"
    else
        echo "❌ File not found: $1"
        exit 1
    fi
else
    # No arguments: check all .wav files in current directory
    for file in *.wav; do
        [ -e "$file" ] || continue
        check_loudness "$file"
    done
fi

