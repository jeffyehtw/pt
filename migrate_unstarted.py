import os
import re
from utils import load_config
from syno.api import Syno
from qbit.api import Qbit
from mt.api import MT
from utils import setup_logger, resolve_category, get_category_paths

logger = setup_logger(verbose=True)

def migrate_unstarted():
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')
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
            
        qbit_tasks = qbit.ds.task.list()
        qbit_tids = set()
        if qbit_tasks:
            for t in qbit_tasks:
                uri = t.get('additional', {}).get('detail', {}).get('uri', '')
                if uri:
                    tid = os.path.basename(uri).replace('.torrent', '')
                    qbit_tids.add(tid)
        
        tasks_to_delete = []
        
        for item in all_items:
            status = item['status']
            title = item['title']
            size = item['size']
            
            uri = item.get('additional', {}).get('detail', {}).get('uri', '')
            tid = os.path.basename(uri).replace('.torrent', '')
            
            match = re.search(r'(12\d{5})', title)
            if match:
                tid = match.group(1)
            elif not re.match(r'12\d{5}', tid):
                continue
                
            if status == 'paused' and size == 0:
                if tid in qbit_tids:
                    logger.info("Task %s already in qBittorrent, skipping migration but marking for deletion.", tid)
                    tasks_to_delete.append(item['id'])
                    continue
                    
                logger.info("Processing unstarted task %s (tid: %s)", item['id'], tid)
                
                detail = mt.detail(tid=tid)
                if detail is None:
                    logger.warning("Could not fetch detail for %s", tid)
                    continue
                    
                category = resolve_category(detail, categories_map)
                category_paths = get_category_paths(category, path_config)
                local_dir = category_paths.get('torrents')
                nas_dir = category_paths.get('remote', {}).get('qbit')
                
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
                        tasks_to_delete.append(item['id'])
                    else:
                        logger.error("Failed to add %s to qBittorrent", tid)
                else:
                    logger.error("Failed to download torrent file for %s", tid)
                    
        if tasks_to_delete:
            tasks_ids_str = [str(t) for t in tasks_to_delete]
            logger.info("Deleting %d migrated unstarted tasks from Synology...", len(tasks_ids_str))
            syno.ds.task.delete(tasks=tasks_ids_str, force_complete=False)
            logger.info("Deleted successfully.")
        else:
            logger.info("No unstarted tasks found to migrate.")

if __name__ == '__main__':
    migrate_unstarted()
