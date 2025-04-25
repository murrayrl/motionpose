#!/usr/bin/env bash
set -euo pipefail

TARGET_LUFS=-23
TMP_SUFFIX=".normtmp.wav"

for f in *.wav; do
    printf "🔍  %-30s  " "$f"

    # First pass: capture JSON block from loudnorm
    JSON=$(ffmpeg -nostats -hide_banner -i "$f" \
        -af loudnorm=I=$TARGET_LUFS:TP=-2:LRA=7:print_format=json \
        -f null - 2>&1)

    # Extract value of input_i (current LUFS)
    I_LUFS=$(echo "$JSON" | grep '"input_i"' | head -n1 | cut -d':' -f2 | tr -d ' ",')
    
    if [[ -z "$I_LUFS" || ! "$I_LUFS" =~ ^-?[0-9]+(\.[0-9]+)?$ ]]; then
        echo "⚠️  could not parse LUFS – skipped"
        continue
    fi

    # Decide whether to normalize
    if (( $(echo "$I_LUFS < $TARGET_LUFS" | bc -l) )); then
        echo "🎚️  $I_LUFS LUFS → normalising to $TARGET_LUFS LUFS"

        ffmpeg -y -loglevel error -i "$f" \
            -af loudnorm=I=$TARGET_LUFS:TP=-2:LRA=7 \
            -ar 44100 "$f$TMP_SUFFIX"

        mv "$f$TMP_SUFFIX" "$f"
        echo "✅  done"
    else
        echo "✔️  already at $I_LUFS LUFS (≥ $TARGET_LUFS)"
    fi
done

