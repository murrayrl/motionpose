#!/bin/bash

#THIS SCRIPT USES API KEYS FOR FREESOUND website ONLY and wont work for others


SOUND_ID="$1"
FILENAME="$2"

# Check if arguments are provided
if [[ -z "$SOUND_ID" || -z "$FILENAME" ]]; then
  echo "Usage: $0 <sound_id> <output_basename>"
  exit 1
fi

# Ensure environment variables are set
if [[ -z "$FREESOUND_CLIENT_ID" || -z "$FREESOUND_CLIENT_SECRET" ]]; then
  echo "Error: FREESOUND_CLIENT_ID and FREESOUND_CLIENT_SECRET must be set in your environment."
  exit 1
fi

# Set the redirect URI (must match your Freesound API credentials)
REDIRECT_URI="http://freesound.org/home/app_permissions/permission_granted/"

# Get the directory of the script and set token file location
SCRIPT_DIR=$(dirname "$0")
TOKEN_FILE="$SCRIPT_DIR/.freesound_tokens"

# Function to fetch a new access token via authorization code
fetch_new_tokens() {
  AUTH_URL="https://freesound.org/apiv2/oauth2/authorize/?client_id=$FREESOUND_CLIENT_ID&response_type=code&redirect_uri=$REDIRECT_URI"
  echo "Please visit this URL in a browser to authorize the application:"
  echo "$AUTH_URL"
  echo "1. Log in to your Freesound account."
  echo "2. Click 'Authorize' to allow the app."
  echo "3. You’ll be redirected to a URL like:"
  echo "   http://freesound.org/home/app_permissions/permission_granted/?code=abcd1234"
  echo "4. Copy the 'code' value (e.g., 'abcd1234') from the URL."
  read -p "Enter the authorization code: " AUTH_CODE

  response=$(curl -s -X POST https://freesound.org/apiv2/oauth2/access_token/ \
    -d "client_id=$FREESOUND_CLIENT_ID" \
    -d "client_secret=$FREESOUND_CLIENT_SECRET" \
    -d "grant_type=authorization_code" \
    -d "code=$AUTH_CODE" \
    -d "redirect_uri=$REDIRECT_URI")

  ACCESS_TOKEN=$(echo "$response" | grep -oP '"access_token":\s*"\K[^"]+')
  REFRESH_TOKEN=$(echo "$response" | grep -oP '"refresh_token":\s*"\K[^"]+')

  if [[ -z "$ACCESS_TOKEN" || -z "$REFRESH_TOKEN" ]]; then
    echo "❌ Failed to fetch tokens. Response:"
    echo "$response"
    exit 1
  fi

  # Store tokens in the token file in the same directory
  echo "ACCESS_TOKEN=$ACCESS_TOKEN" > "$TOKEN_FILE"
  echo "REFRESH_TOKEN=$REFRESH_TOKEN" >> "$TOKEN_FILE"
  echo "Tokens acquired and stored in $TOKEN_FILE."
}

# Function to refresh the access token using the refresh token
refresh_token() {
  REFRESH_TOKEN=$(grep "REFRESH_TOKEN" "$TOKEN_FILE" | cut -d= -f2)
  refresh_response=$(curl -s -X POST https://freesound.org/apiv2/oauth2/access_token/ \
    -d "client_id=$FREESOUND_CLIENT_ID" \
    -d "client_secret=$FREESOUND_CLIENT_SECRET" \
    -d "grant_type=refresh_token" \
    -d "refresh_token=$REFRESH_TOKEN")

  NEW_ACCESS_TOKEN=$(echo "$refresh_response" | grep -oP '"access_token":\s*"\K[^"]+')
  NEW_REFRESH_TOKEN=$(echo "$refresh_response" | grep -oP '"refresh_token":\s*"\K[^"]+')

  if [[ -n "$NEW_ACCESS_TOKEN" ]]; then
    ACCESS_TOKEN="$NEW_ACCESS_TOKEN"
    if [[ -n "$NEW_REFRESH_TOKEN" ]]; then
      REFRESH_TOKEN="$NEW_REFRESH_TOKEN"
    fi
    # Update token file with new tokens
    echo "ACCESS_TOKEN=$ACCESS_TOKEN" > "$TOKEN_FILE"
    echo "REFRESH_TOKEN=$REFRESH_TOKEN" >> "$TOKEN_FILE"
    echo "Access token refreshed successfully."
  else
    echo "Failed to refresh access token."
    ACCESS_TOKEN=""
  fi
}

# Load existing tokens if the token file exists
if [[ -f "$TOKEN_FILE" ]]; then
  source "$TOKEN_FILE"
fi

# Check if the access token is valid
if [[ -n "$ACCESS_TOKEN" ]]; then
  echo "Checking access token validity..."
  test_response=$(curl -s -w "\n%{http_code}" -H "Authorization: Bearer $ACCESS_TOKEN" "https://freesound.org/apiv2/me/")
  http_code=$(echo "$test_response" | tail -n1)
  if [[ "$http_code" -eq 200 ]]; then
    echo "Access token is valid."
  else
    echo "Access token is invalid."
    ACCESS_TOKEN=""
  fi
fi

# If access token is invalid or missing, try to refresh it
if [[ -z "$ACCESS_TOKEN" && -n "$REFRESH_TOKEN" ]]; then
  echo "Attempting to refresh access token..."
  refresh_token
fi

# If still no access token, perform manual authorization
if [[ -z "$ACCESS_TOKEN" ]]; then
  fetch_new_tokens
fi

# Download the sound using the valid access token
echo "📥 Downloading sound $SOUND_ID to ${FILENAME}.wav..."
curl -L -H "Authorization: Bearer $ACCESS_TOKEN" \
  "https://freesound.org/apiv2/sounds/${SOUND_ID}/download/" \
  -o "${FILENAME}.wav"

if [[ $? -eq 0 ]]; then
  echo "✅ Download complete: ${FILENAME}.wav"
else
  echo "❌ Download failed."
fi
