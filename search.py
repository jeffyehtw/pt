'''
Script to search and download torrents from M-Team
'''
import os
import sys
import json
import logging
import argparse

from mt.api import MT

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

def load(file: str) -> dict:
    '''Load configuration from a JSON file'''
    if not os.path.exists(file):
        return None
    with open(file, 'r') as fp:
        return json.load(fp)


def main():
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
    args = parser.parse_args(sys.argv[1:])

    # Apply log level to all handlers
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger.setLevel(log_level)
    file_handler.setLevel(log_level)
    stream_handler.setLevel(log_level)

    logger.info('args=%s', args)

    # Load configuration from mt.json
    config = load(os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'mt.json'
    ))

    # Fall back to config values if not provided on the command line
    if args.key is None and config:
        args.key = config.get('key')
    if args.output is None and config:
        args.output = config.get('output')

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
