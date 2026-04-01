'''
Script to check and manage Synology Download Station tasks.
'''
import os
import sys
import argparse
import json

from datetime import datetime, timedelta

from syno.api import Syno
from utils import setup_logger, load_config, merge_args_with_config

__description__ = 'Synology Download Station Task Manager'
__epilog__ = 'Report bugs to <yehcj.tw@gmail.com>'

logger = None

def clean(path: str, tid: str) -> None:
    '''Clean up local torrent information files'''
    logger.debug('path=%s, tid=%s', path, tid)

    info = os.path.join(path, f'{tid}.info')
    if os.path.exists(info):
        os.remove(info)

    loaded = os.path.join(path, f'{tid}.torrent.loaded')
    if os.path.exists(loaded):
        os.remove(loaded)

def check_free_status(task: str, path: str, tid: str) -> str:
    '''
    Check if a task is free to download.
    
    Returns:
        'free': Task is in free download period
        'ending': Free period ending soon (< 5 min), should pause
        'expired': No free period or no info, should delete
    '''
    logger.debug('task=%s, path=%s, tid=%s', task, path, tid)

    file = os.path.join(path, f'{tid}.info')
    if not os.path.exists(file):
        logger.debug('action=expired, reason=!info')
        return 'expired'

    info = None
    with open(file, 'r') as fp:
        info = json.load(fp)

    if info is None:
        logger.debug('action=expired, reason=!info')
        return 'expired'

    if info['status']['discountEndTime'] is None:
        logger.debug('action=expired, reason=!endtime')
        return 'expired'

    end = datetime.strptime(
        info['status']['discountEndTime'],
        '%Y-%m-%d %H:%M:%S'
    )
    now = datetime.now()

    if now > end:
        # Free period has already ended
        logger.debug(
            'end=%s, action=expired, reason=free_over',
            info['status']['discountEndTime']
        )
        return 'expired'
    elif end - now < timedelta(minutes=5):
        # Free period ending soon
        logger.debug(
            'end=%s, action=ending, reason=free_ending',
            info['status']['discountEndTime']
        )
        return 'ending'
    else:
        logger.debug('action=free, reason=free')
        return 'free'

def main():
    global logger

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

    # Setup logger
    logger = setup_logger(
        log_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'check.log'),
        verbose=args.verbose
    )

    # load configuration file
    config = load_config(os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'synology.json'
    ))

    # Merge configuration with CLI arguments
    args = merge_args_with_config(args, config)

    delete_tasks = []
    pause_tasks = []
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

                free_status = check_free_status(task=task, path=args.path, tid=tid)
                if free_status == 'ending':
                    pause_tasks.append({'id': task, 'tid': tid, 'title': title})
                elif free_status == 'expired':
                    delete_tasks.append({'id': task, 'tid': tid, 'title': title})

            if status == 'waiting':
                # completed, but reverted to waiting due to error
                if detail['completed_time'] > 0:
                    logger.debug('action=pass, reason=completed')
                    continue

                free_status = check_free_status(task=task, path=args.path, tid=tid)
                if free_status == 'ending':
                    pause_tasks.append({'id': task, 'tid': tid, 'title': title})
                elif free_status == 'expired':
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

            if len(pause_tasks) > 0:
                logger.info('Tasks to pause:')
                for t in pause_tasks:
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

            if len(pause_tasks) > 0:
                syno.ds.task.pause(tasks=[t['id'] for t in pause_tasks])
                # NOTE: We do NOT clean up .info files for paused tasks.
                # When the user resumes manually, check.py will detect
                # the expired free period and handle appropriately.

            if len(resume_tasks) > 0:
                syno.ds.task.resume(tasks=[t['id'] for t in resume_tasks])

if __name__ == '__main__':
    main()