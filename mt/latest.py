'''
Fetch the latest torrents from the M-Team RSS feed
'''
import requests
import xmltodict
import logging

from mt.base import headers

logger = logging.getLogger(__name__)


class Latest:
    '''Fetch the latest torrents from the RSS feed'''

    def __init__(self, key: str, rss: str) -> None:
        '''Initialize with API key and RSS URL'''
        logger.debug('rss=%s', rss)

        self.key = key
        self.rss = rss

    def __call__(self) -> list[dict]:
        '''Return the latest torrent items from the RSS feed'''
        logger.debug('')

        try:
            response = requests.get(self.rss, headers=headers(self.key))
            if response.status_code == 200:
                ret = xmltodict.parse(response.text, attr_prefix='')
                return ret['rss']['channel']['item']
            else:
                logger.info(
                    'action=skip, reason=!response, status=%s',
                    response.status_code
                )

        except Exception as e:
            logger.error(str(e))

        return None
