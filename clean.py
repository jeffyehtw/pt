import os
import sys
import json
import shutil
import argparse
import glob
import logging

__description__ = ''
__epilog__ = 'Report bugs to <yehcj.tw@gmail.com>'

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(formatter)

logger.addHandler(stream_handler)

def load(file: str) -> dict:
    config = None
    if not os.path.exists(file):
        return config
    with open(file, 'r') as fp:
        config = json.load(fp)
    return config

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__description__,
        epilog=__epilog__
    )
    parser.add_argument('--output', type=str, default=None)
    args = parser.parse_args(sys.argv[1:])

    # load configuration file
    config = load(os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'mt.json'
    ))

    # overwrite the configuration if a parameter is provided
    if args.output is None:
        args.output = config['output']

    shutil.copy(
        os.path.join(args.output, 'list.json'),
        os.path.join(args.output, 'list.json.bk')
    )
    with open(os.path.join(args.output, 'list.json'), 'r') as fp:
        history = json.load(fp)

    torrents = glob.glob(os.path.join(args.output, '*.loaded'))
    for torrent in torrents:
        tid = os.path.basename(torrent).replace('.torrent.loaded', '')
        logger.debug('tid=%s', tid)
        if tid in history:
            logger.debug('action=pass')
        else:
            logger.debug('action=add')
            history.append(tid)
        os.remove(torrent)

    with open(os.path.join(args.output, 'list.json'), 'w') as fp:
        json.dump(history, fp, indent=4)
