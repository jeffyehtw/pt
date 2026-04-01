import os
import sys
import json
import logging

class MTeamAPIError(Exception):
    '''Custom exception for M-Team API errors'''
    pass

class SynologyAPIError(Exception):
    '''Custom exception for Synology API errors'''
    pass

def setup_logger(name: str = None, log_file: str = None, verbose: bool = False) -> logging.Logger:
    '''Setup a logger with console and optional file output'''
    logger = logging.getLogger(name)
    log_level = logging.DEBUG if verbose else logging.INFO
    logger.setLevel(log_level)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

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

def load_config(file: str) -> dict:
    '''Load configuration from a JSON file'''
    if not os.path.exists(file):
        return None
    with open(file, 'r') as fp:
        return json.load(fp)

def merge_args_with_config(args, config: dict):
    '''Merge CLI arguments with loaded configuration'''
    if not config:
        return args
    for key, value in vars(args).items():
        if value is None and key in config:
            setattr(args, key, config[key])
    return args
