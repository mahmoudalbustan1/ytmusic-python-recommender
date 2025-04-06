import os
import json
import sys

# Try to import the Appwrite SDK with robust error handling
try:
    from appwrite.client import Client
    from appwrite.services.users import Users
    try:
        # First try the exceptions (plural) module
        from appwrite.exceptions import AppwriteException
        print("Successfully imported from appwrite.exceptions")
    except ImportError as e1:
        print(f"Failed to import from appwrite.exceptions: {e1}")
        try:
            # Then try the exception (singular) module
            from appwrite.exception import AppwriteException
            print("Successfully imported from appwrite.exception")
        except ImportError as e2:
            print(f"Failed to import from appwrite.exception: {e2}")
            # Use a generic Exception as fallback
            print("Using generic Exception as fallback")
            AppwriteException = Exception
except ImportError as e:
    print(f"Failed to import Appwrite SDK: {e}")
    sys.exit(1)

from ytmusicapi import YTMusic

# Appwrite Environment Variables - These are automatically provided by Appwrite
APPWRITE_ENDPOINT = os.environ.get("APPWRITE_ENDPOINT") # Automatically set by Appwrite
APPWRITE_PROJECT_ID = os.environ.get("APPWRITE_PROJECT_ID") # Automatically set by Appwrite
APPWRITE_API_KEY = os.environ.get("APPWRITE_API_KEY") # Server API Key for admin actions like getting prefs
APPWRITE_FUNCTION_USER_ID = os.environ.get("APPWRITE_FUNCTION_USER_ID") # Automatically set to the user who triggered the function

# Key used to store headers in Appwrite User Prefs
YT_HEADERS_PREF_KEY = "ytmusic_headers"

# Expected payload structure:
# {
#   "action": "get_library_playlists" | "get_home" | ...
#   # No auth_headers needed here anymore
# }

async def main(context):
    """
    Appwrite function entry point for v3 runtime to interact with YouTube Music API,
    retrieving auth headers from user preferences.
    """
    # Extract request and response objects from context
    req = context.req
    res = context.res
    payload_str = req.payload or '{}'
    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError:
        print("Error: Invalid JSON payload.")
        return res.json({"success": False, "error": "Invalid JSON payload"}, 400)

    action = payload.get("action")

    if not action:
        print("Error: Missing 'action' in payload.")
        return res.json({"success": False, "error": "Missing 'action'"}, 400)

    # Get user_id from payload if provided, otherwise use the function user ID
    user_id = payload.get("user_id") or APPWRITE_FUNCTION_USER_ID
    
    if not user_id:
        print("Error: No user ID found in payload or environment.")
        return res.json({"success": False, "error": "User authentication required"}, 401)
        
    print(f"Using user ID: {user_id}")

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
        return res.json({"success": False, "error": "Internal server error (Appwrite client)"}, 500)

    # --- Get YTMusic Headers from User Prefs ---
    auth_headers_str = None
    try:
        # Use await since get_prefs is likely async in the Python SDK
        user_prefs = await users.get_prefs(user_id=user_id)
        auth_headers_str = user_prefs.data.get(YT_HEADERS_PREF_KEY)
        if not auth_headers_str:
            print(f"Error: YouTube Music headers not found in user preferences (key: {YT_HEADERS_PREF_KEY}).")
            return res.json({
                "success": False,
                "error": "YouTube Music not configured. Please set up in app settings.",
                "code": "YT_SETUP_REQUIRED"
            }, 400)
    except AppwriteException as e:
        print(f"Error fetching user preferences: {e.message} (Code: {e.code})")
        # Handle specific cases like user not found (though unlikely if USER_ID is set)
        return res.json({"success": False, "error": f"Could not retrieve user settings: {e.message}"}, 500)
    except Exception as e:
        print(f"Unexpected error fetching user preferences: {e}")
        return res.json({"success": False, "error": "Internal server error (Prefs fetch)"}, 500)


    # --- YTMusicAPI Initialization ---
    try:
        headers = json.loads(auth_headers_str)
        print(f"Headers keys: {', '.join(headers.keys())}")
        
        # Ensure we have the required Cookie header
        if 'Cookie' not in headers:
            print("Error: Missing required Cookie header")
            return res.json({"success": False, "error": "Invalid YouTube Music configuration. Missing Cookie header."}, 400)
        
        # Ensure all required headers are present in the exact format needed
        required_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:72.0) Gecko/20100101 Firefox/72.0',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Content-Type': 'application/json',
            'X-Goog-AuthUser': '0',
            'x-origin': 'https://music.youtube.com'
        }
        
        # Merge the stored headers with the required headers, ensuring Cookie from user is preserved
        final_headers = {
            **required_headers,
            'Cookie': headers['Cookie']
        }
        
        print("Final headers prepared with required fields")
        
        # YTMusic initialization itself is synchronous
        ytmusic = YTMusic(auth=final_headers)
        print("YTMusic initialized successfully using headers from prefs.")
    except json.JSONDecodeError:
        print("Error: Invalid JSON format for stored auth_headers.")
        # Maybe prompt user to re-configure?
        return res.json({"success": False, "error": "Invalid YouTube Music configuration. Please re-configure in settings."}, 400)
    except Exception as e:
        print(f"Error initializing YTMusic: {e}")
        return res.json({"success": False, "error": f"YouTube Music initialization failed: {e}"}, 500)

    # --- Perform Action based on payload ---
    # Note: ytmusicapi methods themselves are typically synchronous.
    # If any become async in the future, you'd need 'await' here.
    try:
        if action == "get_library_playlists":
            playlists = ytmusic.get_library_playlists(limit=50)
            print(f"Fetched {len(playlists)} playlists.")
            return res.json({"success": True, "data": playlists})

        elif action == "get_home":
             home_feed = ytmusic.get_home(limit=20)
             print("Fetched home feed.")
             return res.json({"success": True, "data": home_feed})

        elif action == "get_recommendations":
            # Note: user_id might be needed if the library can't infer from headers,
            # but typically it does. Limit is optional.
            recommendations = ytmusic.get_recommendations(limit=20) # Example limit
            print(f"Fetched {len(recommendations)} recommendations.")
            return res.json({"success": True, "data": recommendations})
            
        elif action == "test_connection":
            # Simple test to verify authentication is working
            try:
                # Try to get library playlists as a simple test
                playlists = ytmusic.get_library_playlists(limit=1)
                print("Authentication test successful")
                return res.json({
                    "success": True, 
                    "data": "Connection successful",
                    "headers_available": True,
                    "python_version": "3.10"
                })
            except Exception as e:
                print(f"Authentication test failed: {e}")
                return res.json({
                    "success": False,
                    "error": f"Authentication test failed: {e}",
                    "code": "API_ERROR"
                }, 401)

        else:
            print(f"Error: Unknown action '{action}'.")
            return res.json({"success": False, "error": f"Unknown action: {action}"}, 400)

    except Exception as e:
        print(f"Error during YTMusic API call for action '{action}': {e}")
        # Consider logging the full traceback here for debugging
        return res.json({"success": False, "error": f"API call failed for action '{action}': {e}"}, 500)
