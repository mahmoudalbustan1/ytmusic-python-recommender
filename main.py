import os
import json
import sys

# Import minimal dependencies
try:
    from ytmusicapi import YTMusic
    print("Successfully imported ytmusicapi")
except ImportError as e:
    print(f"Failed to import ytmusicapi: {e}")

# Super simple function that just works with mock data
def main(context):
    """Simplified function that returns mock data for YouTube Music"""
    # Get the payload data
    try:
        payload_str = os.environ.get('APPWRITE_FUNCTION_DATA', '{}')
        payload = json.loads(payload_str)
        action = payload.get('action', 'test_connection')
    except Exception as e:
        # Even if there's an error, just log it and continue with defaults
        print(f"Error parsing payload: {e}")
        payload = {}
        action = 'test_connection'
    
    # Print debug info
    print(f"Action: {action}")
    print(f"Payload: {payload}")
    print(f"Environment: {dict(os.environ)}")
    
    # For test_connection, just return success
    if action == 'test_connection':
        return {
            "success": True,
            "message": "Connection successful!",
            "action": action,
            "python_version": sys.version
        }
        
    # For get_library_playlists, return dummy data
    elif action == 'get_library_playlists':
        return {
            "success": True,
            "data": [
                {"id": "PL123", "title": "My Playlist 1"},
                {"id": "PL456", "title": "My Playlist 2"}
            ]
        }
        
    # For get_home, return dummy data
    elif action == 'get_home':
        return {
            "success": True,
            "data": [
                {"title": "Recommended for you", "items": [
                    {"id": "song1", "title": "Song 1", "artist": "Artist 1"},
                    {"id": "song2", "title": "Song 2", "artist": "Artist 2"}
                ]}
            ]
        }
        
    # For get_recommendations, return dummy data
    elif action == 'get_recommendations':
        return {
            "success": True,
            "data": [
                {"id": "song3", "title": "Song 3", "artist": "Artist 3"},
                {"id": "song4", "title": "Song 4", "artist": "Artist 4"}
            ]
        }
        
    # For any other action, return an error
    else:
        return {
            "success": False,
            "error": f"Unknown action: {action}"
        }
        # Consider adding traceback here for detailed debugging if needed:
        # import traceback
        # context.error(traceback.format_exc())
        return context.res.json({"success": False, "error": f"API call failed for action '{action}': {e}"}, 500)
