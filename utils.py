from typing import Dict, Set, List, Optional
import os
import sys
import json
import logging
import argparse
import glob

def setup_logger(
    name: str = None,
    log_file: str = None,
    verbose: bool = False
) -> logging.Logger:
    '''Setup a logger with console and optional file output'''
    logger = logging.getLogger(name)
    log_level = logging.DEBUG if verbose else logging.INFO
    logger.setLevel(log_level)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if logger.hasHandlers():
        logger.handlers.clear()

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger

def load_config(file: str) -> Dict:
    '''Load configuration from a JSON file'''
    if not os.path.exists(file):
        return None
    with open(file, 'r') as fp:
        return json.load(fp)

def merge_args_with_config(
    args: argparse.Namespace,
    config: dict
) -> argparse.Namespace:
    '''Merge CLI arguments with loaded configuration'''
    if not config:
        return args
    for key, value in vars(args).items():
        if value is None and key in config:
            setattr(args, key, config[key])
    return args

def resolve_category(detail: dict, categories_map: dict) -> str:
    '''Determine the normalized category name (Movie, TV, Adult, Music, Watch)'''
    category_name = 'Watch'

    if detail:
        category = detail.get('category')
        if str(category) in categories_map:
            category_name = categories_map[str(category)]
        elif isinstance(category, dict):
            category_name = category.get('name', 'Watch')
        elif isinstance(category, str):
            category_name = category

    cat_lower = category_name.lower()
    name_lower = detail.get('name', '').lower() if detail else ''

    if 'adult' in cat_lower or 'porn' in cat_lower or 'jav' in cat_lower:
        return 'Adult'
    elif 'music' in cat_lower:
        return 'Music'
    elif 'tv' in cat_lower or 'series' in cat_lower:
        return 'TV'
    elif 'movie' in cat_lower:
        return 'Movie'

    # Fallback guessing based on torrent name
    tv_keywords = ['s0', 's1', 's2', 's3', 'e0', 'e1', 'e2', 'ep', 'season']
    movie_keywords = ['movie', 'hdtv', 'bluray', '1080p', '2160p', 'remux']

    if any(x in name_lower for x in tv_keywords):
        return 'TV'
    elif any(x in name_lower for x in movie_keywords):
        return 'Movie'

    return 'Watch'

def get_category_paths(category: str, path_config: dict) -> dict:
    '''Return the paths dictionary for a given category by merging with base_paths'''
    base_paths = path_config.get('base_paths')
    if not base_paths:
        # Fallback to old categories format if base_paths isn't present
        categories = path_config.get('categories', {})
        return categories.get(category) or categories.get('Watch') or {}
        
    def build_path(base, cat):
        return os.path.join(base, cat) if base else ''
        
    remote = base_paths.get('remote', {})
    local = base_paths.get('local', {})

    paths = {
        'torrents': build_path(base_paths.get('torrents', ''), category),
        'remote': {
            'synology': build_path(remote.get('synology', ''), category),
            'qbit': build_path(remote.get('qbit', ''), category)
        },
        'local': {
            'synology': build_path(local.get('synology', ''), category),
            'qbit': build_path(local.get('qbit', ''), category)
        }
    }
    
    # Auto-create local directories if they don't exist
    for path in [paths['torrents'], paths['local']['synology'], paths['local']['qbit']]:
        if path and not os.path.exists(path):
            try:
                os.makedirs(path, exist_ok=True)
            except OSError:
                pass # Ignore if we don't have permission or if it's a remote path mapped incorrectly
                
    return paths
