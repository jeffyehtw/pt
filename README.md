# pt

A comprehensive suite of management tools for **Synology Download Station**, **qBittorrent**, and **M-Team** torrent tracker. This project provides automated task management, torrent searching, metadata synchronization, and file maintenance.

## 🚀 Key Features

*   **Synology & qBittorrent Task Automation**: Automatically clean up stuck downloads, manage seeding time limits, and resume errored tasks.
*   **M-Team Integration**: Search for torrents based on categories, filter for "Free Leech" status, and download directly.
*   **Automatic Categorization**: Torrents are automatically routed to specific Synology or qBittorrent subdirectories (e.g., Movie, TV, Music) based on M-Team metadata.
*   **Targeted Checks**: Optimized existence checks that only scan specific category folders, reducing disk I/O.
*   **Free Period Protection**: Skip scheduled "Free Leech" expiry checks during specific periods while maintaining other tasks.
*   **Smart Cleanup**: Automatically removes used `.torrent` files and orphaned metadata to keep your directories tidy.
*   **Progress-Based Stalling**: Detects dead downloads by tracking actual data progress over time, regardless of speed.

---

## 📂 Project Structure

```text
pt/
├── config/         # Centralized configuration and state
│   ├── path.json       # Category-specific local and NAS paths
│   ├── mt.json         # M-Team API credentials and skip periods
│   ├── syno.json       # Synology NAS credentials and limits
│   ├── list.json       # Persistence: Download history
│   └── last_status.json # State: Task progress tracking
├── manage.py       # Synology task lifecycle manager & maintenance
├── cleanup.py      # Metadata & unused torrent cleanup utility
├── search.py       # M-Team interactive search & categorized download
├── download.py     # Direct M-Team download & categorized task creation
├── purge.py        # Advanced manual file/directory purge utility
├── finder.py       # Standardized debug utility to locate NAS tasks
├── import_local_to_qbit.py # qBittorrent mass importer
├── mt/             # Submodule: M-Team API Wrapper
├── syno/           # Submodule: Synology API Wrapper
└── qbit/           # Submodule: qBittorrent API Wrapper
```

---

## 🛠️ Tool Documentation

### 1. `manage.py` (The Maintainer)
The core automation engine, typically run via cron.

*   **Continuous Maintenance**: Always performs stuck-task cleanup and auto-resumes, even during skip periods.
*   **Unified Stalled Detection**: Monitors `downloaded_pieces` over time. If progress stops for >1 hour (configurable), the task is deleted.
*   **Free Leech Protection**: Bypasses the M-Team "Free" expiry check only if the current time is within a `skip_check_period` in `mt.json`.
*   **Dynamic Seeding Limits**: Enforces seeding limits defined in `syno.json`.

### 2. `cleanup.py` (The Janitor)
Synchronizes your local filesystem with the state of the download client (qBittorrent or Synology).

1.  **Broken Task Removal**: Automatically detects and deletes tasks in an "Error" or "Missing Files" state from the download client (e.g., when you've purged the downloaded files).
2.  **History Update**: Processes `.loaded` markers to update the central `list.json`.
3.  **Torrent Cleanup**: Removes raw `.torrent` files that have already been recorded as successful.
4.  **Orphaned Info**: Removes `.info` metadata files for tasks that no longer exist on the client.

### 3. `search.py` (The Seeker)
Interactive tool to search M-Team and create categorized Synology tasks.

*   **Efficiency**: Resolves category first to perform a targeted check on disk before downloading.
*   **URI Creation**: Uses M-Team download tokens for maximum compatibility.

### 4. `download.py` (The Direct Adder)
Downloads specific torrents by ID and creates categorized Synology tasks. Supports retries and file validation.

### 5. `purge.py` (The Purger)
A powerful manual cleanup tool with advanced filtering.

*   **Targets**: Support for specific download clients (`--client synology`, `--client qbit`) or the local torrent directory (`--torrents`).
*   **Filters**: Support for `--older-than` (days), `--ext` (extension), and `--keyword`.
*   **Safety**: Includes `--trash` (move to `.trash` folder) and mandatory interactive confirmation.
*   **Recursion**: Supports deep cleaning via the `--recursive` flag.

### 6. `finder.py` (The Finder)
A standardized utility to quickly locate specific Task IDs on your NAS using a title keyword.

### 7. `import_local_to_qbit.py` (The Importer)
Mass import local `.torrent` files into qBittorrent, parsing their `.info` metadata to correctly map them to their categorized directories.

---

## ⚙️ Configuration

All configuration is located in the `config/` directory. Example files (`*.json.example`) are provided in the same folder.

### `config/path.json`
Defines the base prefix mappings for local and remote paths across all categories. Categories are automatically appended to these base paths.
```json
{
    "base_paths": {
        "torrents": "/home/cjyeh/pt/torrents",
        "remote": {
            "synology": "home/Download",
            "qbit": "/public/download"
        },
        "local": {
            "synology": "/mnt/ds923/Download",
            "qbit": "/mnt/ds923/public/download"
        }
    }
}
```

### `config/mt.json`
Contains tracker-specific settings and period-based rules.
```json
{
    "key": "your-api-key",
    "rss": "your-rss-url",
    "skip_check_periods": [
        { "start": "20260511 00:00:00", "end": "20260512 23:59:59" }
    ],
    "category_map": { "401": "Movie", "Other": "Watch" }
}
```

### `config/syno.json`
Contains NAS credentials and operational limits.
```json
{
    "ip": "10.0.0.100",
    "port": 5000,
    "account": "nas_user",
    "password": "nas_password",
    "seeding_days_limit": 7,
    "stalled_timeout": 3600
}
```

### `config/qbit.json`
Contains qBittorrent credentials and operational limits.
```json
{
    "ip": "10.0.5.202",
    "port": 8080,
    "api_key": "your-api-key",
    "account": "admin",
    "password": "your-password",
    "seeding_days_limit": 7,
    "stalled_timeout": 3600
}
```

---

## 📦 Requirements

*   Python 3.10+
*   `requests`

Install dependencies:
```bash
pip install requests
```
