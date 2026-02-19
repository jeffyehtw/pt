import os
import shutil
import argparse
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger()

def delete(
    path: str,
    date: str = None,
    before: str = None,
    keyword: str = None,
    dry_run: bool = False
):
    '''
    Deletes files in a directory based on the given filter condition
    '''
    # Validate the date format
    if date is not None:
        try:
            date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            logger.error('Error: Date must be in YYYY-MM-DD format')
            return
    if before is not None:
        try:
            before = datetime.strptime(before, '%Y-%m-%d').date()
        except ValueError:
            logger.error('Error: Date must be in YYYY-MM-DD format')
            return

    if not os.path.exists(path):
        logger.error('Error: The directory %s does not exist', path)
        return

    targets = []
    for file in os.listdir(path):
        file = os.path.join(path, file)

        # Get creation time and convert to date object
        try:
            creation_time = os.path.getctime(file)
            creation_time = datetime.fromtimestamp(creation_time).date()

        except OSError as e:
            logger.error('Error accessing %s: %s', file, str(e))
            continue

        if date is not None and creation_time != date:
            continue

        if before is not None and creation_time > before:
            continue

        if keyword is not None and keyword not in file:
            continue

        targets.append(file)

    for target in targets:
        logger.info('delete: %s', target)

        if dry_run:
            continue

        try:
            if os.path.isfile(target):
                os.remove(target)
            else:
                shutil.rmtree(target)

        except Exception as e:
            logger.error('Error deleting %s: %s', target, str(e))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Delete files based on creation date and keyword'
    )

    # Adding arguments
    parser.add_argument(
        'path',
        type=str,
        help='The path to the directory to scan'
    )
    parser.add_argument(
        '--date',
        type=str,
        default=None,
        help='The specific date to target (format: YYYY-MM-DD)'
    )
    parser.add_argument(
        '--keyword',
        type=str,
        default=None,
        help='Filter files containing this keyword'
    )
    parser.add_argument(
        '--before',
        type=str,
        default=None,
        help='Delete files on or before the specified date'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='List files to be deleted without actually deleting them'
    )

    args = parser.parse_args()

    delete(
        path=args.path,
        date=args.date,
        before=args.before,
        keyword=args.keyword,
        dry_run=args.dry_run
    )
