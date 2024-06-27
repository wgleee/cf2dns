from typing import List

from .aliyun import AliApi
from .dnspod import DnsPodApi
# from .huawei import HuaWeiApi

from .utils import Domain, Record

__all__ = ("AliApi", "DnsPodApi", "Domain", "Record")
