from __future__ import annotations
import typing
from typing import List

import os
import requests
import logging

logger = logging.getLogger(__name__)

class Task:
    '''Class to manage qBittorrent tasks, mimicking Synology Task API.'''
    def __init__(self, ip: str, port: str, account: str = None, password: str = None, api_key: str = None) -> None:
        logger.debug('ip=%s, port=%s', ip, port)

        self.base_url = f'http://{ip}:{port}/api/v2'
        self.account = account
        self.password = password
        self.api_key = api_key
        self.session = requests.Session()
        
        if self.api_key:
            self.session.headers.update({'X-Api-Key': self.api_key})

    def login(self):
        if self.account and self.password:
            response = self.session.post(
                f'{self.base_url}/auth/login',
                data={'username': self.account, 'password': self.password},
                timeout=10
            )
            if response.status_code in [200, 204] and ('Ok.' in response.text or not response.text):
                logger.debug('qBittorrent login successful.')
            else:
                logger.error('qBittorrent login failed: status=%s, text=%s', response.status_code, response.text)

    def logout(self):
        self.session.post(f'{self.base_url}/auth/logout', timeout=10)

    def list(self, offset: int = 0, limit: int = -1) -> List[dict]:
        '''List tasks, mapped to Synology format.'''
        params = {}
        if offset > 0:
            params['offset'] = offset
        if limit > 0:
            params['limit'] = limit
            
        response = self.session.get(f'{self.base_url}/torrents/info', params=params, timeout=30)
        if response.status_code == 200:
            torrents = response.json()
            tasks = []
            for t in torrents:
                # Map state to syno status
                state = t.get('state', '')
                status = 'waiting'
                if state in ['downloading', 'metaDL', 'stalledDL', 'forceDL']:
                    status = 'downloading'
                elif state in ['uploading', 'stalledUP', 'forceUP']:
                    status = 'seeding'
                elif state in ['error', 'missingFiles']:
                    status = 'error'
                elif state in ['pausedDL', 'pausedUP']:
                    status = 'paused'
                
                # We expect tid to be in tags, or we extract from name
                tid = t.get('tags', '')
                if not tid:
                    tid = t.get('name', '')
                
                # Fake the URI so os.path.basename(uri).replace('.torrent', '') works in manage.py
                fake_uri = f"/{tid}.torrent"
                
                tasks.append({
                    'id': t['hash'],
                    'status': status,
                    'title': t['name'],
                    'additional': {
                        'detail': {
                            'uri': fake_uri,
                            'completed_time': t.get('completion_on', 0),
                            'started_time': t.get('added_on', 0),
                            'create_time': t.get('added_on', 0)
                        },
                        'transfer': {
                            # manage.py checks downloaded_pieces to see if it's stalled. 
                            # We can just use downloaded bytes since it only checks for strict equality.
                            'downloaded_pieces': t.get('downloaded', 0)
                        }
                    }
                })
            return tasks
        return None

    def info(self, tasks: List[str]) -> None:
        pass

    def create(
            self,
            uri: str = None,
            file: str = None,
            destination: str = None
        ) -> bool:
        '''Create a new download task.'''
        logger.debug('uri=%s, file=%s, destination=%s', uri, file, destination)
        
        data = {}
        if destination:
            data['savepath'] = destination

        # Extract tid from filename to add as tag
        if file:
            tid = os.path.basename(file).replace('.torrent', '')
            data['tags'] = tid
            
            with open(file, 'rb') as f:
                files = {'torrents': (os.path.basename(file), f, 'application/x-bittorrent')}
                response = self.session.post(f'{self.base_url}/torrents/add', data=data, files=files, timeout=30)
        elif uri:
            data['urls'] = uri
            response = self.session.post(f'{self.base_url}/torrents/add', data=data, timeout=30)
        else:
            return False
            
        if response.status_code == 200:
            return True
        else:
            logger.error('action=create_fail, status_code=%s, response=%s', response.status_code, response.text)
            return False

    def delete(self, tasks: List[str], force_complete: bool = False) -> None:
        '''Delete tasks. tasks is a list of hashes.'''
        logger.debug('tasks=[%s]', ','.join(tasks))
        # force_complete here implies deleting data too? manage.py doesn't use it.
        # But let's delete data if force_complete=True, just in case.
        data = {
            'hashes': '|'.join(tasks),
            'deleteFiles': 'true'
        }
        response = self.session.post(f'{self.base_url}/torrents/delete', data=data, timeout=30)
        if response.status_code == 200:
            logger.debug('Deleted tasks successfully')

    def pause(self, tasks: List[str]) -> bool:
        logger.debug('tasks=[%s]', ','.join(tasks))
        data = {'hashes': '|'.join(tasks)}
        response = self.session.post(f'{self.base_url}/torrents/pause', data=data, timeout=30)
        return response.status_code == 200

    def resume(self, tasks: List[str]) -> bool:
        logger.debug('tasks=[%s]', ','.join(tasks))
        data = {'hashes': '|'.join(tasks)}
        response = self.session.post(f'{self.base_url}/torrents/resume', data=data, timeout=30)
        return response.status_code == 200
