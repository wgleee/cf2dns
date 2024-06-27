from typing import List
from abc import ABCMeta, abstractmethod

class DnsBase(metaclass=ABCMeta):
    @abstractmethod
    def get_domain(self) -> List:
        pass

    @abstractmethod
    def get_record(self, domain: str, sub_domain: str, record_type: str, line: str, **kwargs) -> List:
        pass

    @abstractmethod
    def create_record(self, domain: str, sub_domain: str, record_type: str, value: str, line: str, ttl: int, **kwargs) -> str:
        pass

    @abstractmethod
    def change_record(self, domain: str, sub_domain: str, record_id: int, record_type: str, value: str, line: str, ttl: int, **kwargs) -> bool:
        pass

    @abstractmethod
    def del_record(self, record_id: int, **kwargs) -> bool:
        pass

    @abstractmethod
    def del_record_by_domain(self, domain: str, sub_domain: str) -> bool:
        pass
