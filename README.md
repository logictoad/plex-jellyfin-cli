# Plex-Jellyfin CLI Tool

A command-line utility for synchronizing, comparing, and exporting metadata between Plex and Jellyfin media servers.  
Supports listing, exporting, fuzzy matching, watched status sync, duplicate detection, and more.

---

## Features

- **List** movies or TV shows from Plex or Jellyfin, with optional file paths and CSV export.
- **Show** details for a specific title from either server.
- **Sync** watched status between Plex and Jellyfin (both directions, with dry-run support).
- **Compare** libraries to find missing titles, with fuzzy matching and year-aware logic.
- **Detect duplicates** (combined/multi-version entries) in both servers.
- **Customizable fuzzy match threshold** for title comparison.
- **CSV export** for easy reporting.

---

## Requirements

- Python 3.7+
- [plexapi](https://github.com/pkkid/python-plexapi)
- [requests](https://pypi.org/project/requests/)
- [python-dotenv](https://pypi.org/project/python-dotenv/)
- [rapidfuzz](https://github.com/maxbachmann/RapidFuzz)
- Plex and Jellyfin API credentials in a `.env` file

---

## Setup

1. **Install dependencies:**
    ```sh
    pip install -r requirements.txt
    ```

2. **Create a `.env` file** in the same directory as `cli.py`:
    ```
    PLEX_URL=http://your-plex-server:32400
    PLEX_TOKEN=your_plex_token
    JELLYFIN_URL=http://your-jellyfin-server:8096
    JELLYFIN_USER=your_jellyfin_username
    JELLYFIN_APIKEY=your_jellyfin_apikey
    ```

---

## Usage

```sh
python cli.py [OPTIONS]
```

### List Movies or TV Shows

- **List Plex movies:**
  ```
  python cli.py --list movies plex
  ```
- **List Jellyfin TV shows:**
  ```
  python cli.py --list tv jellyfin
  ```
- **List with file paths:**
  ```
  python cli.py --list movies plex --withpath
  python cli.py --list tv jellyfin --withpath
  ```
- **Export to CSV:**
  ```
  python cli.py --list movies plex --withpath --export movies.csv
  ```

### Show Details for a Title

- **Show details for a Plex movie:**
  ```
  python cli.py --show "Movie Title" movies plex
  ```
- **Show details for a Jellyfin TV show:**
  ```
  python cli.py --show "Show Title" tv jellyfin
  ```

### Sync Watched Status

- **Sync watched status from Jellyfin to Plex (dry run):**
  ```
  python cli.py --sync jellyfin,plex movies --dryrun
  ```
- **Sync watched status from Plex to Jellyfin for TV shows:**
  ```
  python cli.py --sync plex,jellyfin tv
  ```

### Compare Libraries

- **Compare movies missing from Jellyfin:**
  ```
  python cli.py --compare movies plex jellyfin
  ```
- **Compare TV shows missing from Plex:**
  ```
  python cli.py --compare tv jellyfin plex
  ```
- **Fuzzy matching threshold (default 85):**
  ```
  python cli.py --compare tv plex jellyfin --fuzzy 90
  ```

### Detect Duplicates (Combined Versions)

- **List Plex movies with combined versions:**
  ```
  python cli.py --duplicates movies plex
  ```
- **List Jellyfin TV episodes with combined versions:**
  ```
  python cli.py --duplicates tv jellyfin
  ```

---

## Notes

- **Fuzzy matching**: The `--fuzzy` parameter controls how closely titles must match (higher = stricter).
- **Year matching**: Titles like `Title (2020)` will match `Title` if the year in metadata matches.
- **Paths**: For TV shows, the path is inferred from the first episode's file location.
- **Duplicates**: "Combined" entries are detected by multiple media sources/parts.

---

## License

MIT License

---

## Credits

- [plexapi](https://github.com/pkkid/python-plexapi)
- [Jellyfin](https://jellyfin.org/)
- [RapidFuzz](https://github.com/maxbachmann/RapidFuzz)
