'''
Search for torrents on M-Team
'''
import logging

from mt.base import BASE_URL, post

logger = logging.getLogger(__name__)


class Search:
    '''Search for torrents on M-Team'''

    def __init__(self, key: str) -> None:
        '''Initialize with API key'''
        logger.debug('')

        self.key = key

    def __call__(
        self,
        mode: str,
        free: bool,
        index: int,
        size: int,
        keyword: str = None
    ) -> list[dict]:
        '''Search for torrents by mode, filter, and keyword'''
        logger.debug(
            'mode=%s, free=%s, index=%s, size=%s, keyword=%s',
            mode,
            free,
            index,
            size,
            keyword
        )

        payload = {
            'mode': mode,
            'pageNumber': index,
            'pageSize': size,
        }

        if free:
            payload['discount'] = 'FREE'
        if keyword is not None:
            payload['keyword'] = keyword

        try:
            data = post(self.key, f'{BASE_URL}/torrent/search', payload)
            if data is not None:
                return data['data']

        except Exception as e:
            logger.error(str(e))

        return None
