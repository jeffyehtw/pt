'''
Script to check and manage Synology Download Station tasks.
'''
from typing import Dict, List, Tuple, Set, Optional
import os
import sys
import logging
import argparse
import json
import glob

from datetime import datetime, timedelta

from syno.api import Syno
from utils import load_config

__description__ = 'Synology Download Station Task Manager'
__epilog__ = 'Task management completed.'

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

file_handler = logging.FileHandler(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'manage.log'
))
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

def clean(search_dirs: List[str], tid: str) -> None:
    '''Clean up local torrent information files'''
    logger.debug('tid=%s', tid)

    for directory in search_dirs:
        if not os.path.exists(directory):
            continue
            
        info_files = glob.glob(
            os.path.join(directory, '**', f'{tid}.info'),
            recursive=True
        )
        for info in info_files:
            os.remove(info)

        loaded_files = glob.glob(
            os.path.join(directory, '**', f'{tid}.torrent.loaded'),
            recursive=True
        )
        for loaded in loaded_files:
            os.remove(loaded)

def is_in_skip_period(skip_periods: List) -> Tuple[bool, Optional[Dict]]:
    '''Check if current time falls within any skip period'''
    now = datetime.now()
    for period in skip_periods:
        try:
            start = datetime.strptime(period['start'], '%Y%m%d %H:%M:%S')
            end = datetime.strptime(period['end'], '%Y%m%d %H:%M:%S')
            if start <= now <= end:
                return True, period
        except (ValueError, KeyError) as e:
            logger.error('Error parsing skip period: %s', e)
    return False, None

def is_keep_alive(search_dirs: List[str], tid: str) -> bool:
    '''Check if a task is explicitly marked to be kept alive'''
    for directory in search_dirs:
        if not os.path.exists(directory):
            continue
        info_files = glob.glob(
            os.path.join(directory, '**', f'{tid}.info'),
            recursive=True
        )
        if info_files:
            try:
                with open(info_files[0], 'r') as fp:
                    info = json.load(fp)
                    return info.get('keep_alive', False)
            except Exception:
                pass
    return False

def free(task: str, search_dirs: List[str], tid: str) -> bool:
    '''Check if a task is free'''
    logger.debug('task=%s, tid=%s', task, tid)
    
    found_file = None
    for directory in search_dirs:
        if not os.path.exists(directory):
            continue
        info_files = glob.glob(
            os.path.join(directory, '**', f'{tid}.info'),
            recursive=True
        )
        if info_files:
            found_file = info_files[0]
            break
            
    if not found_file:
        logger.debug('action=delete, reason=!info')
        return False

    info = None
    with open(found_file, 'r') as fp:
        info = json.load(fp)

    if info is None:
        logger.debug('action=delete, reason=!info')
        return False

    status_info = info.get('status', {})
    end_times = []

    # Check discountEndTime
    discount_end = status_info.get('discountEndTime')
    if discount_end:
        try:
            end_times.append(datetime.strptime(discount_end, '%Y-%m-%d %H:%M:%S'))
        except ValueError:
            pass

    # Check mallSingleFree endDate
    mall_free = status_info.get('mallSingleFree')
    if mall_free and isinstance(mall_free, dict):
        mall_end = mall_free.get('endDate')
        if mall_end:
            try:
                end_times.append(datetime.strptime(mall_end, '%Y-%m-%d %H:%M:%S'))
            except ValueError:
                pass

    if not end_times:
        logger.debug('action=delete, reason=!endtime')
        return False

    best_end = max(end_times)
    now = datetime.now()

    if best_end - now < timedelta(minutes=5):
        logger.debug(
            'end=%s, action=delete, reason=!free',
            best_end.strftime('%Y-%m-%d %H:%M:%S')
        )
        clean(search_dirs=search_dirs, tid=tid)
        return False
    else:
        logger.debug('action=pass, reason=free')

    return True

def main() -> None:
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
        default=None,
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
        help='Legacy path directory override'
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

    # Load configurations
    base = os.path.dirname(os.path.realpath(__file__))
    config_dir = os.path.join(base, 'config')

    mt_config = load_config(os.path.join(config_dir, 'mt.json')) or {}
    syno_config = load_config(os.path.join(config_dir, 'syno.json')) or {}
    path_config = load_config(os.path.join(config_dir, 'path.json')) or {}

    # Check for skip periods (only affects free leech check)
    skip_periods = mt_config.get('skip_check_periods', [])
    skip_free_check, period = is_in_skip_period(skip_periods)
    if skip_free_check and period:
        logger.info(
            'Current time falls within skip period (%s to %s). '
            'Skipping free-leech protection checks.',
            period['start'],
            period['end']
        )

    seeding_days_limit = syno_config.get('seeding_days_limit', 7)
    stalled_timeout = syno_config.get('stalled_timeout', 3600)

    # Merge Synology configuration
    if syno_config:
        if args.ip is None:
            args.ip = syno_config.get('ip')
        if args.port is None:
            args.port = str(syno_config.get('port', '5000'))
        if args.account is None:
            args.account = syno_config.get('account')
        if args.password is None:
            args.password = syno_config.get('password')

    # Collect all search directories
    search_dirs = []
    if args.path:
        search_dirs.append(args.path)
    
    # Add all local torrent directories from path.json
    for cat_data in path_config.get('categories', {}).values():
        path = cat_data.get('torrent')
        if path and path not in search_dirs:
            search_dirs.append(path)

    delete_tasks = []
    resume_tasks = []

    # Current time
    now_dt = datetime.now()
    now_ts = now_dt.timestamp()

    # Load last status to track progress over time
    last_status_file = os.path.join(config_dir, 'last_status.json')
    last_status = {}
    if os.path.exists(last_status_file):
        with open(last_status_file, 'r') as f:
            try:
                last_status = json.load(f)
            except json.JSONDecodeError:
                last_status = {}
    
    current_status = {}

    with Syno(
        ip=args.ip,
        port=args.port,
        account=args.account,
        password=args.password
    ) as syno:
        logger.debug('action=login')

        items = syno.ds.task.list()
        if items is None:
            logger.error('Failed to list tasks')
            return
            
        logger.debug('action=list, count=%d', len(items))

        for item in items:
            uri = item['additional']['detail']['uri']
            tid = os.path.basename(uri).replace('.torrent', '')
            task = item['id']
            status = item['status']
            title = item['title']
            detail = item['additional']['detail']
            transfer = item['additional']['transfer']

            logger.debug('tid=%s, task=%s, status=%s', tid, task, status)

            if is_keep_alive(search_dirs, tid):
                logger.debug('action=pass, reason=keep_alive')
                continue

            if status == 'downloading':
                # Record current progress
                pieces = transfer['downloaded_pieces']
                current_status[task] = {
                    'pieces': pieces,
                    'time': now_ts
                }

                # Check for progress over time
                is_stalled = False
                if task in last_status:
                    prev = last_status[task]
                    # If pieces haven't changed
                    if pieces == prev['pieces']:
                        stalled_duration = now_ts - prev['time']
                        # If stuck for more than the timeout
                        if stalled_duration > stalled_timeout:
                            logger.info(
                                'action=delete, tid=%s, reason=stalled, '
                                'pieces=%d, duration=%ds',
                                tid,
                                pieces,
                                stalled_duration
                            )
                            is_stalled = True
                    else:
                        # Progress made, update baseline to current time
                        # (handled by current_status[task] assignment above)
                        pass
                else:
                    # First time seeing this task, 
                    # use creation/start time as baseline
                    started_time = detail['started_time'] or detail['create_time']
                    if started_time > 0 and (now_ts - started_time) > stalled_timeout:
                        # If it's an old task we just started tracking and 
                        # it has 0 pieces, it might be stuck from the start
                        if pieces == 0:
                            logger.info(
                                'action=delete, tid=%s, reason=no_start, '
                                'duration=%ds',
                                tid,
                                now_ts - started_time
                            )
                            is_stalled = True

                if is_stalled:
                    delete_tasks.append({
                        'id': task,
                        'tid': tid,
                        'title': title
                    })
                    continue

                # Check if it's still free
                if not skip_free_check and \
                   not free(task=task, search_dirs=search_dirs, tid=tid):
                    delete_tasks.append({
                        'id': task,
                        'tid': tid,
                        'title': title
                    })

            if status == 'waiting':
                # completed, but reverted to waiting due to error
                if detail['completed_time'] > 0:
                    logger.debug('action=pass, reason=completed')
                    continue

                if not skip_free_check and \
                   not free(task=task, search_dirs=search_dirs, tid=tid):
                    delete_tasks.append({
                        'id': task,
                        'tid': tid,
                        'title': title
                    })

            if status == 'error':
                resume_tasks.append({'id': task, 'tid': tid, 'title': title})

            if status == 'seeding':
                # Check for seeding limit
                completed_time = detail['completed_time']
                seeding_limit_seconds = seeding_days_limit * 86400
                if completed_time > 0 and \
                   (now_ts - completed_time) > seeding_limit_seconds:
                    logger.debug(
                        'action=delete, reason=seeding_over_%d_days, '
                        'duration=%ds',
                        seeding_days_limit,
                        now_ts - completed_time
                    )
                    delete_tasks.append({
                        'id': task,
                        'tid': tid,
                        'title': title
                    })

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
                    clean(search_dirs=search_dirs, tid=t['tid'])
                    # Remove from status tracking
                    if t['id'] in current_status:
                        del current_status[t['id']]

            if len(resume_tasks) > 0:
                syno.ds.task.resume(tasks=[t['id'] for t in resume_tasks])

    # Save current status for next run
    if not args.dry_run:
        with open(last_status_file, 'w') as f:
            json.dump(current_status, f, indent=4)

if __name__ == '__main__':
    main()
