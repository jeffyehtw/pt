'''
Script to clean up orphaned torrent files and metadata
'''
from typing import Dict, Set, List
import os
import sys
import json
import argparse
import glob
import logging

import logging

from syno.api import Syno
from qbit.api import Qbit
from utils import load_config

__description__ = 'Clean up orphaned torrent files and metadata'
__epilog__ = 'Cleanup process completed.'

logger = logging.getLogger()
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Set up stream handler for console output
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

def get_active_tids(ip: str, port: str, account: str, password: str, client_type: str = 'syno', api_key: str = None) -> Set[str]:
    '''Retrieve active task IDs from download client'''
    active_tids = set()
    try:
        client_cls = Qbit if client_type == 'qbit' else Syno
        client_kwargs = {
            'ip': ip,
            'port': port,
            'account': account,
            'password': password
        }
        if client_type == 'qbit':
            client_kwargs['api_key'] = api_key

        with client_cls(**client_kwargs) as client:
            items = client.list_tasks()
            if items is None:
                logger.error('Failed to list tasks from %s', client_type)
                return active_tids

            for item in items:
                # Extract TID from the torrent URI
                uri = item.get('additional', {}).get('detail', {}).get('uri', '')
                tid = os.path.basename(uri).replace('.torrent', '')
                if tid:
                    active_tids.add(tid)
            logger.info('Retrieved %d active tasks from %s', len(active_tids), client_type)

    except Exception as e:
        logger.error('Failed to connect to %s: %s', client_type, e)

    return active_tids

def clean_files(
    search_dirs: List[str],
    active_tids: Set[str],
    history: List[str],
    dry_run: bool = False
) -> Dict[str, int]:
    '''Remove orphaned .torrent and .info files'''
    counts = {'torrent': 0, 'info': 0}

    for directory in search_dirs:
        if not os.path.exists(directory):
            continue
            
        # 1. Clean .torrent files
        torrent_files = glob.glob(
            os.path.join(directory, '**', '*.torrent'),
            recursive=True
        )
        for f in torrent_files:
            tid = os.path.basename(f).replace('.torrent', '')
            # Delete if in history (already seen) OR not in active tasks (finished/deleted)
            if tid in history or tid not in active_tids:
                counts['torrent'] += 1
                if dry_run:
                    logger.info('[Dry Run] Would remove .torrent: %s', f)
                else:
                    try:
                        os.remove(f)
                        logger.info('Removed .torrent: %s', f)
                    except Exception as e:
                        logger.error('Failed to remove %s: %s', f, e)

        # 2. Clean .info files
        info_files = glob.glob(
            os.path.join(directory, '**', '*.info'),
            recursive=True
        )
        for f in info_files:
            tid = os.path.basename(f).replace('.info', '')
            # Info files only exist for active tasks
            if tid not in active_tids:
                counts['info'] += 1
                if dry_run:
                    logger.info('[Dry Run] Would remove orphaned .info: %s', f)
                else:
                    try:
                        os.remove(f)
                        logger.info('Removed orphaned .info: %s', f)
                    except Exception as e:
                        logger.error('Failed to remove %s: %s', f, e)

    return counts

def main() -> None:
    '''Entry point: parse arguments and execute cleanup'''
    parser = argparse.ArgumentParser(
        description=__description__,
        epilog=__epilog__
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        default=False,
        help='Verbose mode'
    )
    parser.add_argument(
        '--client',
        type=str,
        choices=['syno', 'qbit'],
        default='syno',
        help='Download client to use (syno or qbit)'
    )
    args = parser.parse_args(sys.argv[1:])

    # Apply log level
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger.setLevel(log_level)
    stream_handler.setLevel(log_level)

    # Load configuration files
    base = os.path.dirname(os.path.realpath(__file__))
    config_dir = os.path.join(base, 'config')

    syno_config = load_config(os.path.join(config_dir, 'syno.json')) or {}
    qbit_config = load_config(os.path.join(config_dir, 'qbit.json')) or {}
    path_config = load_config(os.path.join(config_dir, 'path.json')) or {}
    history_file = os.path.join(config_dir, 'list.json')

    # Load history
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r') as fp:
                history = json.load(fp)
        except Exception as e:
            logger.error('Failed to load history list: %s', e)

    # Collect all search directories from path.json
    search_dirs = []
    for cat_data in path_config.get('categories', {}).values():
        path = cat_data.get('torrent')
        if path and path not in search_dirs:
            search_dirs.append(path)

    if not search_dirs:
        logger.warning('No search directories found in path.json')
        return

    # Get active tasks from client
    client_config = qbit_config if args.client == 'qbit' else syno_config
    active_tids = get_active_tids(
        ip=client_config.get('ip'),
        port=str(client_config.get('port', '8080' if args.client == 'qbit' else '5000')),
        account=client_config.get('account'),
        password=client_config.get('password'),
        client_type=args.client,
        api_key=client_config.get('api_key')
    )

    if not active_tids:
        logger.warning('No active tasks found or failed to connect to client')
        # We proceed anyway because we can still clean based on history

    logger.info('Starting cleanup across %d directories', len(search_dirs))
    results = clean_files(search_dirs, active_tids, history, args.dry_run)
    
    logger.info(
        'Cleanup finished. Removed %d torrents and %d info files.',
        results['torrent'],
        results['info']
    )

if __name__ == '__main__':
    main()
