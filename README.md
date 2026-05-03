# pt

A comprehensive suite of management tools for **Synology Download Station** and **M-Team** torrent tracker. This project provides automated task management, torrent searching, metadata synchronization, and file maintenance.

## 🚀 Key Features

*   **Synology Task Automation**: Automatically clean up stuck downloads, manage seeding time limits, and resume errored tasks.
*   **M-Team Integration**: Search for torrents based on categories, filter for "Free Leech" status, and download directly.
*   **Automatic Categorization**: Torrents are automatically routed to specific Synology subdirectories (e.g., Movie, TV, Music) based on M-Team metadata.
*   **Free Period Protection**: Skip scheduled checks during specific "free time" periods to optimize processing.
*   **Smart Cleanup**: Automatically removes used `.torrent` files and orphaned metadata to keep your directories tidy.
*   **Submodule-based Architecture**: Core logic is encapsulated in clean, reusable submodules for M-Team (`mt/`) and Synology (`syno/`).

---

## 📂 Project Structure

```text
pt/
├── config/         # Centralized configuration directory
│   ├── settings.json   # Global behavioral settings (seeding, categories, skip periods)
│   ├── mt.json         # M-Team API credentials
│   └── syno.json       # Synology NAS credentials
├── check.py        # Synology task lifecycle manager & "Free Period" monitor
├── clean.py        # Metadata & unused torrent cleanup utility
├── search.py       # M-Team interactive search & categorized download
├── download.py     # Direct M-Team download & categorized task creation
├── delete.py       # General-purpose file/directory cleanup utility
├── mt/             # Submodule: M-Team API Wrapper
└── syno/           # Submodule: Synology API Wrapper
```

---

## 🛠️ Tool Documentation

### 1. `check.py` (Synology Manager)
Manages active tasks on your Synology NAS.

*   **Free Period Check**: Exits immediately if the current time is within a defined "skip period" in `settings.json`.
*   **Stuck Downloads**: Deletes tasks downloading for >1 hour with 0 speed.
*   **Dynamic Seeding Limits**: Removes tasks seeding beyond the limit defined in `settings.json` (default 7 days).
*   **Free Leech Protection**: Monitors "Free Leech" expiry and removes tasks 5 minutes before they become paid.
*   **Auto-Resume**: Automatically resumes tasks in an `error` state.

### 2. `clean.py` (Metadatable & Torrent Sync)
Synchronizes local files with the state of the NAS.

1.  **Used Torrents**: Removes `.torrent` files from the watch directory that have already been recorded in `list.json`.
2.  **Metadata Sync**: Processes `.loaded` markers and updates history.
3.  **Orphaned Info**: Removes `.info` files whose tasks are no longer on the NAS.

### 3. `search.py` (Categorized Search)
Searches M-Team and automatically creates categorized tasks on Synology.

*   **Categorization**: Matches M-Team category to paths defined in `settings.json` (e.g., `home/Download/Movie`).
*   **URI-based Creation**: Uses M-Team download URLs directly to create tasks, ensuring maximum compatibility.

### 4. `download.py` (Direct Download)
Downloads specific torrents by ID and creates categorized Synology tasks.

---

## ⚙️ Configuration

Settings are now centralized in the `config/` directory. The tools prioritize files in `config/` but will fall back to root-level files if they exist.

### `config/settings.json`
```json
{
    "seeding_days_limit": 7,
    "skip_check_periods": [
        {
            "start": "20260503 00:00:00",
            "end": "20260505 23:59:59"
        }
    ],
    "category_paths": {
        "Movie": "home/Download/Movie",
        "TV": "home/Download/TV",
        "Music": "home/Download/Music",
        "Adult": "home/Download/Adult",
        "Other": "home/Download"
    }
}
```

### `config/syno.json`
```json
{
    "ip": "10.0.x.x",
    "port": 5000,
    "account": "your-username",
    "password": "your-password"
}
```

### `config/mt.json`
```json
{
    "key": "your-m-team-api-key",
    "output": "/path/to/local/torrent/backup"
}
```

---

## 📦 Requirements

*   Python 3.6+
*   `requests`
*   `xmltodict`

Install dependencies:
```bash
pip install requests xmltodict
```
