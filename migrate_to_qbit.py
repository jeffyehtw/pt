import os
import json
import logging

from syno.api import Syno
from qbit.api import Qbit
from mt.api import MT
from utils import setup_logger, load_config, resolve_category, get_category_paths

logger = setup_logger(verbose=True)

def migrate():
    base = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(base, 'config')

    syno_config = load_config(os.path.join(config_dir, 'syno.json')) or {}
    qbit_config = load_config(os.path.join(config_dir, 'qbit.json')) or {}
    mt_config = load_config(os.path.join(config_dir, 'mt.json')) or {}
    path_config = load_config(os.path.join(config_dir, 'path.json')) or {}
    categories_map = mt_config.get('category_map', {})
    
    syno_kwargs = {k: syno_config.get(k) for k in ['ip', 'port', 'account', 'password']}
    qbit_kwargs = {k: qbit_config.get(k) for k in ['ip', 'port', 'account', 'password', 'api_key'] if k in qbit_config}
    mt_key = mt_config.get('key')
    
    with MT(key=mt_key) as mt, Syno(**syno_kwargs) as syno, Qbit(**qbit_kwargs) as qbit:
        offset = 0
        limit = 100
        all_items = []
        while True:
            items = syno.ds.task.list(offset=offset, limit=limit)
            if not items:
                break
            all_items.extend(items)
            if len(items) < limit:
                break
            offset += limit
            
        if not all_items:
            logger.info("No tasks found in Synology")
            return
            
        qbit_tasks = qbit.ds.task.list()
        qbit_tids = {str(t['id']) for t in qbit_tasks}
            
        tasks_to_pause = []
        
        for item in all_items:
            status = item['status']
            is_incomplete = item['additional']['transfer']['size_downloaded'] < item['size']
            
            if status in ['downloading', 'waiting'] or (status == 'paused' and is_incomplete):
                task_id = item['id']
                uri = item['additional']['detail']['uri']
                tid = os.path.basename(uri).replace('.torrent', '')
                
                if tid in qbit_tids:
                    logger.debug("Task %s already in qBittorrent, skipping.", tid)
                    continue
                    
                logger.info("Processing task %s (tid: %s) - status: %s", task_id, tid, status)
                
                detail = mt.detail(tid=tid)
                if detail is None:
                    logger.warning("Could not fetch detail for %s", tid)
                    continue
                    
                category = resolve_category(detail, categories_map)
                category_paths = get_category_paths(category, path_config)
                local_dir = category_paths.get('torrents')
                nas_dir = category_paths.get('remote', {}).get('synology')
                
                torrent_path, _ = mt.download(
                    tid=tid,
                    local_dir=local_dir,
                    detail=detail
                )
                
                if torrent_path and os.path.exists(torrent_path):
                    success = qbit.ds.task.create(
                        file=torrent_path,
                        destination=nas_dir
                    )
                    if success:
                        logger.info("Successfully migrated %s to qBittorrent.", tid)
                        tasks_to_pause.append(task_id)
                    else:
                        logger.error("Failed to add %s to qBittorrent", tid)
                else:
                    logger.error("Failed to download torrent file for %s", tid)
                    
        if tasks_to_pause:
            # Synology pause method accepts list of task IDs but wait:
            # wait, syno/task.py pause method expects list of strings representing the IDs
            tasks_ids_str = [str(t) for t in tasks_to_pause]
            logger.info("Pausing %d tasks on Synology: %s", len(tasks_ids_str), tasks_ids_str)
            syno.ds.task.pause(tasks=tasks_ids_str)
            logger.info("Paused successfully.")
        else:
            logger.info("No downloading/waiting tasks found to migrate.")

if __name__ == '__main__':
    migrate()
