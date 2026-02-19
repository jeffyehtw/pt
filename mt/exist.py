'''
Check if a torrent has already been downloaded
'''
import os
import logging

logger = logging.getLogger(__name__)


class Exist:
    '''Check if a torrent has already been downloaded'''

    def __init__(self, output: str) -> None:
        '''Initialize with output directory'''
        logger.debug('output=%s', output)

        self.output = output
        self.list = None  # shared reference, set by MT after __enter__

    def __call__(self, tid: str) -> bool:
        '''Return True if the torrent has already been downloaded'''
        logger.debug('tid=%s', tid)

        if self.list is not None:
            return tid in self.list

        # Fall back to checking for the files on disk
        torrent = os.path.join(self.output, f'{tid}.torrent')
        loaded = os.path.join(self.output, f'{tid}.torrent.loaded')

        return os.path.exists(torrent) or os.path.exists(loaded)
