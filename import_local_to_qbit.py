import os
import sys
import json
import logging
import time
import requests

from qbit.api import Qbit
from utils import setup_logger, load_config, resolve_category, get_category_paths

logger = setup_logger(verbose=True)

def import_local_to_qbit():
    base = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(base, 'config')
    torrents_dir = os.path.join(base, 'torrents_local')

    qbit_config = load_config(os.path.join(config_dir, 'qbit.json')) or {}
    mt_config = load_config(os.path.join(config_dir, 'mt.json')) or {}
    path_config = load_config(os.path.join(config_dir, 'path.json')) or {}
    categories_map = mt_config.get('category_map', {})

    ip = qbit_config.get('ip')
    port = str(qbit_config.get('port', '8080'))
    account = qbit_config.get('account')
    password = qbit_config.get('password')
    api_key = qbit_config.get('api_key')

    if not os.path.exists(torrents_dir):
        logger.error(f"Directory {torrents_dir} not found.")
        return

    with Qbit(ip=ip, port=port, account=account, password=password, api_key=api_key) as qbit:
        # Check if auth succeeded by doing a quick test list
        qbit_tasks = qbit.list_tasks()
        if qbit_tasks is None:
            logger.error("Failed to fetch task list. Ensure login is successful.")
            sys.exit(1)
            
        qbit_tids = set()
        for t in qbit_tasks:
            uri = t.get('additional', {}).get('detail', {}).get('uri', '')
            if uri:
                tid = os.path.basename(uri).replace('.torrent', '')
                qbit_tids.add(tid)

        count = 0
        added = 0
        skipped = 0

        torrent_files = [f for f in os.listdir(torrents_dir) if f.endswith('.torrent')]
        
        for f in torrent_files:
            tid = f.replace('.torrent', '')
            count += 1
            
            if tid in qbit_tids:
                logger.debug(f"Task {tid} already in qBittorrent, skipping.")
                skipped += 1
                continue

            torrent_path = os.path.join(torrents_dir, f)
            info_path = os.path.join(torrents_dir, f"{tid}.info")

            detail = None
            if os.path.exists(info_path):
                try:
                    with open(info_path, 'r') as info_file:
                        detail = json.load(info_file)
                except Exception as e:
                    logger.warning(f"Failed to read info file for {tid}: {e}")

            category = resolve_category(detail, categories_map)
            category_paths = get_category_paths(category, path_config)
            nas_dir = category_paths.get('remote', {}).get('qbit')

            logger.info(f"Adding {tid} (category: {category}) to qBittorrent...")

            success = qbit.create_task(
                file=torrent_path,
                destination=nas_dir
            )
            
            if success:
                logger.info(f"Successfully added {tid} to qBittorrent.")
                added += 1
                qbit_tids.add(tid) # update set so we don't add again
                # Mark as loaded
                loaded_path = f"{torrent_path}.loaded"
                with open(loaded_path, 'w') as lf:
                    pass
                time.sleep(0.5)
            else:
                logger.error(f"Failed to add {tid} to qBittorrent")

        logger.info(f"Import complete! Processed {count} torrents, added {added}, skipped {skipped}.")

if __name__ == '__main__':
    import_local_to_qbit()
