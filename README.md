# YouTube Music Recommender for Reverbify

This is a Python function for Appwrite that integrates with YouTube Music API to provide personalized recommendations and home content.

## Features

- Authentication with YouTube Music using browser cookies
- Fetching personalized recommendations
- Fetching home content
- Library playlist access
- Secure storage of authentication headers in user preferences

## Setup

1. Deploy this function to Appwrite
2. Set up the required environment variables:
   - `APPWRITE_ENDPOINT`
   - `APPWRITE_PROJECT_ID`
   - `APPWRITE_API_KEY`
   - `APPWRITE_FUNCTION_USER_ID`
3. Configure the function to use Python runtime
4. Install the dependencies from requirements.txt

## Usage

The function accepts the following actions:

- `test_connection`: Test if the authentication is working
- `get_recommendations`: Get personalized music recommendations
- `get_home`: Get the YouTube Music home feed
- `get_library_playlists`: Get the user's library playlists

## Authentication

Authentication is handled by extracting and storing the necessary headers from the user's browser session. The function retrieves these headers from the user's preferences in Appwrite.
