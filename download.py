'''
Script to download specific torrents from M-Team by ID
'''
import os
import sys
import json
import argparse

from mt.api import MT
from utils import setup_logger, load_config, merge_args_with_config

__description__ = 'Download M-Team torrents by torrent ID'
__epilog__ = 'Report bugs to <yehcj.tw@gmail.com>'

logger = None

def main():
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
    args = parser.parse_args(sys.argv[1:])

    # Setup logger
    logger = setup_logger(
        log_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.log'),
        verbose=args.verbose
    )

    logger.info('args=%s', args)

    # Load configuration from mt.json
    config = load_config(os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'mt.json'
    ))

    # Merge configuration with CLI arguments
    args = merge_args_with_config(args, config)

    # Load Synology configuration
    synology_config = load(os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'config', 'synology.json'
    ))
    if synology_config is None:
        synology_config = load(os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'synology.json'
        ))

    with MT(key=args.key, output=args.output) as mt:
        for tid in args.id:
            logger.info('tid=%s', tid)

            # Skip if already downloaded (unless --force is set)
            if not args.force and mt.exist(tid=tid):
                logger.info('action=skip, reason=exist')
                continue

            # Fetch detailed metadata
            detail = mt.detail(tid=tid)
            if detail is None:
                logger.info('action=skip, reason=!detail')
                continue

            if args.verbose:
                logger.info(
                    'name=%s, status=%s',
                    detail['name'],
                    detail['status']['discount']
                )

            torrent_path, torrent_url = mt.download(tid=tid, detail=detail)

            # Create Synology task if configured
            if torrent_url and synology_config:
                destination = mt.download.resolve_destination(detail)
                with Syno(
                    ip=synology_config['ip'],
                    port=synology_config['port'],
                    account=synology_config['account'],
                    password=synology_config['password']
                ) as syno:
                    success = syno.ds.task.create(uri=torrent_url, destination=destination)
                    if success:
                        logger.info('action=syno_create, tid=%s, destination=%s', tid, destination)
                    else:
                        logger.error('action=syno_create_fail, tid=%s', tid)

if __name__ == '__main__':
    main()
