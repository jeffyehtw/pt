'''
Shared HTTP helpers for M-Team API requests
'''
import time
import random
import requests
import logging

logger = logging.getLogger(__name__)

BASE_URL = 'https://api.m-team.cc/api'

def headers(key: str) -> dict:
    '''Return common API request headers'''
    return {'x-api-key': key}

def post(key: str, url: str, payload: dict, form: bool = False) -> dict:
    '''Send a POST request with a random delay to avoid rate limiting'''
    logger.debug('url=%s, payload=%s, form=%s', url, payload, form)

    time.sleep(random.randint(2, 5))

    # Endpoints that expect form-encoded data (detail, download)
    if form:
        response = requests.post(url, headers=headers(key), data=payload)
    # Endpoints that accept JSON (search)
    else:
        response = requests.post(url, headers=headers(key), json=payload)

    if response.status_code != 200:
        logger.info(
            'action=skip, reason=!response, status=%s',
            response.status_code
        )
        return None

    ret = response.json()
    if ret.get('message') != 'SUCCESS':
        logger.info('action=skip, reason=%s', ret.get('message'))
        return None

    return ret.get('data')
