'''
Download torrent files from M-Team
'''
import os
import json
import requests
import logging

from mt.base import BASE_URL, post

logger = logging.getLogger(__name__)


class Download:
    '''Download a torrent file from M-Team'''

    def __init__(self, key: str, output: str) -> None:
        '''Initialize with API key and output directory'''
        logger.debug('output=%s', output)

        self.key = key
        self.output = output
        self.list = None  # shared reference, set by MT after __enter__

    def __call__(self, tid: str, detail: dict = None) -> None:
        '''Download torrent by ID and optionally save its metadata'''
        logger.debug('tid=%s', tid)

        try:
            # Step 1: Get a temporary download token/URL from the API
            data = post(
                self.key,
                f'{BASE_URL}/torrent/genDlToken',
                {'id': tid},
                form=True
            )
            if data is None:
                logger.info('action=skip, reason=!data')
                return

            # Step 2: Append connection options and fetch the actual torrent file
            torrent_url = data + '&useHttps=true&type=ipv4'
            response = requests.get(torrent_url)

            if response.status_code != 200:
                logger.info(
                    'action=skip, reason=!response, status=%s',
                    response.status_code
                )
                return

            # Step 3: Save the .torrent file
            logger.info('action=download, tid=%s', tid)
            torrent_path = os.path.join(self.output, f'{tid}.torrent')
            with open(torrent_path, 'wb') as fp:
                fp.write(response.content)

            # Step 4: Optionally save torrent metadata as a .info file
            if detail is not None:
                info_path = os.path.join(self.output, f'{tid}.info')
                with open(info_path, 'w') as fp:
                    json.dump(detail, fp, indent=4)

            # Step 5: Record this tid in the history list
            if self.list is None:
                self.list = []
            self.list.append(tid)

        except Exception as e:
            logger.error(str(e))
