import typing
import logging
from typing import List, Dict, Any, Optional

from .task import Task
from base_client import BaseTorrentClient

logger = logging.getLogger(__name__)

class Qbit(BaseTorrentClient):
    '''Main qBittorrent API client wrapper.'''
    def __init__(self, ip: str, port: str, account: str = None, password: str = None, api_key: str = None) -> None:
        logger.debug('ip=%s, port=%s', ip, port)

        self.ip = ip
        self.port = port
        self.account = account
        self.password = password
        self.api_key = api_key
        
        self.task = Task(ip=ip, port=port, account=account, password=password, api_key=api_key)

    def login(self) -> None:
        self.task.login()

    def logout(self) -> None:
        self.task.logout()

    def __enter__(self) -> "Qbit":
        logger.debug('')
        self.login()
        return self

    def __exit__(
        self,
        exc_type: typing.Any,
        exc_value: typing.Any,
        traceback: typing.Any
    ) -> None:
        logger.debug('')
        self.logout()

    def list_tasks(self) -> List[Dict[str, Any]]:
        return self.task.list()

    def create_task(self, uri: Optional[str] = None, file: Optional[str] = None, destination: Optional[str] = None) -> bool:
        return self.task.create(uri=uri, file=file, destination=destination)

    def delete_tasks(self, tasks: List[str]) -> None:
        self.task.delete(tasks=tasks)

    def resume_tasks(self, tasks: List[str]) -> bool:
        return self.task.resume(tasks=tasks)

    def pause_tasks(self, tasks: List[str]) -> bool:
        return self.task.pause(tasks=tasks)
