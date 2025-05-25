from plexapi.server import PlexServer
from datetime import datetime as dt, timedelta

class PlexConnectionError(Exception):
    pass

def plex_get_server(plex_url, plex_token):
    """Return a PlexServer instance, or print a friendly error if connection fails."""
    try:
        return PlexServer(plex_url, plex_token)
    except Exception as e:
        print(f"[ERROR] Could not connect to Plex server at {plex_url}. Is it online and reachable?\nDetails: {e}")
        raise PlexConnectionError(f"Could not connect to Plex server at {plex_url}") from e

def plex_get_movies(plex_server):
    """Return the Plex movies library section."""
    return plex_server.library.section("Movies")

def plex_list_all_movies(lib_movies):
    """Return all movie objects from the given Plex library section."""
    return lib_movies.search()

def plex_get_movie(lib_movies, movietitle):
    """Get a Plex movie by title from the given library section."""
    return lib_movies.get(title=movietitle)

def plex_update_movie_addedat(lib_movies, movietitle, addedat_date, dryrun=False):
    """Update the 'addedAt' date for a Plex movie. Supports dry run."""
    videoentry = lib_movies.get(title=movietitle)
    dateobj = videoentry.addedAt.strftime("%Y-%m-%d %H:%M")
    dtdateobj = dt.strptime(dateobj, "%Y-%m-%d %H:%M")
    compareaddedat_date = addedat_date.strftime("%Y-%m-%d %H:%M")
    dtcompareaddedat_date = dt.strptime(compareaddedat_date, "%Y-%m-%d %H:%M")
    startdate = dtdateobj - timedelta(hours=12)
    enddate = dtdateobj + timedelta(hours=12)
    if dtcompareaddedat_date < startdate or dtcompareaddedat_date > enddate:
        print(f"{'[DRYRUN] ' if dryrun else ''}Updating Movie: {videoentry}, Current Date: {videoentry.addedAt}")
        if not dryrun:
            updates = {"addedAt.value": addedat_date}
            videoentry.edit(**updates)

def plex_list_all_shows(lib_tv):
    """Return all TV show objects from the given Plex library section."""
    return lib_tv.search()

def plex_get_show(lib_tv, tvtitle):
    """Get a Plex TV show by title from the given library section."""
    return lib_tv.get(title=tvtitle)

def plex_mark_movie_played(movie, dryrun=False):
    """Mark a Plex movie as played. Supports dry run."""
    if dryrun:
        print(f"[DRYRUN] Would mark movie '{movie.title}' as played in Plex.")
        return
    movie.markPlayed()
    print(f"Marked movie '{movie.title}' as played in Plex.")

def plex_mark_episode_played(episode, dryrun=False):
    """Mark a Plex episode as played. Supports dry run."""
    if dryrun:
        print(f"[DRYRUN] Would mark episode '{episode.title}' as played in Plex.")
        return
    episode.markPlayed()
    print(f"Marked episode '{episode.title}' as played in Plex.")