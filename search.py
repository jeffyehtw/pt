import os
import sys
import json
import logging
import argparse

from modules.mt import MT

__description__ = ''
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

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

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
    config = None
    if not os.path.exists(file):
        return config
    with open(file, 'r') as fp:
        config = json.load(fp)
    return config

def main():
    global file_handler
    global stream_handler

    parser = argparse.ArgumentParser(
        description=__description__,
        epilog=__epilog__
    )
    parser.add_argument('--key', type=str, default=None)
    parser.add_argument('--output', type=str, default=None)
    parser.add_argument('--mode', choices=__choices__, required=True, help='')
    parser.add_argument('--free', action='store_true', default=False, help='')
    parser.add_argument('--index', type=int, default=1, help='')
    parser.add_argument('--size', type=int, default=25, help='')
    parser.add_argument('--keyword', type=str, default=None, help='')
    parser.add_argument('--verbose', action='store_true', default=False)
    parser.add_argument(
        '--log-level',
        type=str,
        choices={ 'INFO', 'DEBUG' },
        default='INFO',
        help=''
    )
    args = parser.parse_args(sys.argv[1:])

    logger.setLevel(getattr(logging, args.log_level))
    file_handler.setLevel(getattr(logging, args.log_level))
    stream_handler.setLevel(getattr(logging, args.log_level))
    logger.info(__file__)
    logger.info('args=%s', args)

    # load configuration file
    config = load(os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'mt.json'
    ))

    # overwrite the configuration if a parameter is provided
    if args.key is None:
        args.key = config['key']
    if args.output is None:
        args.output = config['output']

    file_handler = logging.FileHandler(os.path.join(args.output, 'app.log'))

    with MT(key=args.key, output=args.output) as mt:
        items = mt.search(
            mode=args.mode,
            free=args.free,
            index=args.index,
            size=args.size,
            keyword=args.keyword
        )

        for item in items:
            tid = item['id']
            logger.info(f'tid={tid}')

            detail = mt.detail(tid=tid)
            # skip uncertain torrent
            if detail is None:
                logger.info('action=skip')
                logger.info('reason=!detail')
                continue

            if args.verbose:
                logger.info('status=%s', detail['status']['discount'])
                logger.info('name=%s', detail['name'])

            # free exception
            if args.free and 'FREE' != detail['status']['discount']:
                logger.info('action=skip')
                logger.info('reason=!free')
                continue

            mt.download(tid=tid)

if __name__ == '__main__':
    main()
