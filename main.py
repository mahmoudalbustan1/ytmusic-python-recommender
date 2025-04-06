import os
import json
import sys

# Import packages
# Use the standard Appwrite exception import
from appwrite.client import Client
from appwrite.services.users import Users
from appwrite.exception import AppwriteException
print("Imported Appwrite SDK")
try:
    from ytmusicapi import YTMusic
    print("Successfully imported ytmusicapi")
except ImportError as e:
    print(f"Failed to import ytmusicapi: {e}")

# Define environment variables
APPWRITE_ENDPOINT = os.environ.get("APPWRITE_ENDPOINT", "")
APPWRITE_PROJECT_ID = os.environ.get("APPWRITE_PROJECT_ID", "")
APPWRITE_API_KEY = os.environ.get("APPWRITE_API_KEY", "")
APPWRITE_FUNCTION_ID = os.environ.get("APPWRITE_FUNCTION_ID", "")

# Define constants
YT_HEADERS_PREF_KEY = 'ytmusic_headers'

# Main function definition
def main(context):
    """Appwrite function to interact with YTMusic API"""
    # Print basic debug info
    print("YouTube Music Recommender function started")
    
    # Get data from environment variable
    # Get User ID and Payload
    user_id = os.environ.get('APPWRITE_FUNCTION_USER_ID')
    payload_str = os.environ.get('APPWRITE_FUNCTION_DATA', '{}')
    print(f"Received payload: {payload_str}")
    print(f"Executing as user: {user_id}")
    
    # Parse input data
    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON payload: {e}")
        return context.res.json({"success": False, "error": "Invalid JSON payload"}, 400)
    except Exception as e: # Catch other potential errors during loading
        print(f"Unexpected error parsing payload: {e}")
        return context.res.json({"success": False, "error": "Error processing request data"}, 400)
    
    # Get action from data
    action = payload.get('action') # Get action, default to None if not present
    print(f"Requested action: {action}")
    
    # Validate User ID presence for most actions
    if not user_id and action != 'test_connection': # Allow test_connection without user_id
        print("Error: Missing user ID (APPWRITE_FUNCTION_USER_ID not set).")
        return context.res.json({"success": False, "error": "User context required for this action"}, 401)

    # Validate Action presence
    if not action:
        print("Error: Missing 'action' in payload.")
        return context.res.json({"success": False, "error": "Missing 'action' parameter in request"}, 400)

    print(f"Processing action '{action}' for user '{user_id or 'N/A'}'")

    # --- Appwrite Client Initialization ---
    try:
        client = Client()
        (client
         .set_endpoint(APPWRITE_ENDPOINT)
         .set_project(APPWRITE_PROJECT_ID)
         .set_key(APPWRITE_API_KEY) # Use API Key to fetch prefs
        )
        users = Users(client)
    except Exception as e:
        print(f"Error initializing Appwrite client: {e}")
        return context.res.json({"success": False, "error": "Internal server error (Appwrite client)"}, 500)

    # --- Get YTMusic Headers from User Prefs ---
    auth_headers_str = None
    try:
        # Use await since get_prefs is likely async in the Python SDK
        # get_prefs is synchronous in the Python SDK
        user_prefs = users.get_prefs(user_id=user_id)
        auth_headers_str = user_prefs.data.get(YT_HEADERS_PREF_KEY)
        if not auth_headers_str:
            print(f"Error: YouTube Music headers not found in user preferences (key: {YT_HEADERS_PREF_KEY}).")
            return context.res.json({
                "success": False,
                "error": "YouTube Music not configured. Please set up in app settings.",
                "code": "YT_SETUP_REQUIRED"
            }, 400)
    except AppwriteException as e:
        print(f"Error fetching user preferences: {e.message} (Code: {e.code})")
        # Handle specific cases like user not found (though unlikely if USER_ID is set)
        return context.res.json({"success": False, "error": f"Could not retrieve user settings: {e.message}"}, 500)
    except Exception as e:
        print(f"Unexpected error fetching user preferences: {e}")
        return context.res.json({"success": False, "error": "Internal server error (Prefs fetch)"}, 500)


    # --- YTMusicAPI Initialization ---
    try:
        headers = json.loads(auth_headers_str)
        # Use the headers directly from prefs. ytmusicapi handles defaults.
        # Ensure 'Cookie' is present, as it's essential.
        if 'Cookie' not in headers:
             print("Error: Missing required 'Cookie' header in stored preferences.")
             return context.res.json({"success": False, "error": "Invalid YouTube Music configuration (Missing Cookie). Please re-configure."}, 400)

        print(f"Using headers from prefs. Keys: {', '.join(headers.keys())}")
        ytmusic = YTMusic(auth=headers)
        print("YTMusic initialized successfully using headers from prefs.")
    except json.JSONDecodeError:
        print("Error: Invalid JSON format for stored auth_headers.")
        # Maybe prompt user to re-configure?
        return context.res.json({"success": False, "error": "Invalid YouTube Music configuration. Please re-configure in settings."}, 400)
    except Exception as e:
        print(f"Error initializing YTMusic: {e}")
        return context.res.json({"success": False, "error": f"YouTube Music initialization failed: {e}"}, 500)

    # --- Perform Action based on payload ---
    # Note: ytmusicapi methods themselves are typically synchronous.
    # If any become async in the future, you'd need 'await' here.
    try:
        if action == "get_library_playlists":
            playlists = ytmusic.get_library_playlists(limit=50)
            print(f"Fetched {len(playlists)} playlists.")
            return context.res.json({"success": True, "data": playlists})

        elif action == "get_home":
             home_feed = ytmusic.get_home(limit=20)
             print("Fetched home feed.")
             return context.res.json({"success": True, "data": home_feed})

        elif action == "get_recommendations":
            # Note: user_id might be needed if the library can't infer from headers,
            # but typically it does. Limit is optional.
            recommendations = ytmusic.get_recommendations(limit=20) # Example limit
            print(f"Fetched {len(recommendations)} recommendations.")
            return context.res.json({"success": True, "data": recommendations})
            
        elif action == "test_connection":
            # Simple test to verify authentication is working
            try:
                # Try to get library playlists as a simple test
                playlists = ytmusic.get_library_playlists(limit=1)
                print("Authentication test successful")
                # If YTMusic was initialized, connection is implicitly tested
                return context.res.json({
                    "success": True,
                    "message": "Connection and authentication test successful.",
                    "headers_found": True,
                    "python_version": sys.version
                })
            except Exception as e:
                print(f"Authentication test failed: {e}")
                # If YTMusic init failed above, this won't be reached,
                # but handle potential errors during the test call itself.
                return context.res.json({
                    "success": False,
                    "error": f"Authentication test failed during API call: {e}",
                    "code": "YT_API_ERROR"
                }, 401) # Unauthorized or Bad Request might be appropriate

        else:
            print(f"Error: Unknown action '{action}'.")
            return context.res.json({"success": False, "error": f"Unknown action: {action}"}, 400)

    except Exception as e:
        print(f"Error during YTMusic API call for action '{action}': {e}")
        # Consider logging the full traceback here for debugging
        return context.res.json({"success": False, "error": f"API call failed for action '{action}': {e}"}, 500)
