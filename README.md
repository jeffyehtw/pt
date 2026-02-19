# pt

A comprehensive suite of management tools for **Synology Download Station** and **M-Team** torrent tracker. This project provides automated task management, torrent searching, metadata synchronization, and file maintenance.

## 🚀 Key Features

*   **Synology Task Automation**: Automatically clean up stuck downloads, manage seeding time limits, and resume errored tasks.
*   **M-Team Integration**: Search for torrents based on categories (Movie, TV, Music, etc.), filter for "Free Leech" status, and download directly.
*   **Metadata Management**: Keep your torrent information files (`.info`) in sync with active Synology tasks.
*   **Submodule-based Architecture**: Core logic is encapsulated in clean, reusable submodules for M-Team (`mt/`) and Synology (`syno/`).

---

## 📂 Project Structure

```text
pt/
├── check.py        # Synology task lifecycle manager
├── clean.py        # Metadata & history cleanup utility
├── search.py       # M-Team interactive search & download
├── download.py     # Direct M-Team download by Torrent ID
├── delete.py       # General-purpose file/directory cleanup
├── mt/             # Submodule: M-Team API Wrapper
└── syno/           # Submodule: Synology API Wrapper
```

---

## 🛠️ Tool Documentation

### 1. `check.py` (Synology Manager)
Manages active tasks on your Synology NAS.

*   **Stuck Downloads**: Deletes tasks downloading for >1 hour with 0 speed.
*   **Seeding Limits**: Removes tasks seeding for more than **7 days**.
*   **Free Leech Protection**: Monitors "Free Leech" expiry and removes tasks 5 minutes before they become paid.
*   **Auto-Resume**: Automatically resumes tasks in an `error` state.

**Usage:**
```bash
python3 check.py --path /path/to/torrent/info --dry-run
```

### 2. `clean.py` (Metadatable Sync)
Synchronizes local metadata files with the state of the NAS.

1.  Processes `.loaded` markers and updates `list.json` history.
2.  Removes orphaned `.info` files whose tasks are no longer on the NAS.

**Usage:**
```bash
python3 clean.py --output /path/to/metadata
```

### 3. `search.py` (M-Team Search)
Searches M-Team for torrents and downloads them to a monitored directory.

*   **Modes**: `movie`, `tvshow`, `music`, `adult`, `normal`, `rankings`.
*   **Filters**: use `--free` to strictly download Free Leech items.

**Usage:**
```bash
python3 search.py --mode movie --keyword "Interstellar" --free --output ./torrents
```

### 4. `download.py` (Direct Download)
Downloads specific torrents using their unique IDs.

**Usage:**
```bash
python3 download.py --id 123456 789012 --output ./torrents
```

### 5. `delete.py` (File Utility)
A utility for bulk deleting files/folders based on date and keywords.

**Usage:**
```bash
python3 delete.py /path/to/log/dir --before 2024-12-31 --keyword ".log"
```

---

## ⚙️ Configuration

The tools look for JSON configuration files in the root directory.

### `synology.json`
```json
{
    "ip": "192.168.1.10",
    "port": 5000,
    "account": "admin",
    "password": "yourpassword",
    "path": "/volume1/Torrent/info"
}
```

### `mt.json`
```json
{
    "key": "your-m-team-api-key",
    "output": "/volume1/Torrent/watch"
}
```

---

## 📦 Submodules

### [mt](mt/README.md)
Python client for the M-Team API. Handles authentication, searching, metadata retrieval, and downloading.

### [syno](syno/README.md)
Python client for the Synology Download Station API. Handles task listing, resumption, and deletion.

---

## 📝 Requirements

*   Python 3.6+
*   `requests`
*   `xmltodict` (for RSS support in `mt` submodule)

Install dependencies via pip:
```bash
pip install requests xmltodict
```
