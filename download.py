'''
Script to download specific torrents from M-Team by ID
'''
import os
import sys
import json
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

__description__ = 'Download M-Team torrents by torrent ID'
__epilog__ = 'Download process completed.'

logger = None

def main() -> None:
    '''Entry point: parse arguments'''
    global logger

    parser = argparse.ArgumentParser(
        description=__description__,
        epilog=__epilog__
    )
    parser.add_argument(
        '--id',
        type=str,
        nargs='+',
        required=True,
        help='One or more torrent IDs to download'
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
        '--keep-alive',
        action='store_true',
        default=False,
        help='Keep the torrent alive in the client by bypassing manage checks'
    )
    parser.add_argument(
        '--client',
        type=str,
        choices=['syno', 'qbit'],
        default='qbit',
        help='Download client to use (syno or qbit)'
    )
    args = parser.parse_args(sys.argv[1:])

    # Setup logger
    logger = setup_logger(
        log_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.log'),
        verbose=args.verbose
    )

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

        def process_tids(client = None) -> None:
            for tid in args.id:
                logger.info('tid=%s', tid)

                # Resolve category and paths early to enable targeted existence check
                # Fetch detailed metadata for category resolution
                detail = mt.detail(tid=tid)
                if detail is None:
                    logger.info('action=skip, reason=!detail')
                    continue
                
                category = resolve_category(detail, categories_map)
                category_paths = get_category_paths(category, path_config)
                local_dir = category_paths.get('torrents')
                if args.client == 'qbit':
                    nas_dir = category_paths.get('remote', {}).get('qbit')
                else:
                    nas_dir = category_paths.get('remote', {}).get('synology')

                # Skip if already downloaded (unless --force is set)
                # Check history list and targeted disk location
                search_dir = args.output or local_dir
                if not args.force and mt.exist(
                    tid=tid,
                    search_dir=search_dir,
                    history=history,
                    check_loaded=(client is not None)
                ):
                    logger.info('action=skip, reason=exist')
                    continue

                if args.keep_alive:
                    detail['keep_alive'] = True

                if args.verbose:
                    logger.info(
                        'name=%s, status=%s',
                        detail['name'],
                        detail['status']['discount']
                    )

                # If args.output is set, we use it as the base
                # for local_dir if relative
                if args.output and not os.path.isabs(local_dir):
                    local_dir = os.path.join(args.output, local_dir)

                # Attempt to download torrent file locally
                torrent_path = None
                max_retries = 3
                for attempt in range(max_retries):
                    torrent_path, torrent_url = mt.download(
                        tid=tid,
                        local_dir=local_dir,
                        detail=detail
                    )

                    if torrent_path and os.path.exists(torrent_path):
                        # Verify it's a valid torrent file (not HTML)
                        with open(torrent_path, 'rb') as f:
                            start = f.read(100)
                            if b'd8:announce' in start or \
                               b'd13:announce-list' in start:
                                break
                            else:
                                logger.warning(
                                    'action=download_retry, tid=%s, '
                                    'reason=invalid_file_content',
                                    tid
                                )
                                os.remove(torrent_path)
                                torrent_path = None

                    if attempt < max_retries - 1:
                        import time
                        time.sleep(5)

                if not torrent_path:
                    logger.error(
                        'action=skip, tid=%s, '
                        'reason=download_fail_after_retries',
                        tid
                    )
                    continue

                # Create task in client if configured
                if client:
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
                            'action=client_create, tid=%s, method=file, '
                            'destination=%s',
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
                process_tids(client)
        else:
            process_tids()

    # Save updated history
    if history:
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=4)

if __name__ == '__main__':
    main()
