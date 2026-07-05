from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseTorrentClient(ABC):
    @abstractmethod
    def login(self) -> None:
        pass

    @abstractmethod
    def logout(self) -> None:
        pass

    @abstractmethod
    def list_tasks(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def create_task(self, uri: Optional[str] = None, file: Optional[str] = None, destination: Optional[str] = None) -> bool:
        pass

    @abstractmethod
    def delete_tasks(self, tasks: List[str]) -> None:
        pass

    @abstractmethod
    def resume_tasks(self, tasks: List[str]) -> bool:
        pass

    @abstractmethod
    def pause_tasks(self, tasks: List[str]) -> bool:
        pass
        
    def __enter__(self):
        self.login()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logout()
