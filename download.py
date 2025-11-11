import os
import sys
import json
import logging
import argparse

from mt.api import MT

__description__ = ''
__epilog__ = 'Report bugs to <yehcj.tw@gmail.com>'

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
    parser.add_argument('--id', type=str, nargs='+', required=True, default=[])
    parser.add_argument('--key', type=str, default=None)
    parser.add_argument('--output', type=str, default=None)
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

    with MT(key=args.key, output=args.output) as mt:
        for tid in args.id:
            logging.info(f'tid={tid}')

            if mt.exist(tid=tid):
                logger.info('action=skip')
                logger.info('reason=exist')
                continue

            detail = None
            if args.verbose:
                detail = mt.detail(tid=tid)
                logging.info('status=%s', detail['status']['discount'])
                logging.info('name=%s', detail['name'])

            mt.download(tid=tid, detail=detail)

if __name__ == '__main__':
    main()
