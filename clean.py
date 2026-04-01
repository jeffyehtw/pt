'''
Script to clean up orphaned torrent metadata files and update the history list
'''
import os
import sys
import json
import shutil
import argparse
import glob

from syno.api import Syno
from utils import setup_logger, load_config, merge_args_with_config

__description__ = 'Clean up orphaned torrent metadata files'
__epilog__ = 'Report bugs to <yehcj.tw@gmail.com>'

logger = None

def get_active_tids(ip: str, port: str, account: str, password: str) -> set:
    '''Retrieve active task IDs from Synology NAS'''
    active_tids = set()
    try:
        with Syno(
            ip=ip,
            port=port,
            account=account,
            password=password
        ) as syno:
            items = syno.ds.task.list()
            for item in items:
                # Extract TID from the torrent URI
                uri = item.get('additional', {}).get('detail', {}).get('uri', '')
                tid = uri.replace('.torrent', '')
                if tid:
                    active_tids.add(tid)
            logger.info('Retrieved %d active tasks from Synology', len(active_tids))

    except Exception as e:
        logger.error('Failed to connect to Synology: %s', e)
        logger.warning('Continuing without Synology task list')

    return active_tids

def process_loaded_files(args):
    '''Update list.json with .loaded files and remove them'''
    list_json_path = os.path.join(args.output, 'list.json')
    list_json_bk_path = os.path.join(args.output, 'list.json.bk')

    # Backup list.json before modification
    if not args.dry_run and os.path.exists(list_json_path):
        shutil.copy(list_json_path, list_json_bk_path)

    history = []
    if os.path.exists(list_json_path):
        try:
            with open(list_json_path, 'r') as fp:
                history = json.load(fp)
        except Exception as e:
            logger.error('Failed to load history list: %s', e)

    # Find and process all .loaded files
    torrents = glob.glob(os.path.join(args.output, '*.loaded'))
    added_count = 0
    removed_count = 0

    for torrent in torrents:
        tid = os.path.basename(torrent).replace('.torrent.loaded', '')
        if tid not in history:
            logger.info('Adding new TID to history: %s', tid)
            history.append(tid)
            added_count += 1

        if args.dry_run:
            logger.info('[Dry Run] Would remove: %s', torrent)
            removed_count += 1
        else:
            try:
                os.remove(torrent)
                removed_count += 1
            except Exception as e:
                logger.error('Failed to remove %s: %s', torrent, e)

    # Save updated history
    if not args.dry_run and added_count > 0:
        with open(list_json_path, 'w') as fp:
            json.dump(history, fp, indent=4)
        logger.info('Updated history list with %d new items', added_count)

    return removed_count

def clean_orphaned_info(args, active_tids):
    '''Remove .info files not present in active_tids'''
    info_files = glob.glob(os.path.join(args.output, '*.info'))
    orphaned_count = 0

    for info_file in info_files:
        tid = os.path.basename(info_file).replace('.info', '')

        if tid not in active_tids:
            orphaned_count += 1
            if args.dry_run:
                logger.info('[Dry Run] Would remove orphaned file: %s', info_file)
            else:
                try:
                    os.remove(info_file)
                    logger.info('Removed orphaned file: %s', info_file)
                except Exception as e:
                    logger.error('Failed to remove %s: %s', info_file, e)

    logger.info('Processed %d orphaned .info files', orphaned_count)

    return orphaned_count

def main():
    '''Entry point: parse arguments and execute cleanup'''
    global logger

    parser = argparse.ArgumentParser(
        description=__description__,
        epilog=__epilog__
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        required=True,
        help='Output directory path'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode (do not remove files)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        default=False,
        help='Verbose mode (set log level to DEBUG)'
    )
    parser.add_argument(
        '--ip',
        type=str,
        default=None,
        help='Synology NAS IP address'
    )
    parser.add_argument(
        '--port',
        type=str,
        default=None,
        help='Synology NAS port'
    )
    parser.add_argument(
        '--account',
        type=str,
        default=None,
        help='Synology NAS user account'
    )
    parser.add_argument(
        '--password',
        type=str,
        default=None,
        help='Synology NAS user password'
    )
    args = parser.parse_args(sys.argv[1:])

    # Setup logger
    logger = setup_logger(
        log_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.log'),
        verbose=args.verbose
    )

    # Load configuration files
    base = os.path.dirname(os.path.realpath(__file__))
    mt_config = load_config(os.path.join(base, 'mt.json'))
    syno_config = load_config(os.path.join(base, 'synology.json'))

    # Merge configurations
    args = merge_args_with_config(args, mt_config)
    args = merge_args_with_config(args, syno_config)

    logger.info('Starting cleanup in %s', args.output)

    # Step 1: Process .loaded files and update history
    process_loaded_files(args)

    # Step 2: Get active tasks from Synology
    active_tids = get_active_tids(
        ip=args.ip,
        port=args.port,
        account=args.account,
        password=args.password
    )

    # Step 3: Clean up orphaned .info files
    if active_tids:
        clean_orphaned_info(args, active_tids)
    else:
        logger.warning('Skipping orphaned .info cleanup as no active tasks were found')

if __name__ == '__main__':
    main()
