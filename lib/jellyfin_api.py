import requests
from requests.exceptions import RequestException, ReadTimeout, ConnectionError

def jellyfin_headers(jellyfin_apikey):
    """Return headers for Jellyfin API requests."""
    return {"X-Emby-Token": jellyfin_apikey, "Content-Type": "application/json"}

def jellyfin_get_user_id(jellyfin_url, jellyfin_apikey, username):
    """Look up the Jellyfin user ID (GUID) for the given username."""
    url = f"{jellyfin_url}/Users"
    try:
        resp = requests.get(url, headers=jellyfin_headers(jellyfin_apikey), timeout=10)
        resp.raise_for_status()
        for user in resp.json():
            if user["Name"].lower() == username.lower():
                return user["Id"]
        return None
    except (ReadTimeout, ConnectionError):
        print(f"Error: Could not connect to Jellyfin server at {jellyfin_url} (timeout or connection error). Please check the server status and your network connection.")
        return None
    except RequestException as e:
        print(f"Error: Failed to connect to Jellyfin server: {e}")
        return None

def jellyfin_get_movies(jellyfin_url, jellyfin_apikey, user_id, with_path=False):
    """Get all movies for a Jellyfin user. Optionally include file paths."""
    url = f"{jellyfin_url}/Users/{user_id}/Items"
    params = {"IncludeItemTypes": "Movie", "Recursive": "true"}
    if with_path:
        params["fields"] = "Path"
    try:
        resp = requests.get(url, headers=jellyfin_headers(jellyfin_apikey), params=params, timeout=10)
        resp.raise_for_status()
        return resp.json().get("Items", [])
    except (ReadTimeout, ConnectionError):
        print(f"Error: Could not connect to Jellyfin server at {jellyfin_url} (timeout or connection error). Please check the server status and your network connection.")
        return []
    except RequestException as e:
        print(f"Error: Failed to connect to Jellyfin server: {e}")
        return []

def jellyfin_get_movie_by_title(title, jellyfin_url, jellyfin_apikey, user_id):
    """Get a Jellyfin movie by title for a given user."""
    movies = jellyfin_get_movies(jellyfin_url, jellyfin_apikey, user_id)
    for movie in movies:
        if movie["Name"].lower() == title.lower():
            return movie
    return None

def jellyfin_get_tvshows(jellyfin_url, jellyfin_apikey, user_id, with_path=False):
    """Get all TV shows for a Jellyfin user. Optionally include file paths."""
    url = f"{jellyfin_url}/Users/{user_id}/Items"
    params = {"IncludeItemTypes": "Series", "Recursive": "true"}
    if with_path:
        params["fields"] = "Path"
    try:
        resp = requests.get(url, headers=jellyfin_headers(jellyfin_apikey), params=params, timeout=10)
        resp.raise_for_status()
        return resp.json().get("Items", [])
    except (ReadTimeout, ConnectionError):
        print(f"Error: Could not connect to Jellyfin server at {jellyfin_url} (timeout or connection error). Please check the server status and your network connection.")
        return []
    except RequestException as e:
        print(f"Error: Failed to connect to Jellyfin server: {e}")
        return []

def jellyfin_get_tvshow_by_title(title, jellyfin_url, jellyfin_apikey, user_id):
    """Get a Jellyfin TV show by title for a given user."""
    shows = jellyfin_get_tvshows(jellyfin_url, jellyfin_apikey, user_id)
    for show in shows:
        if show["Name"].lower() == title.lower():
            return show
    return None

def jellyfin_get_episodes(show_id, jellyfin_url, jellyfin_apikey, user_id, with_path=False):
    """Get all episodes for a Jellyfin show and user. Optionally include file paths."""
    url = f"{jellyfin_url}/Users/{user_id}/Items"
    params = {"ParentId": show_id, "IncludeItemTypes": "Episode", "Recursive": "true"}
    if with_path:
        params["fields"] = "Path"
    try:
        resp = requests.get(url, headers=jellyfin_headers(jellyfin_apikey), params=params, timeout=10)
        resp.raise_for_status()
        return resp.json().get("Items", [])
    except (ReadTimeout, ConnectionError):
        print(f"Error: Could not connect to Jellyfin server at {jellyfin_url} (timeout or connection error). Please check the server status and your network connection.")
        return []
    except RequestException as e:
        print(f"Error: Failed to connect to Jellyfin server: {e}")
        return []

def jellyfin_mark_movie_played(movie_id, jellyfin_url, jellyfin_apikey, user_id, dryrun=False):
    """Mark a Jellyfin movie as played for a user. Supports dry run."""
    url = f"{jellyfin_url}/Users/{user_id}/PlayedItems/{movie_id}"
    if dryrun:
        print(f"[DRYRUN] Would mark movie {movie_id} as played in Jellyfin.")
        return
    try:
        resp = requests.post(url, headers=jellyfin_headers(jellyfin_apikey), timeout=10)
        if resp.status_code == 204:
            print(f"Marked movie {movie_id} as played in Jellyfin.")
        else:
            print(f"Failed to mark movie {movie_id} as played in Jellyfin.")
    except (ReadTimeout, ConnectionError):
        print(f"Error: Could not connect to Jellyfin server at {jellyfin_url} (timeout or connection error). Please check the server status and your network connection.")
    except RequestException as e:
        print(f"Error: Failed to connect to Jellyfin server: {e}")

def jellyfin_mark_episode_played(episode_id, jellyfin_url, jellyfin_apikey, user_id, dryrun=False):
    """Mark a Jellyfin episode as played for a user. Supports dry run."""
    url = f"{jellyfin_url}/Users/{user_id}/PlayedItems/{episode_id}"
    if dryrun:
        print(f"[DRYRUN] Would mark episode {episode_id} as played in Jellyfin.")
        return
    try:
        resp = requests.post(url, headers=jellyfin_headers(jellyfin_apikey), timeout=10)
        if resp.status_code == 204:
            print(f"Marked episode {episode_id} as played in Jellyfin.")
        else:
            print(f"Failed to mark episode {episode_id} as played in Jellyfin.")
    except (ReadTimeout, ConnectionError):
        print(f"Error: Could not connect to Jellyfin server at {jellyfin_url} (timeout or connection error). Please check the server status and your network connection.")
    except RequestException as e:
        print(f"Error: Failed to connect to Jellyfin server: {e}")