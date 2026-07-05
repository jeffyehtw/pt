'''
Script to search and download torrents from M-Team
'''
import os
import sys
import json
import logging
import argparse

from mt.api import MT
from syno.api import Syno
from qbit.api import Qbit
from utils import (
    setup_logger,
    load_config,
    merge_args_with_config,
    resolve_category,
    get_category_paths
)

__description__ = 'Search and download torrents from M-Team'
__epilog__ = 'Search and acquisition completed.'
__choices__ = {
    'normal',
    'adult',
    'movie',
    'music',
    'tvshow',
    'waterfall',
    'rss',
    'rankings'
}

logger = logging.getLogger()
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

file_handler = logging.FileHandler(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'app.log'
))
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

def main() -> None:
    '''Entry point: parse arguments'''
    global file_handler
    global stream_handler

    parser = argparse.ArgumentParser(
        description=__description__,
        epilog=__epilog__
    )
    parser.add_argument(
        '--key',
        type=str,
        default=None,
        help='M-Team API key'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output directory'
    )
    parser.add_argument(
        '--mode',
        choices=__choices__,
        required=True,
        help='Search mode'
    )
    parser.add_argument(
        '--free',
        action='store_true',
        default=False,
        help='Search for free torrents only'
    )
    parser.add_argument(
        '--index',
        type=int,
        default=1,
        help='Page number'
    )
    parser.add_argument(
        '--size',
        type=int,
        default=25,
        help='Page size'
    )
    parser.add_argument(
        '--keyword',
        type=str,
        default=None,
        help='Search keyword'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        default=False,
        help='Verbose mode (set log level to DEBUG)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        default=False,
        help='Download even if the torrent already exists'
    )
    parser.add_argument(
        '--client',
        type=str,
        choices=['syno', 'qbit'],
        default='syno',
        help='Download client to use (syno or qbit)'
    )
    args = parser.parse_args(sys.argv[1:])

    # Apply log level to all handlers
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger.setLevel(log_level)
    file_handler.setLevel(log_level)
    stream_handler.setLevel(log_level)

    logger.info('args=%s', args)

    # Load configurations
    base = os.path.dirname(os.path.realpath(__file__))
    config_dir = os.path.join(base, 'config')

    mt_config = load_config(os.path.join(config_dir, 'mt.json')) or {}
    syno_config = load_config(os.path.join(config_dir, 'syno.json')) or {}
    qbit_config = load_config(os.path.join(config_dir, 'qbit.json')) or {}
    path_config = load_config(os.path.join(config_dir, 'path.json')) or {}
    categories_map = mt_config.get('category_map', {})

    # Merge configuration with CLI arguments
    args = merge_args_with_config(args, mt_config)

    # Load history list
    history_file = os.path.join(config_dir, 'list.json')
    history = []
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            history = json.load(f)

    with MT(key=args.key) as mt:
        # Initialize torrent client if configured
        torrent_client = None
        if args.client == 'syno' and syno_config:
            torrent_client = Syno(
                ip=syno_config['ip'],
                port=str(syno_config['port']),
                account=syno_config['account'],
                password=syno_config['password']
            )
        elif args.client == 'qbit' and qbit_config:
            torrent_client = Qbit(
                ip=qbit_config['ip'],
                port=str(qbit_config['port']),
                api_key=qbit_config.get('api_key'),
                account=qbit_config.get('account'),
                password=qbit_config.get('password')
            )

        def process_items(client = None) -> None:
            items = mt.search(
                mode=args.mode,
                free=args.free,
                index=args.index,
                size=args.size,
                keyword=args.keyword
            )
            if items is None:
                return

            for item in items:
                tid = item['id']
                logger.info('tid=%s', tid)

                # Fetch detailed metadata early for path resolution
                detail = mt.detail(tid=tid)
                if detail is None:
                    logger.info('action=skip, reason=!detail')
                    continue

                # Resolve category and paths
                category = resolve_category(detail, categories_map)
                category_paths = get_category_paths(category, path_config)
                local_dir = category_paths.get('torrent')
                if args.client == 'qbit':
                    nas_dir = category_paths.get('qbit_download')
                else:
                    nas_dir = category_paths.get('remote_download')

                # Skip if already downloaded (unless --force is set)
                # Use targeted local path for efficiency
                search_dir = args.output or local_dir
                if not args.force and mt.exist(
                    tid=tid,
                    search_dir=search_dir,
                    history=history
                ):
                    logger.info('action=skip, reason=exist')
                    continue

                if args.verbose:
                    logger.info(
                        'name=%s, status=%s',
                        detail['name'],
                        detail['status']['discount']
                    )

                # Check for free discount if --free is specified
                if args.free and 'FREE' != detail['status']['discount']:
                    logger.info('action=skip, reason=!free')
                    continue

                # If args.output is set, we use it as the base
                # for local_dir if relative
                if args.output and not os.path.isabs(local_dir):
                    local_dir = os.path.join(args.output, local_dir)

                torrent_path, torrent_url = mt.download(
                    tid=tid,
                    local_dir=local_dir,
                    detail=detail
                )

                # Create task in client if configured
                if torrent_path and client:
                    # Exclusively use FILE method for reliability
                    # and destination control
                    success = client.create_task(
                        file=torrent_path,
                        destination=nas_dir
                    )

                    # Fallback to default destination if the specific one fails
                    if not success and nas_dir:
                        logger.warning(
                            'action=client_create_retry, tid=%s, '
                            'reason=fail_with_destination, destination=%s',
                            tid,
                            nas_dir
                        )
                        success = client.create_task(
                            file=torrent_path,
                            destination=None
                        )

                    if success:
                        logger.info(
                            'action=client_create, tid=%s, destination=%s',
                            tid,
                            nas_dir if success else 'default'
                        )
                        # Create .loaded file to mark as successfully
                        # added to Synology
                        loaded_path = f'{torrent_path}.loaded'
                        with open(loaded_path, 'w') as f:
                            f.write('')
                            
                        # Add to history
                        if tid not in history:
                            history.append(tid)
                    else:
                        logger.error('action=client_create_fail, tid=%s', tid)

        if torrent_client:
            with torrent_client as client:
                process_items(client)
        else:
            process_items()

    # Save updated history
    if history:
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=4)

if __name__ == '__main__':
    main()
