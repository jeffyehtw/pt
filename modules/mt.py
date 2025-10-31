import os
import json
import time
import random
import shutil
import requests
import xmltodict
import logging

logger = logging.getLogger(__name__)

class Url():
    def __init__(self):
        self.detail = 'https://api.m-team.cc/api/torrent/detail'
        self.download = 'https://api.m-team.cc/api/torrent/genDlToken'
        self.search = 'https://api.m-team.cc/api/torrent/search'

class MT():
    def __init__(self, rss: str = None, key: str = None, output: str = None):
        self.key = key
        self.rss = rss
        self.output = output
        self.url = Url()
        self.list = None

    def __enter__(self):
        if self.output is not None:
            with open(os.path.join(self.output, 'list.json')) as fp:
                self.list = json.load(fp)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        with open(os.path.join(self.output, 'list.json'), 'w') as fp:
            json.dump(self.list, fp, indent=4)

    def latest(self) -> list[dict]:
        try:
            response = requests.get(self.rss, headers={ 'x-api-key': self.key })
            if response.status_code == 200:
                ret = xmltodict.parse(response.text, attr_prefix='')
                return ret['rss']['channel']['item']
            else:
                logger.info('action=skip')
                logger.info('reason=!response')
        except Exception as e:
            logger.error(str(e))
        return None

    def download(self, tid: str, detail: dict = None) -> None:
        headers = { 'x-api-key': self.key }
        payload = { 'id': tid }

        try:
            time.sleep(random.randint(2, 5))
            response = requests.request(
                'POST',
                self.url.download,
                headers=headers,
                data=payload
            )
            if response.status_code == 200:
                response = response.json()
                if response['message'] == 'SUCCESS':
                    url = response['data'] + '&useHttps=true&type=ipv4'

                    response = requests.get(url)
                    if response.status_code == 200:
                        logger.info('action=download')

                        torrent = os.path.join(self.output, f'{tid}.torrent')
                        with open(torrent, 'wb') as fp:
                            fp.write(response.content)

                        if detail is not None:
                            info = os.path.join(self.output, f'{tid}.info')
                            with open(info, 'w') as fp:
                                json.dump(detail, fp, indent=4)

                        if self.list is None:
                            self.list = []
                        self.list.append(tid)
                    else:
                        logger.info('action=skip')
                        logger.info('reason=!response')
                else:
                    logger.info('action=skip')
                    logger.info('reason=!response')

            else:
                logger.info('action=skip')
                logger.info('reason=!response')

        except Exception as e:
            logger.error(str(e))

    def exist(self, tid: str) -> bool:
        if self.list is None:
            torrent = os.path.join(self.output, f'{tid}.torrent')
            synology = os.path.join(self.output, f'{tid}.torrent.loaded')
            return os.path.exists(torrent) or os.path.exists(synology)
        else:
            return tid in self.list

    def detail(self, tid: str) -> dict:
        payload = { 'id': tid }
        headers = { 'x-api-key': self.key }

        try:
            time.sleep(random.randint(2, 5))
            response = requests.request(
                'POST',
                self.url.detail,
                headers=headers,
                data=payload
            )
            if response.status_code == 200:
                ret = response.json()
                if ret['message'] == 'SUCCESS':
                    return ret['data']
                else:
                    logger.info('action=skip')
                    logger.info('reason=!response')
            else:
                logger.info('action=skip')
                logger.info('reason=!response')
        except Exception as e:
            logger.error(str(e))

        return None

    def search(
            self,
            mode: str,
            free: bool,
            index: int,
            size: int,
            keyword: str
        ) -> list[dict]:
        headers = { 'x-api-key': self.key }
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
            time.sleep(random.randint(2, 5))
            response = requests.post(
                self.url.search,
                headers=headers,
                json=payload
            )
            if response.status_code == 200:
                return response.json()['data']['data']
            else:
                logger.info('action=skip')
                logger.info('reason=!response')

        except Exception as e:
            logger.error(str(e))
