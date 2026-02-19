'''
Script to check and manage Synology Download Station tasks.
'''
import os
import sys
import logging
import argparse
import json

from datetime import datetime, timedelta

from syno.api import Syno

__description__ = 'Synology Download Station Task Manager'
__epilog__ = 'Report bugs to <yehcj.tw@gmail.com>'

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

file_handler = logging.FileHandler(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'check.log'
))
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

def load(file: str) -> dict:
    '''Load configuration from JSON file'''
    logger.debug('file=%s', file)

    if not os.path.exists(file):
        return None

    config = {}
    with open(file, 'r') as fp:
        config = json.load(fp)

    return config

def clean(path: str, tid: str) -> None:
    '''Clean up local torrent information files'''
    logger.debug('path=%s, tid=%s', path, tid)

    info = os.path.join(path, f'{tid}.info')
    if os.path.exists(info):
        os.remove(info)

    loaded = os.path.join(path, f'{tid}.torrent.loaded')
    if os.path.exists(loaded):
        os.remove(loaded)

def free(task: str, path: str, tid: str) -> bool:
    '''Check if a task is free'''
    logger.debug('task=%s, path=%s, tid=%s', task, path, tid)

    file = os.path.join(path, f'{tid}.info')
    if not os.path.exists(file):
        logger.debug('action=pass, reason=!info')
        return True

    info = None
    with open(file, 'r') as fp:
        info = json.load(fp)

    if info is None:
        logger.debug('action=delete, reason=!info')
        return False

    if info['status']['discountEndTime'] is None:
        logger.debug('action=delete, reason=!endtime')
        return False

    end = datetime.strptime(
        info['status']['discountEndTime'],
        '%Y-%m-%d %H:%M:%S'
    )
    now = datetime.now()

    if end - now < timedelta(minutes=5):
        logger.debug(
            'end=%s, action=delete, reason=!free',
            info['status']['discountEndTime']
        )
        clean(path=path, tid=tid)
        return False
    else:
        logger.debug('action=pass, reason=free')

    return True

def main():
    parser = argparse.ArgumentParser(
        description=__description__,
        epilog=__epilog__
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
        default=5000,
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
    parser.add_argument(
        '--path',
        type=str,
        default=None,
        help='Directory containing the torrent information files'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose mode'
    )
    args = parser.parse_args(sys.argv[1:])

    # load configuration file
    config = load(os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'synology.json'
    ))

    # overwrite the configuration if a parameter is provided
    for key, value in vars(args).items():
        if value is None and key in config:
            setattr(args, key, config[key])

    delete_tasks = []
    resume_tasks = []

    # Current time
    now_dt = datetime.now()
    now_ts = now_dt.timestamp()

    with Syno(
        ip=args.ip,
        port=args.port,
        account=args.account,
        password=args.password
    ) as syno:
        logger.debug('action=login')

        items = syno.ds.task.list()
        logger.debug('action=list, count=%d', len(items))

        for item in items:
            tid = item['additional']['detail']['uri'].replace('.torrent', '')
            task = item['id']
            status = item['status']
            title = item['title']
            detail = item['additional']['detail']
            transfer = item['additional']['transfer']

            logger.debug('tid=%s, task=%s, status=%s', tid, task, status)

            if status == 'downloading':
                # Check for stuck downloads
                started_time = detail['started_time']
                if started_time <= 0:
                     started_time = detail['create_time']

                if transfer['downloaded_pieces'] == 0 and (now_ts - started_time) > 3600:
                    logger.debug(
                        'action=delete, reason=stuck, duration=%ds',
                        now_ts - started_time
                    )
                    delete_tasks.append({'id': task, 'tid': tid, 'title': title})

                if not free(task=task, path=args.path, tid=tid):
                    delete_tasks.append({'id': task, 'tid': tid, 'title': title})

            if status == 'waiting':
                # completed, but reverted to waiting due to error
                if detail['completed_time'] > 0:
                    logger.debug('action=pass, reason=completed')
                    continue

                if not free(task=task, path=args.path, tid=tid):
                    delete_tasks.append({'id': task, 'tid': tid, 'title': title})

            if status == 'error':
                resume_tasks.append({'id': task, 'tid': tid, 'title': title})

            if status == 'seeding':
                # Check for seeding over 7 days
                completed_time = detail['completed_time']
                if completed_time > 0 and (now_ts - completed_time) > (7 * 86400):
                    logger.debug(
                        'action=delete, reason=seeding_over_7_days, duration=%ds',
                        now_ts - completed_time
                    )
                    delete_tasks.append({'id': task, 'tid': tid, 'title': title})

        if args.verbose:
            if len(delete_tasks) > 0:
                logger.info('Tasks to delete:')
                for t in delete_tasks:
                    logger.info('  %s: %s', t['id'], t['title'])

            if len(resume_tasks) > 0:
                logger.info('Tasks to resume:')
                for t in resume_tasks:
                    logger.info('  %s: %s', t['id'], t['title'])

        if not args.dry_run:
            if len(delete_tasks) > 0:
                syno.ds.task.delete(tasks=[t['id'] for t in delete_tasks])
                # Clean up local files for deleted tasks
                for t in delete_tasks:
                    clean(path=args.path, tid=t['tid'])

            if len(resume_tasks) > 0:
                syno.ds.task.resume(tasks=[t['id'] for t in resume_tasks])

if __name__ == '__main__':
    main()