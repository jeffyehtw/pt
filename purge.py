'''
Utility script to bulk-purge files and directories based on age, keyword, or extension.
'''
import os
import sys
import shutil
import argparse
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from utils import setup_logger, load_config, get_category_paths

__description__ = 'Delete or trash files based on age, keyword, and extension'
__epilog__ = 'Purge process completed.'

def get_files(
    path: str,
    recursive: bool = False
) -> List[str]:
    '''Collect all file/directory paths in the given target path'''
    if not recursive:
        return [os.path.join(path, f) for f in os.listdir(path)]
    
    all_items = []
    for root, dirs, files in os.walk(path):
        for name in files:
            all_items.append(os.path.join(root, name))
        for name in dirs:
            all_items.append(os.path.join(root, name))
    return all_items

def purge_items(
    items: List[str],
    date: Optional[datetime.date] = None,
    before: Optional[datetime.date] = None,
    older_than: Optional[int] = None,
    keyword: Optional[str] = None,
    extension: Optional[str] = None,
    trash: bool = False,
    dry_run: bool = False,
    logger: logging.Logger = None
) -> int:
    '''Apply filters and delete/trash matched items'''
    now = datetime.now()
    targets = []
    
    # Resolve relative age if provided
    cutoff_date = None
    if older_than is not None:
        cutoff_date = (now - timedelta(days=older_than)).date()

    for item in items:
        # 1. Skip if path doesn't exist (might happen in recursive walk)
        if not os.path.exists(item):
            continue

        # 2. Extract Metadata
        try:
            mtime = os.path.getmtime(item)
            item_date = datetime.fromtimestamp(mtime).date()
        except OSError:
            continue

        # 3. Apply Filters
        if date and item_date != date:
            continue
        if before and item_date > before:
            continue
        if cutoff_date and item_date > cutoff_date:
            continue
        if keyword and keyword.lower() not in os.path.basename(item).lower():
            continue
        if extension and not item.lower().endswith(extension.lower()):
            continue

        targets.append(item)

    if not targets:
        return 0

    # 4. Confirmation
    if not dry_run:
        print(f"\nMatched {len(targets)} items.")
        confirm = input(f"Are you sure you want to {'TRASH' if trash else 'DELETE'} them? [y/N]: ")
        if confirm.lower() != 'y':
            print("Operation cancelled.")
            return 0

    # 5. Execution
    success_count = 0
    for target in targets:
        action_verb = "trash" if trash else "delete"
        if dry_run:
            logger.info("[Dry Run] Would %s: %s", action_verb, target)
            success_count += 1
            continue

        try:
            if trash:
                # Basic trash implementation: move to a folder named .trash in the root of search
                # If on Synology, we could target #recycle, but .trash is safer for general use
                trash_dir = os.path.join(os.path.dirname(target), '.trash')
                os.makedirs(trash_dir, exist_ok=True)
                shutil.move(target, os.path.join(trash_dir, os.path.basename(target)))
            else:
                if os.path.isfile(target) or os.path.islink(target):
                    os.remove(target)
                else:
                    shutil.rmtree(target)
            
            logger.info("%s: %s", action_verb, target)
            success_count += 1
        except Exception as e:
            logger.error("Failed to %s %s: %s", action_verb, target, e)

    return success_count

def main() -> None:
    '''Entry point: parse arguments and execute purge'''
    parser = argparse.ArgumentParser(
        description=__description__,
        epilog=__epilog__
    )
    parser.add_argument('path', nargs='?', type=str, help='Target directory path (optional if --category is provided)')
    parser.add_argument('--category', type=str, help='Target category from path.json (e.g., Movie, TV)')
    parser.add_argument('--date', type=str, help='Exact creation date (YYYY-MM-DD)')
    parser.add_argument('--before', type=str, help='Target date or older (YYYY-MM-DD)')
    parser.add_argument('--older-than', type=int, help='Items older than X days')
    parser.add_argument('--keyword', type=str, help='Filter by filename keyword')
    parser.add_argument('--ext', type=str, help='Filter by file extension (e.g., .torrent)')
    parser.add_argument('--recursive', action='store_true', help='Search subdirectories')
    parser.add_argument('--trash', action='store_true', help='Move to .trash instead of deleting')
    parser.add_argument('--dry-run', action='store_true', help='Preview matches without acting')
    parser.add_argument('--verbose', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    logger = setup_logger(verbose=args.verbose)

    # Validate Dates
    target_date = None
    before_date = None
    try:
        if args.date:
            target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        if args.before:
            before_date = datetime.strptime(args.before, '%Y-%m-%d').date()
    except ValueError:
        logger.error("Error: Dates must be in YYYY-MM-DD format")
        sys.exit(1)

    target_path = args.path

    if not target_path and not args.category:
        logger.error("Error: Must provide either a target path or a --category.")
        parser.print_help()
        sys.exit(1)

    if args.category:
        config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')
        path_config = load_config(os.path.join(config_dir, 'path.json')) or {}
        
        category_paths = get_category_paths(args.category, path_config)
        local_download = category_paths.get('local_download')
        if not local_download:
            logger.error("Error: Could not resolve file path for category '%s' in path.json.", args.category)
            sys.exit(1)
        
        # Override the path with the resolved category download dir
        target_path = local_download
        logger.info("Resolved category '%s' to path: %s", args.category, target_path)

    if not os.path.exists(target_path):
        logger.error("Error: Path does not exist: %s", target_path)
        sys.exit(1)

    # Execute
    items = get_files(target_path, recursive=args.recursive)
    count = purge_items(
        items=items,
        date=target_date,
        before=before_date,
        older_than=args.older_than,
        keyword=args.keyword,
        extension=args.ext,
        trash=args.trash,
        dry_run=args.dry_run,
        logger=logger
    )

    logger.info("Successfully processed %d items.", count)

if __name__ == '__main__':
    main()
