import os
import json
import sys

# Import packages
# Use the standard Appwrite exception import
from appwrite.client import Client
from appwrite.services.users import Users
from appwrite.exception import AppwriteException
# Use context.log for startup messages if context is available early,
# otherwise print is okay here before main() is called.
print("Imported Appwrite SDK")
try:
    from ytmusicapi import YTMusic
    print("Successfully imported ytmusicapi") # Print is okay here
except ImportError as e:
    print(f"Failed to import ytmusicapi: {e}") # Print is okay here

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
    context.log("YouTube Music Recommender function started")
    # context.log already called at the start
    
    # Get data from environment variable
    # Get User ID and Payload
    user_id = os.environ.get('APPWRITE_FUNCTION_USER_ID')
    payload_str = os.environ.get('APPWRITE_FUNCTION_DATA', '{}')
    context.log(f"Received payload: {payload_str}")
    context.log(f"Executing as user: {user_id}")
    
    # Parse input data
    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError as e:
        context.error(f"Error parsing JSON payload: {e}")
        return context.res.json({"success": False, "error": "Invalid JSON payload"}, 400)
    except Exception as e: # Catch other potential errors during loading
        context.error(f"Unexpected error parsing payload: {e}")
        return context.res.json({"success": False, "error": "Error processing request data"}, 400)
    
    # Get action from data
    action = payload.get('action') # Get action, default to None if not present
    context.log(f"Requested action: {action}") # Use context.log
    
    # Validate User ID presence for most actions
    if not user_id and action != 'test_connection': # Allow test_connection without user_id
        context.error("Missing user ID (APPWRITE_FUNCTION_USER_ID not set). Action requires user context.") # Use context.error
        return context.res.json({"success": False, "error": "User context required for this action"}, 401)

    # Validate Action presence
    if not action:
        context.error("Missing 'action' in payload.") # Use context.error
        return context.res.json({"success": False, "error": "Missing 'action' parameter in request"}, 400)

    context.log(f"Processing action '{action}' for user '{user_id or 'N/A'}'") # Use context.log

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
        context.error(f"Error initializing Appwrite client: {e}") # Use context.error
        return context.res.json({"success": False, "error": "Internal server error (Appwrite client)"}, 500)

    # --- Get YTMusic Headers from User Prefs ---
    auth_headers_str = None
    try:
        # Use await since get_prefs is likely async in the Python SDK
        # get_prefs is synchronous in the Python SDK
        user_prefs = users.get_prefs(user_id=user_id)
        auth_headers_str = user_prefs.get(YT_HEADERS_PREF_KEY) # Use .get on the dict directly
        if not auth_headers_str:
            context.error(f"YouTube Music headers not found in user preferences (key: {YT_HEADERS_PREF_KEY}).") # Use context.error
            return context.res.json({
                "success": False,
                "error": "YouTube Music not configured. Please set up in app settings.",
                "code": "YT_SETUP_REQUIRED"
            }, 400)
    except AppwriteException as e:
        context.error(f"Appwrite error fetching user preferences: {e.message} (Code: {e.code})") # Use context.error
        # Handle specific cases like user not found (though unlikely if USER_ID is set)
        return context.res.json({"success": False, "error": f"Could not retrieve user settings: {e.message}"}, e.code if e.code >= 400 else 500)
    except Exception as e:
        context.error(f"Unexpected error fetching user preferences: {e}") # Use context.error
        return context.res.json({"success": False, "error": "Internal server error (Prefs fetch)"}, 500)


    # --- YTMusicAPI Initialization ---
    try:
        headers = json.loads(auth_headers_str)
        # Use the headers directly from prefs. ytmusicapi handles defaults.
        # Ensure 'Cookie' is present, as it's essential.
        if 'Cookie' not in headers:
             context.error("Missing required 'Cookie' header in stored preferences.") # Use context.error
             return context.res.json({"success": False, "error": "Invalid YouTube Music configuration (Missing Cookie). Please re-configure."}, 400)

        context.log(f"Using headers from prefs. Keys: {', '.join(headers.keys())}") # Use context.log
        ytmusic = YTMusic(auth=headers)
        context.log("YTMusic initialized successfully using headers from prefs.") # Use context.log
    except json.JSONDecodeError:
        context.error(f"Invalid JSON format for stored auth_headers: {e}") # Use context.error and include exception
        # Maybe prompt user to re-configure?
        return context.res.json({"success": False, "error": "Invalid YouTube Music configuration (Bad JSON). Please re-configure."}, 400)
    except Exception as e:
        context.error(f"Error initializing YTMusic: {e}") # Use context.error
        return context.res.json({"success": False, "error": f"YouTube Music initialization failed: {e}"}, 500)

    # --- Perform Action based on payload ---
    # Note: ytmusicapi methods themselves are typically synchronous.
    # If any become async in the future, you'd need 'await' here.
    try:
        if action == "get_library_playlists":
            playlists = ytmusic.get_library_playlists(limit=50)
            context.log(f"Fetched {len(playlists)} playlists.") # Use context.log
            return context.res.json({"success": True, "data": playlists})

        elif action == "get_home":
             home_feed = ytmusic.get_home(limit=20)
             context.log("Fetched home feed.") # Use context.log
             return context.res.json({"success": True, "data": home_feed})

        elif action == "get_recommendations":
            # Note: user_id might be needed if the library can't infer from headers,
            # but typically it does. Limit is optional.
            recommendations = ytmusic.get_recommendations(limit=20) # Example limit
            context.log(f"Fetched {len(recommendations)} recommendations.") # Use context.log
            return context.res.json({"success": True, "data": recommendations})
            
        elif action == "test_connection":
            # Simple test to verify authentication is working
            try:
                # Try to get library playlists as a simple test
                playlists = ytmusic.get_library_playlists(limit=1)
                context.log("Authentication test successful (fetched playlists).") # Use context.log
                # If YTMusic was initialized, connection is implicitly tested
                return context.res.json({
                    "success": True,
                    "message": "Connection and authentication test successful.",
                    "headers_found": True,
                    "python_version": sys.version
                })
            except Exception as e:
                context.error(f"Authentication test failed during API call: {e}") # Use context.error
                # If YTMusic init failed above, this won't be reached,
                # but handle potential errors during the test call itself.
                return context.res.json({
                    "success": False,
                    "error": f"Authentication test failed during API call: {e}",
                    "code": "YT_API_ERROR" # Keep code consistent
                }, 401) # Unauthorized or Bad Request might be appropriate

        else:
            context.error(f"Unknown action '{action}'.") # Use context.error
            return context.res.json({"success": False, "error": f"Unknown action: {action}"}, 400)

    except Exception as e:
        context.error(f"Error during YTMusic API call for action '{action}': {e}") # Use context.error
        # Consider logging the full traceback here for debugging
        # Consider adding traceback here for detailed debugging if needed:
        # import traceback
        # context.error(traceback.format_exc())
        return context.res.json({"success": False, "error": f"API call failed for action '{action}': {e}"}, 500)
