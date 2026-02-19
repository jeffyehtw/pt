'''
M-Team torrent tracker API wrapper
'''
import os
import json
import logging

from mt.latest import Latest
from mt.download import Download
from mt.exist import Exist
from mt.detail import Detail
from mt.search import Search

logger = logging.getLogger(__name__)

class MT:
    '''Client for the M-Team torrent tracker API'''

    def __init__(
        self,
        rss: str = None,
        key: str = None,
        output: str = None
    ) -> None:
        '''Initialize the MT client and its sub-operation instances'''
        logger.debug('rss=%s, output=%s', rss, output)

        self.key = key
        self.rss = rss
        self.output = output
        self.list = None

        self.latest = Latest(key=key, rss=rss)
        self.download = Download(key=key, output=output)
        self.exist = Exist(output=output)
        self.detail = Detail(key=key)
        self.search = Search(key=key)

    def __enter__(self):
        '''Load the torrent history list from disk'''
        logger.debug('')

        if self.output is not None:
            with open(os.path.join(self.output, 'list.json')) as fp:
                self.list = json.load(fp)

        # Share the loaded list with sub-instances that need it
        self.download.list = self.list
        self.exist.list = self.list

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        '''Save the torrent history list back to disk'''
        logger.debug('')

        # Sync list back from download in case it was mutated
        self.list = self.download.list

        with open(os.path.join(self.output, 'list.json'), 'w') as fp:
            json.dump(self.list, fp, indent=4)
