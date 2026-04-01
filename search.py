'''
Script to search and download torrents from M-Team
'''
import os
import sys
import json
import argparse

from mt.api import MT
from utils import setup_logger, load_config, merge_args_with_config

__description__ = 'Search and download torrents from M-Team'
__epilog__ = 'Report bugs to <yehcj.tw@gmail.com>'
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

logger = None

def main():
    '''Entry point: parse arguments'''
    global logger

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

    with MT(key=args.key, output=args.output) as mt:
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

            # Check for free discount if --free is specified
            if args.free and 'FREE' != detail['status']['discount']:
                logger.info('action=skip, reason=!free')
                continue

            mt.download(tid=tid, detail=detail)

if __name__ == '__main__':
    main()
