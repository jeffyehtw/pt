'''
Fetch detailed metadata for a torrent from M-Team
'''
import logging

from mt.base import BASE_URL, post

logger = logging.getLogger(__name__)

class Detail:
    '''Fetch detailed metadata for a torrent from M-Team'''

    def __init__(self, key: str) -> None:
        '''Initialize with API key'''
        logger.debug('')

        self.key = key

    def __call__(self, tid: str) -> dict:
        '''Return detailed metadata for a torrent by ID'''
        logger.debug('tid=%s', tid)

        try:
            # detail endpoint requires form-encoded data
            return post(
                self.key,
                f'{BASE_URL}/torrent/detail',
                {'id': tid},
                form=True
            )
        except Exception as e:
            logger.error(str(e))

        return None
