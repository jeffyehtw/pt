# mt - M-Team Torrent Tracker API Wrapper

A Python client for the [M-Team](https://m-team.cc) torrent tracker API.

## Structure

```
mt/
├── api.py       # MT entry point — aggregates all sub-classes
├── base.py      # Shared HTTP helpers (headers, post)
├── latest.py    # Latest — fetch RSS feed items
├── download.py  # Download — download torrent files
├── exist.py     # Exist — check if already downloaded
├── detail.py    # Detail — fetch torrent metadata
└── search.py    # Search — search for torrents
```

## Classes & Functions

### `MT` (api.py)

The main API client. Uses a context manager to automatically load and save the torrent
history list (`list.json`) on entry and exit.

| Method | Description |
|---|---|
| `latest()` | Fetch the latest items from the configured RSS feed |
| `search(mode, free, index, size, keyword)` | Search for torrents |
| `detail(tid)` | Get detailed metadata for a torrent by ID |
| `download(tid, detail)` | Download a torrent file and optionally save its metadata |
| `exist(tid)` | Check if a torrent has already been downloaded |


## Usage

### Search and Download Free Torrents

```python
from mt.api import MT

with MT(key='your-api-key', output='/path/to/output') as mt:
    items = mt.search(mode='movie', free=True, index=1, size=25)

    for item in items:
        tid = item['id']

        if mt.exist(tid=tid):
            continue  # already downloaded

        detail = mt.detail(tid=tid)
        if detail is None:
            continue

        mt.download(tid=tid, detail=detail)
```

### Fetch RSS Feed

```python
from mt.api import MT

mt = MT(rss='https://your-rss-url', key='your-api-key')
items = mt.latest()
for item in items:
    print(item['title'], item['link'])
```


## Configuration

Credentials and paths are typically stored in `mt.json` and loaded by the calling script:

```json
{
    "key": "your-api-key",
    "output": "/path/to/torrent/output"
}
```

## Output Files

For each downloaded torrent with ID `{tid}`:

| File | Description |
|---|---|
| `{tid}.torrent` | The torrent file, ready to be loaded by a client |
| `{tid}.info` | JSON metadata from the M-Team API (discount, name, etc.) |
| `{tid}.torrent.loaded` | Created by the Synology client after loading the torrent |

## Search Modes

| Mode | Description |
|---|---|
| `normal` | General torrents |
| `adult` | Adult content |
| `movie` | Movies |
| `music` | Music |
| `tvshow` | TV shows |
| `waterfall` | Waterfall mode |
| `rss` | RSS feed |
| `rankings` | Rankings |

## Dependencies

- `requests` - HTTP requests
- `xmltodict` - RSS XML parsing
