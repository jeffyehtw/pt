'''
Utility script to find specific task IDs on a Synology NAS by title keyword
'''
import os
import sys
import argparse
import logging
from typing import List, Dict, Optional

from syno.api import Syno
from utils import setup_logger, load_config

__description__ = 'Find task IDs on Synology NAS'
__epilog__ = 'Task lookup completed.'

def find_tasks(syno: Syno, keyword: str) -> List[Dict[str, str]]:
    '''
    Search for tasks on the NAS matching a keyword.
    Returns a list of dictionaries containing 'id' and 'title'.
    '''
    tasks = syno.ds.task.list()
    if tasks is None:
        return []
        
    return [
        {'id': t['id'], 'title': t['title']} 
        for t in tasks 
        if keyword.lower() in t['title'].lower()
    ]

def main() -> None:
    '''Entry point: parse arguments and lookup tasks'''
    parser = argparse.ArgumentParser(
        description=__description__,
        epilog=__epilog__
    )
    parser.add_argument(
        'keyword',
        type=str,
        help='Keyword to search for in task titles'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose mode'
    )
    args = parser.parse_args(sys.argv[1:])

    # Setup logger
    logger = setup_logger(verbose=args.verbose)

    # Load NAS configuration
    config_dir = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'config'
    )
    syno_config = load_config(os.path.join(config_dir, 'syno.json'))
    
    if not syno_config:
        logger.error('Could not load config/syno.json')
        sys.exit(1)

    # Connect and search
    try:
        with Syno(
            ip=syno_config['ip'],
            port=str(syno_config['port']),
            account=syno_config['account'],
            password=syno_config['password']
        ) as syno:
            logger.info("Searching for tasks matching: '%s'...", args.keyword)
            
            results = find_tasks(syno, args.keyword)
            
            if results:
                print(f"\nFound {len(results)} matching tasks:")
                for res in results:
                    print(f"  ID: {res['id']} | Title: {res['title']}")
                print("")
            else:
                logger.info("No tasks found matching '%s'", args.keyword)
                
    except Exception as e:
        logger.error("An error occurred during NAS interaction: %s", e)
        sys.exit(1)

if __name__ == '__main__':
    main()
