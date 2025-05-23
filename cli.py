#!/usr/bin/python3

import os
import argparse
import re
import csv
from datetime import datetime as dt, timedelta
import requests
from dotenv import load_dotenv
from rapidfuzz import fuzz

from plexapi.server import PlexServer
from plexapi.exceptions import NotFound

# Load the .env file
load_dotenv()

plex_token = os.getenv("PLEX_TOKEN")
plex_url = os.getenv("PLEX_URL")

jellyfin_url = os.getenv("JELLYFIN_URL")
jellyfin_user = os.getenv("JELLYFIN_USER")
jellyfin_apikey = os.getenv("JELLYFIN_APIKEY")

plexlocal = PlexServer(plex_url, plex_token)
plex_lib_movies = plexlocal.library.section("Movies")
plex_lib_tv = plexlocal.library.section("TV Shows")


def jellyfin_headers():
    return {"X-Emby-Token": jellyfin_apikey, "Content-Type": "application/json"}


def jellyfin_get_user_id(jellyfin_username):
    """
    Looks up the Jellyfin user ID (GUID) for the given username.
    """
    url = f"{jellyfin_url}/Users"
    resp = requests.get(url, headers=jellyfin_headers(), timeout=10)
    resp.raise_for_status()
    users = resp.json()
    for user in users:
        if user.get("Name", "").lower() == jellyfin_username.lower():
            return user["Id"]
    raise ValueError(f"User '{jellyfin_username}' not found in Jellyfin users list.")


def jellyfin_get_movies(jellyfin_user_id, with_path=False):
    url = f"{jellyfin_url}/Users/{jellyfin_user_id}/Items"
    params = {"IncludeItemTypes": "Movie", "Recursive": "true"}
    if with_path:
        params["fields"] = "Path"
    resp = requests.get(url, headers=jellyfin_headers(), params=params, timeout=10)
    resp.raise_for_status()
    return resp.json().get("Items", [])


def jellyfin_get_movie_by_title(title, jellyfin_user_id):
    movies = jellyfin_get_movies(jellyfin_user_id)
    for movie in movies:
        if movie["Name"].lower() == title.lower():
            return movie
    return None


def jellyfin_mark_movie_played(movie_id, jellyfin_user_id, dryrun=False):
    url = f"{jellyfin_url}/Users/{jellyfin_user_id}/PlayedItems/{movie_id}"
    if dryrun:
        print(f"[DRYRUN] Would mark movie {movie_id} as played in Jellyfin.")
        return
    resp = requests.post(url, headers=jellyfin_headers(), timeout=10)
    if resp.status_code == 204:
        print(f"Marked movie {movie_id} as played in Jellyfin.")
    else:
        print(f"Failed to mark movie {movie_id} as played in Jellyfin.")


def jellyfin_get_tvshows(jellyfin_user_id, with_path=False):
    url = f"{jellyfin_url}/Users/{jellyfin_user_id}/Items"
    params = {"IncludeItemTypes": "Series", "Recursive": "true"}
    if with_path:
        params["fields"] = "Path"
    resp = requests.get(url, headers=jellyfin_headers(), params=params, timeout=10)
    resp.raise_for_status()
    return resp.json().get("Items", [])


def jellyfin_get_tvshow_by_title(title, jellyfin_user_id):
    shows = jellyfin_get_tvshows(jellyfin_user_id)
    for show in shows:
        if show["Name"].lower() == title.lower():
            return show
    return None


def jellyfin_get_episodes(show_id, jellyfin_user_id, with_path=False):
    url = f"{jellyfin_url}/Users/{jellyfin_user_id}/Items"
    params = {"ParentId": show_id, "IncludeItemTypes": "Episode", "Recursive": "true"}
    if with_path:
        params["fields"] = "Path"
    resp = requests.get(url, headers=jellyfin_headers(), params=params, timeout=10)
    resp.raise_for_status()
    return resp.json().get("Items", [])


def jellyfin_mark_episode_played(episode_id, jellyfin_user_id, dryrun=False):
    url = f"{jellyfin_url}/Users/{jellyfin_user_id}/PlayedItems/{episode_id}"
    if dryrun:
        print(f"[DRYRUN] Would mark episode {episode_id} as played in Jellyfin.")
        return
    resp = requests.post(url, headers=jellyfin_headers(), timeout=10)
    if resp.status_code == 204:
        print(f"Marked episode {episode_id} as played in Jellyfin.")
    else:
        print(f"Failed to mark episode {episode_id} as played in Jellyfin.")


def movies_list_all_titles(lib_movies):
    """Return all movie objects from the given Plex library section."""
    return lib_movies.search()


def movies_get_movie(lib_movies, movietitle):
    return lib_movies.get(title=movietitle)


def movie_update_addedat(lib_movies, movietitle, addedat_date, dryrun=False):
    videoentry = lib_movies.get(title=movietitle)
    dateobj = dt.strftime(videoentry.addedAt, "%Y-%m-%d %H:%M")
    dtdateobj = dt.strptime(dateobj, "%Y-%m-%d %H:%M")
    compareaddedat_date = dt.strftime(addedat_date, "%Y-%m-%d %H:%M")
    dtcompareaddedat_date = dt.strptime(compareaddedat_date, "%Y-%m-%d %H:%M")
    startdate = dtdateobj - timedelta(hours=12)
    enddate = dtdateobj + timedelta(hours=12)
    if dtcompareaddedat_date < startdate or dtcompareaddedat_date > enddate:
        print(
            f"{'[DRYRUN] ' if dryrun else ''}Updating Movie: {videoentry}, Current Date: {videoentry.addedAt}"
        )
        if not dryrun:
            updates = {"addedAt.value": addedat_date}
            videoentry.edit(**updates)


def tv_list_all_shows(lib_tv):
    return lib_tv.search()


def tv_get_show(lib_tv, tvtitle):
    return lib_tv.get(title=tvtitle)


def normalize_title(title):
    # Remove year in parentheses, e.g., "Title (2020)" -> "Title"
    title = re.sub(r"\s*\(\d{4}\)", "", title)
    # Lowercase, replace " & " and " and " with a common token, remove punctuation, and strip whitespace
    title = title.lower()
    title = re.sub(r"\s+(&|and)\s+", " and ", title)
    title = re.sub(r"[\W_]+", "", title)
    return title.strip()


def find_best_match(title, candidates, threshold=85, year=None, candidate_years=None):
    norm_title = normalize_title(title)
    for idx, candidate in enumerate(candidates):
        norm_candidate = normalize_title(candidate)
        # If titles match after normalization
        if norm_title == norm_candidate:
            # If a year is provided, check candidate year if available
            if year and candidate_years:
                candidate_year = candidate_years[idx]
                if candidate_year and str(candidate_year) == str(year):
                    return candidate
                # If no year in candidate, still allow match
                if not candidate_year:
                    return candidate
            else:
                return candidate
        # Fallback to fuzzy match
        if fuzz.token_sort_ratio(norm_title, norm_candidate) >= threshold:
            return candidate
    return None


def compare_titles(
    library, source, target, jellyfin_user_id=None, fuzzy=True, threshold=85
):
    """
    Print titles in source library that are missing from target library.
    library: "movies" or "tv"
    source/target: "plex" or "jellyfin"
    """
    if library == "movies":
        if source == "plex":
            source_titles = []
            source_years = []
            for movie in movies_list_all_titles(plex_lib_movies):
                source_titles.append(movie.title)
                source_years.append(getattr(movie, "year", None))
        else:
            source_titles = []
            source_years = []
            for movie in jellyfin_get_movies(jellyfin_user_id):
                source_titles.append(movie["Name"])
                source_years.append(movie.get("ProductionYear"))
        if target == "plex":
            target_titles = []
            target_years = []
            for movie in movies_list_all_titles(plex_lib_movies):
                target_titles.append(movie.title)
                target_years.append(getattr(movie, "year", None))
        else:
            target_titles = []
            target_years = []
            for movie in jellyfin_get_movies(jellyfin_user_id):
                target_titles.append(movie["Name"])
                target_years.append(movie.get("ProductionYear"))
    elif library == "tv":
        if source == "plex":
            source_titles = []
            source_years = []
            for show in tv_list_all_shows(plex_lib_tv):
                source_titles.append(show.title)
                source_years.append(getattr(show, "year", None))
        else:
            source_titles = []
            source_years = []
            for show in jellyfin_get_tvshows(jellyfin_user_id):
                source_titles.append(show["Name"])
                source_years.append(show.get("ProductionYear"))
        if target == "plex":
            target_titles = []
            target_years = []
            for show in tv_list_all_shows(plex_lib_tv):
                target_titles.append(show.title)
                target_years.append(getattr(show, "year", None))
        else:
            target_titles = []
            target_years = []
            for show in jellyfin_get_tvshows(jellyfin_user_id):
                target_titles.append(show["Name"])
                target_years.append(show.get("ProductionYear"))
    else:
        print("Invalid library type for comparison.")
        return

    # Normalize all titles for direct comparison
    norm_source_titles = {normalize_title(t): t for t in source_titles}
    norm_target_titles = {normalize_title(t): t for t in target_titles}

    missing = []
    for idx, (norm_title, orig_title) in enumerate(norm_source_titles.items()):
        if fuzzy:
            match = find_best_match(
                orig_title,
                target_titles,
                threshold,
                year=(source_years[idx] if "source_years" in locals() else None),
                candidate_years=(target_years if "target_years" in locals() else None),
            )
            if not match:
                missing.append(orig_title)
        else:
            if norm_title not in norm_target_titles:
                missing.append(orig_title)
    if missing:
        print(
            f"Titles in {source} {library} missing from {target} {library}: {len(missing)} of {len(source_titles)}"
        )
        for title in sorted(missing):
            print(title)
    else:
        print(f"No missing {library} titles found from {source} to {target}.")


def get_show_folder_from_episode(ep_path):
    """
    Returns the show folder given an episode file path.
    Handles both with and without a 'Season' subfolder, including 'Season 01', 'S01', 'S1', etc.
    """
    parent = os.path.dirname(ep_path)
    # If parent folder looks like 'Season 01', 'Season1', 'S01', or 'S1', go up two levels
    if re.search(r"([\\/](Season\s?\d+|S\d{1,2}))$", parent, re.IGNORECASE):
        return os.path.dirname(parent)
    return parent


def print_with_path(
    items, server_type, library_type=None, export_csv=None, jellyfin_user_id=None
):
    """
    Print item titles and, if possible, their file paths.
    For Plex TV, prints the base show folder path (from the first episode found).
    For Jellyfin TV, fetches the first episode and uses its path.
    If export_csv is a file path, writes results as CSV as well as printing to console.
    Prints each row immediately for progress, then writes all to CSV at the end if requested.
    """
    # Sort items by title/name before iterating
    if server_type == "plex":
        items = sorted(items, key=lambda x: x.title)
    elif server_type == "jellyfin":
        items = sorted(items, key=lambda x: x.get("Name", "").lower())

    rows = []
    for item in items:
        if server_type == "plex":
            if library_type == "movies":
                try:
                    if hasattr(item, "media") and item.media and item.media[0].parts:
                        path = item.media[0].parts[0].file
                    else:
                        path = "(no path)"
                except (KeyError, AttributeError, IndexError):
                    pass
                row = [item.title, path]
            elif library_type == "tv":
                show_path = "(no path)"
                try:
                    episodes = list(item.episodes())
                    if episodes:
                        ep = episodes[0]
                        if hasattr(ep, "media") and ep.media and ep.media[0].parts:
                            ep_path = ep.media[0].parts[0].file
                            show_path = get_show_folder_from_episode(ep_path)
                except (KeyError, AttributeError, IndexError):
                    pass
                row = [item.title, show_path]
            else:
                row = [str(item), ""]
        elif server_type == "jellyfin":
            if library_type == "movies":
                path = item.get("Path", "(no path)")
                row = [item.get("Name", "(no title)"), path]
            elif library_type == "tv":
                show_path = "(no path)"
                try:
                    show_id = item.get("Id")
                    if show_id and jellyfin_user_id:
                        episodes = jellyfin_get_episodes(
                            show_id, jellyfin_user_id, with_path=True
                        )
                        ep_path = None
                        for ep in episodes:
                            ep_path = ep.get("Path")
                            if ep_path:
                                break
                        if ep_path:
                            show_path = get_show_folder_from_episode(ep_path)
                except (KeyError, AttributeError, IndexError):
                    pass
                row = [item.get("Name", "(no title)"), show_path]
            else:
                row = [item.get("Name", "(no title)"), "(no path)"]
        else:
            row = [str(item), ""]
        print(" | ".join(row))
        rows.append(row)

    print(f"Total: {len(rows)}")
    if export_csv:
        with open(export_csv, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Title", "Path"])
            writer.writerows(rows)
        print(f"Exported to CSV: {export_csv}")


def list_duplicates(library, server, jellyfin_user_id=None):
    """
    List shows or movies with duplicate (combined) entries in Plex or Jellyfin.
    For Plex, checks for multiple Media objects (movies) or episodes with multiple Media objects (TV).
    For Jellyfin, checks for multiple MediaSources in a movie or episode.
    """
    if library == "movies" and server == "plex":
        movies = movies_list_all_titles(plex_lib_movies)
        for movie in sorted(movies, key=lambda x: x.title.lower()):
            if hasattr(movie, "media") and len(movie.media) > 1:
                print(f"[Plex] Movie with combined versions: {movie.title}")
    elif library == "tv" and server == "plex":
        shows = tv_list_all_shows(plex_lib_tv)
        for show in sorted(shows, key=lambda x: x.title.lower()):
            for episode in show.episodes():
                if hasattr(episode, "media") and len(episode.media) > 1:
                    print(
                        f"[Plex] Show: {show.title} | Episode: {episode.title} (Season {episode.seasonNumber}, Ep {episode.index}) has combined versions"
                    )
    elif library == "movies" and server == "jellyfin":
        movies = jellyfin_get_movies(jellyfin_user_id)
        for movie in sorted(movies, key=lambda x: x.get("Name", "").lower()):
            # MediaSources is a list of versions/files for the movie
            if movie.get("MediaSources") and len(movie["MediaSources"]) > 1:
                print(f"[Jellyfin] Movie with combined versions: {movie['Name']}")
    elif library == "tv" and server == "jellyfin":
        shows = jellyfin_get_tvshows(jellyfin_user_id)
        for show in sorted(shows, key=lambda x: x.get("Name", "").lower()):
            episodes = jellyfin_get_episodes(show["Id"], jellyfin_user_id)
            for ep in episodes:
                if ep.get("MediaSources") and len(ep["MediaSources"]) > 1:
                    print(
                        f"[Jellyfin] Show: {show['Name']} | Episode: {ep.get('Name', '')} (Season {ep.get('SeasonNumber')}, Ep {ep.get('IndexNumber')}) has combined versions"
                    )
    else:
        print(
            "Invalid parameters for --duplicates. LIBRARY must be 'movies' or 'tv', SERVER must be 'plex' or 'jellyfin'."
        )


def main():
    parser = argparse.ArgumentParser(
        description="Plex/Jellyfin Sync Utility",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  List Plex movies:
    python jellyfin_sync.py --list movies plex

  List Jellyfin TV shows:
    python jellyfin_sync.py --list tv jellyfin

  List Plex movies with file paths:
    python jellyfin_sync.py --list movies plex --withpath

  List Jellyfin TV shows with file paths:
    python jellyfin_sync.py --list tv jellyfin

  Show details for a Plex movie:
    python jellyfin_sync.py --show "Movie Title" movies plex

  Show details for a Jellyfin TV show:
    python jellyfin_sync.py --show "Show Title" tv jellyfin

  Sync watched status from Jellyfin to Plex (dry run):
    python jellyfin_sync.py --sync jellyfin,plex movies --dryrun

  Sync watched status from Plex to Jellyfin for TV shows:
    python jellyfin_sync.py --sync plex,jellyfin tv

  Compare movies missing from Jellyfin:
    python jellyfin_sync.py --compare movies plex jellyfin

  Compare TV shows missing from Plex:
    python jellyfin_sync.py --compare tv jellyfin plex

  List Plex movies with file paths and export to CSV:
    python jellyfin_sync.py --list movies plex --withpath --export movies.csv
""",
    )
    parser.add_argument(
        "--list",
        nargs=2,
        metavar=("LIBRARY", "SERVER"),
        help='List items: LIBRARY is "movies" or "tv", SERVER is "plex" or "jellyfin"',
    )
    parser.add_argument(
        "--withpath",
        action="store_true",
        help="Include file path in --list output if possible",
    )
    parser.add_argument(
        "--export", metavar="CSVFILE", help="Export results to CSV file"
    )
    parser.add_argument(
        "--show",
        nargs=3,
        metavar=("TITLE", "LIBRARY", "SERVER"),
        help="Show details for a specific title: TITLE LIBRARY SERVER",
    )
    parser.add_argument(
        "--sync",
        nargs=2,
        metavar=("DIRECTION", "LIBRARY"),
        help='Sync direction: "plex,jellyfin" or "jellyfin,plex", LIBRARY is "movies" or "tv"',
    )
    parser.add_argument(
        "--compare",
        nargs=3,
        metavar=("LIBRARY", "SOURCE", "TARGET"),
        help='Compare titles: LIBRARY is "movies" or "tv", SOURCE/TARGET is "plex" or "jellyfin"',
    )
    parser.add_argument("--dryrun", action="store_true", help="Dry run (no changes)")
    parser.add_argument(
        "--fuzzy",
        type=int,
        default=85,
        help="Fuzzy match threshold for title comparison (default: 85)",
    )
    parser.add_argument(
        "--duplicates",
        nargs=2,
        metavar=("LIBRARY", "SERVER"),
        help='List items with combined/duplicate versions: LIBRARY is "movies" or "tv", SERVER is "plex" or "jellyfin"',
    )
    args = parser.parse_args()

    # Only resolve user ID once if any Jellyfin operation is requested
    jellyfin_user_id = None
    needs_jellyfin = False
    if (
        (args.list and args.list[1].lower() == "jellyfin")
        or (args.show and args.show[2].lower() == "jellyfin")
        or (args.sync and ("jellyfin" in args.sync[0].lower()))
        or (
            args.compare
            and ("jellyfin" in [args.compare[1].lower(), args.compare[2].lower()])
        )
        or (args.duplicates and args.duplicates[1].lower() == "jellyfin")
    ):
        needs_jellyfin = True
    if needs_jellyfin:
        jellyfin_user_id = jellyfin_get_user_id(jellyfin_user)

    # List items
    if args.list:
        library = args.list[0].lower()
        server = args.list[1].lower()
        export_csv = args.export if args.export else None
        with_path = args.withpath or export_csv
        if library == "movies" and server == "plex":
            movies = movies_list_all_titles(plex_lib_movies)
            if with_path:
                print_with_path(movies, "plex", "movies", export_csv=export_csv)
            else:
                # Sort by title (case-insensitive) before printing
                sorted_movies = sorted(movies, key=lambda x: x.title.lower())
                for movie in sorted_movies:
                    print(movie.title)
                print(f"Total: {len(sorted_movies)}")
            return
        if library == "movies" and server == "jellyfin":
            movies = jellyfin_get_movies(jellyfin_user_id, with_path=with_path)
            if with_path:
                print_with_path(movies, "jellyfin", "movies", export_csv=export_csv)
            else:
                # Sort by Name (case-insensitive) before printing
                sorted_movies = sorted(movies, key=lambda x: x.get("Name", "").lower())
                for movie in sorted_movies:
                    print(movie["Name"])
                print(f"Total: {len(sorted_movies)}")
            return
        if library == "tv" and server == "plex":
            shows = tv_list_all_shows(plex_lib_tv)
            if with_path:
                print_with_path(shows, "plex", "tv", export_csv=export_csv)
            else:
                # Sort by title (case-insensitive) before printing
                sorted_shows = sorted(shows, key=lambda x: x.title.lower())
                for show in sorted_shows:
                    print(show.title)
                print(f"Total: {len(sorted_shows)}")
            return
        if library == "tv" and server == "jellyfin":
            shows = jellyfin_get_tvshows(jellyfin_user_id, with_path=with_path)
            if with_path:
                print_with_path(
                    shows,
                    "jellyfin",
                    "tv",
                    export_csv=export_csv,
                    jellyfin_user_id=jellyfin_user_id,
                )
            else:
                # Sort by Name (case-insensitive) before printing
                sorted_shows = sorted(shows, key=lambda x: x.get("Name", "").lower())
                for show in sorted_shows:
                    print(show["Name"])
                print(f"Total: {len(sorted_shows)}")
            return
        print(
            "Invalid --list parameters. LIBRARY must be 'movies' or 'tv', SERVER must be 'plex' or 'jellyfin'."
        )
        return

    # Show details
    if args.show:
        title = args.show[0]
        library = args.show[1].lower()
        server = args.show[2].lower()
        if library == "movies" and server == "plex":
            try:
                movie = movies_get_movie(plex_lib_movies, title)
                print(title, movie)
            except NotFound:
                print("Movie not found in Plex:", title)
            except (KeyError, AttributeError):
                print("Error accessing movie details in Plex:", title)
            return
        if library == "movies" and server == "jellyfin":
            movie = jellyfin_get_movie_by_title(title, jellyfin_user_id)
            if movie:
                print(title, movie)
            else:
                print("Error finding remote movie:", title)
            return
        if library == "tv" and server == "plex":
            try:
                show = tv_get_show(plex_lib_tv, title)
                print(title, show)
            except NotFound:
                print("TV show not found in Plex:", title)
            except (KeyError, AttributeError):
                print("Error accessing TV show details in Plex:", title)
            return
        if library == "tv" and server == "jellyfin":
            show = jellyfin_get_tvshow_by_title(title, jellyfin_user_id)
            if show:
                print(title, show)
            else:
                print("Error finding remote TV show:", title)
            return
        print(
            "Invalid --show parameters. LIBRARY must be 'movies' or 'tv', SERVER must be 'plex' or 'jellyfin'."
        )
        return

    # Sync
    if args.sync:
        direction = args.sync[0].lower().replace(" ", "")
        library = args.sync[1].lower()
        dryrun = args.dryrun
        if library == "movies":
            if direction == "jellyfin,plex":
                local_list = movies_list_all_titles(plex_lib_movies)
                for lmovie in local_list:
                    rmovie = jellyfin_get_movie_by_title(lmovie.title, jellyfin_user_id)
                    if not rmovie:
                        print("Unable to find movie in Jellyfin:", lmovie.title)
                        continue
                    print("Checking movie:", lmovie.title)
                    remote_addedat = dt.strptime(
                        rmovie["DateCreated"][:16], "%Y-%m-%dT%H:%M"
                    )
                    movie_update_addedat(
                        plex_lib_movies, lmovie.title, remote_addedat, dryrun=dryrun
                    )
                    if rmovie.get("UserData", {}).get("Played", False):
                        if not lmovie.isPlayed:
                            print(
                                f"{'[DRYRUN] ' if dryrun else ''}Remote watched and local unwatched. Changing:"
                            )
                            if not dryrun:
                                lmovie.markPlayed()
            if direction == "plex,jellyfin":
                movies = movies_list_all_titles(plex_lib_movies)
                for lmovie in movies:
                    rmovie = jellyfin_get_movie_by_title(lmovie.title, jellyfin_user_id)
                    if not rmovie:
                        print("Unable to find movie in Jellyfin:", lmovie.title)
                        continue
                    print("Checking movie:", lmovie.title)
                    if lmovie.isPlayed and not rmovie.get("UserData", {}).get(
                        "Played", False
                    ):
                        print(
                            f"{'[DRYRUN] ' if dryrun else ''}Local watched and remote unwatched. Marking remote as played."
                        )
                        jellyfin_mark_movie_played(
                            rmovie["Id"], jellyfin_user_id, dryrun=dryrun
                        )
            print("Unknown sync direction. Use 'plex,jellyfin' or 'jellyfin,plex'.")
            return
        if library == "tv":
            if direction == "jellyfin,plex":
                local_shows = tv_list_all_shows(plex_lib_tv)
                for lshow in local_shows:
                    rshow = jellyfin_get_tvshow_by_title(lshow.title, jellyfin_user_id)
                    if not rshow:
                        print("Unable to find show in Jellyfin:", lshow.title)
                        continue
                    print("Checking show:", lshow.title)
                    local_episodes = lshow.episodes()
                    remote_episodes = jellyfin_get_episodes(
                        rshow["Id"], jellyfin_user_id
                    )
                    for lepisode in local_episodes:
                        match = next(
                            (
                                re
                                for re in remote_episodes
                                if re["IndexNumber"] == lepisode.index
                                and re["SeasonNumber"] == lepisode.seasonNumber
                            ),
                            None,
                        )
                        if match and match.get("UserData", {}).get("Played", False):
                            if not lepisode.isPlayed:
                                print(
                                    f"{'[DRYRUN] ' if dryrun else ''}Remote watched and local unwatched for {lepisode.title}. Marking local as played."
                                )
                                if not dryrun:
                                    lepisode.markPlayed()
            if direction == "plex,jellyfin":
                local_shows = tv_list_all_shows(plex_lib_tv)
                for lshow in local_shows:
                    rshow = jellyfin_get_tvshow_by_title(lshow.title, jellyfin_user_id)
                    if not rshow:
                        print("Unable to find show in Jellyfin:", lshow.title)
                        continue
                    print("Checking show:", lshow.title)
                    local_episodes = lshow.episodes()
                    remote_episodes = jellyfin_get_episodes(
                        rshow["Id"], jellyfin_user_id
                    )
                    for lepisode in local_episodes:
                        match = next(
                            (
                                re
                                for re in remote_episodes
                                if re["IndexNumber"] == lepisode.index
                                and re["SeasonNumber"] == lepisode.seasonNumber
                            ),
                            None,
                        )
                        if (
                            match
                            and lepisode.isPlayed
                            and not match.get("UserData", {}).get("Played", False)
                        ):
                            print(
                                f"{'[DRYRUN] ' if dryrun else ''}Local watched and remote unwatched for {lepisode.title}. Marking remote as played."
                            )
                            jellyfin_mark_episode_played(
                                match["Id"], jellyfin_user_id, dryrun=dryrun
                            )
            print("Unknown sync direction. Use 'plex,jellyfin' or 'jellyfin,plex'.")
            return
        print("Invalid --sync parameters. LIBRARY must be 'movies' or 'tv'.")
        return

    # Compare
    if args.compare:
        library = args.compare[0].lower()
        source = args.compare[1].lower()
        target = args.compare[2].lower()
        compare_titles(library, source, target, jellyfin_user_id, threshold=args.fuzzy)
        return

    # Duplicates
    if args.duplicates:
        library = args.duplicates[0].lower()
        server = args.duplicates[1].lower()
        list_duplicates(library, server, jellyfin_user_id=jellyfin_user_id)
        return

    print("No valid action specified. Use --help for options.")


if __name__ == "__main__":
    main()
