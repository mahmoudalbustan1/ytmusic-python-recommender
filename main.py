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
    # Get Payload
    payload_str = os.environ.get('APPWRITE_FUNCTION_DATA', '{}')
    context.log(f"Received payload: {payload_str}")
    
    # Print detailed debug information
    context.log(f"Function data environment variable: {os.environ.get('APPWRITE_FUNCTION_DATA', 'None')}")
    context.log(f"Headers in request: {dir(context.req.headers) if hasattr(context.req, 'headers') else 'No headers attribute'}")
    
    # Parse payload to check for direct auth_headers or user_id
    try:
        payload = json.loads(payload_str)
        # Log the entire payload for debugging
        context.log(f"Full payload: {json.dumps(payload)}")
        context.log(f"Payload keys: {list(payload.keys()) if isinstance(payload, dict) else 'Not a dict'}")
    except json.JSONDecodeError as e:
        context.error(f"Error parsing JSON payload: {e}")
        return context.res.json({"success": False, "error": "Invalid JSON payload"}, 400)
    except Exception as e:
        context.error(f"Unexpected error parsing payload: {e}")
        return context.res.json({"success": False, "error": "Error processing request data"}, 400)
    
    # Check for auth_headers directly in payload
    auth_headers_str = payload.get('auth_headers')
    if auth_headers_str:
        context.log(f"Found auth_headers in payload with length: {len(str(auth_headers_str))}")
    else:
        context.log("No auth_headers found in payload")
    
    # Get user_id from various sources
    env_user_id = os.environ.get('APPWRITE_FUNCTION_USER_ID')
    user_id = payload.get('user_id', env_user_id)
    context.log(f"User ID from payload: {payload.get('user_id', 'None')}")
    context.log(f"User ID from env: {env_user_id}")
    context.log(f"Final User ID: {user_id}")
    
    # Payload is already parsed above
    
    # Get action from data
    action = payload.get('action') # Get action, default to None if not present
    context.log(f"Requested action: {action}") # Use context.log
    
    # For test_connection with direct auth_headers, we don't need user_id
    if action == 'test_connection':
        context.log("Test connection requested, proceeding without user ID check")
    # For other actions without auth_headers, validate user ID presence
    elif not auth_headers_str and not user_id:
        context.error("Missing both user ID and auth_headers. Action requires either user context or direct auth headers.")
        return context.res.json({"success": False, "error": "User authentication required"}, 401)

    # Validate Action presence
    if not action:
        context.error("Missing 'action' in payload.") # Use context.error
        return context.res.json({"success": False, "error": "Missing 'action' parameter in request"}, 400)

    context.log(f"Processing action '{action}' for user '{user_id or 'N/A'}'") # Use context.log

    # We'll initialize the client only if we need to fetch user prefs

    # --- Get YTMusic Headers ---
    auth_headers_str = None
    
    # First check if auth_headers were provided directly in the payload (preferred method)
    if auth_headers_str:
        context.log("Using auth_headers directly from payload")
    # Otherwise, if we have a user_id, try to get from user prefs
    elif user_id:
        try:
            # Initialize Appwrite client to get prefs
            client = Client()
            client.set_endpoint(APPWRITE_ENDPOINT).set_project(APPWRITE_PROJECT_ID).set_key(APPWRITE_API_KEY)
            users = Users(client)
            
            # Get user prefs
            user_prefs = users.get_prefs(user_id=user_id)
            auth_headers_str = user_prefs.get(YT_HEADERS_PREF_KEY) # Use .get on the dict directly
            
            if not auth_headers_str:
                context.error(f"YouTube Music headers not found in user preferences (key: {YT_HEADERS_PREF_KEY}).")
                return context.res.json({
                    "success": False,
                    "error": "YouTube Music not configured. Please set up in app settings.",
                    "code": "YT_SETUP_REQUIRED"
                }, 400)
                
            context.log("Retrieved auth_headers from user preferences")
        except AppwriteException as e:
            context.error(f"Appwrite error fetching user preferences: {e.message} (Code: {e.code})")
            return context.res.json({"success": False, "error": f"Could not retrieve user settings: {e.message}"}, e.code if e.code >= 400 else 500)
        except Exception as e:
            context.error(f"Unexpected error fetching user preferences: {e}")
            return context.res.json({"success": False, "error": "Internal server error (Prefs fetch)"}, 500)
    # If this is a test_connection with no auth_headers and no user_id
    elif action == 'test_connection':
        return context.res.json({
            "success": True,
            "message": "Connection successful but no auth headers available",
            "requires_setup": True
        })
    else:
        context.error("No auth_headers available and no user_id to fetch them")
        return context.res.json({
            "success": False,
            "error": "YouTube Music not configured. No authentication headers available.",
            "code": "YT_SETUP_REQUIRED"
        }, 400)


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
