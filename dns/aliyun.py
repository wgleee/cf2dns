# -*- coding: utf-8 -*-
from math import ceil

from typing import List

from alibabacloud_alidns20150109.client import Client as Alidns20150109Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_alidns20150109 import models as alidns_20150109_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_util.client import Client as UtilClient

from .base import DnsBase
from .utils import Domain, Record, date_to_timestamp
# from .dnsbase import DnsBase

# 请参考 https://api.aliyun.com/product/Alidns
aliyun_endpoint = "alidns.cn-shenzhen.aliyuncs.com"

# 解析线路
# https://help.aliyun.com/zh/dns/resolve-line-enumeration
aliyun_lines = {
    "default": "默认",
    "telecom": "中国电信",
    "unicom": "中国联通",
    "mobile": "中国移动",
    "oversea": "境外",
    "edu": "中国教育网",
    "drpeng": "中国鹏博士",
    "btvn": "中国广电网",
    "aliyun": "阿里云",
    "search": "搜索引擎",
    "internal": "中国地区",
}

def parse_line(line: str) -> str:
    if line in ("电信", "中国电信"):
        line = "telecom"
    elif line in ("联通", "中国联通"):
        line = "unicom"
    elif line in ("移动", "中国移动"):
        line = "mobile"
    elif line == "境外":
        line = "oversea"
    elif line == "默认":
        line = "default"
    assert line in aliyun_lines , f"{line} 不是有效的线路名, 请参考: https://help.aliyun.com/zh/dns/resolve-line-enumeration"
    return line


class AliApi(DnsBase):
    def __init__(self, access_key_id, access_key_secret, endpoint=None):
        config = open_api_models.Config(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            endpoint=endpoint or aliyun_endpoint,
        )
        self._client = Alidns20150109Client(config)

    def get_domain(self) -> List[Domain]:
        describe_domains_request = alidns_20150109_models.DescribeDomainsRequest()
        runtime = util_models.RuntimeOptions()
        data = []
        try:
            result = self._client.describe_domains_with_options(
                describe_domains_request, runtime
            )
            for domain in result.body.domains.domain:
                data.append(
                    Domain(
                        domain_name=domain.domain_name,
                        create_time=date_to_timestamp(domain.create_time),
                        record_count=domain.record_count
                    )
                )
            return data
        except Exception as error:
            print(error.message)
            print(error.data.get("Recommend"))
            UtilClient.assert_as_string(error.message)

    def _get_record(self, domain: str, sub_domain: str = None, record_type: str = None, line: str = None, page_number: int = 1, page_size: int = 200) -> List[Record]:
        data = []
        describe_domain_records_request = (
            alidns_20150109_models.DescribeDomainRecordsRequest(
                domain_name=domain,
                rrkey_word=sub_domain,
                line=line,
                type=record_type,
                page_size=page_size,
                page_number=page_number,
            )
        )
        runtime = util_models.RuntimeOptions()
        try:
            result = self._client.describe_domain_records_with_options(
                describe_domain_records_request, runtime
            )
            max_page_number = ceil(result.body.total_count / page_size)
            if page_number > max_page_number:
                return
            for record in result.body.domain_records.record:
                data.append(
                    Record(
                        sub_domain=record.rr,
                        type=record.type,
                        value=record.value,
                        line=record.line,
                        ttl=record.ttl,
                        record_id=record.record_id,
                        create_timestamp=record.create_timestamp / 1000,
                        update_timestamp=record.update_timestamp / 1000 if record.update_timestamp else record.create_timestamp / 1000,
                    )
                )
            return data
        except Exception as error:
            print(error.message)
            print(error.data.get("Recommend"))
            UtilClient.assert_as_string(error.message)

    def get_record(self, domain: str, sub_domain: str = None, record_type: str = None, line: str = None) -> List[Record]:
        if line is not None:
            line = parse_line(line)
        data = []
        page_number = 1
        page_size = 200
        while True:
            record = self._get_record(
                domain=domain, sub_domain=sub_domain, record_type=record_type, line=line, page_number=page_number, page_size=page_size
            )
            if record is None:
                break
            data.extend(record)
            page_number += 1
        return data

    def create_record(self, domain: str, sub_domain: str, record_type: str, value: str, line: str = "default", ttl: int = 600) -> str:
        add_domain_record_request = alidns_20150109_models.AddDomainRecordRequest(
            domain_name=domain,
            rr=sub_domain,
            type=record_type,
            value=value,
            ttl=ttl,
            line=parse_line(line),
        )
        runtime = util_models.RuntimeOptions()
        try:
            result = self._client.add_domain_record_with_options(
                add_domain_record_request, runtime
            )
            return result.body.record_id
        except Exception as error:
            print(error.message)
            print(error.data.get("Recommend"))
            UtilClient.assert_as_string(error.message)

    def change_record( self, domain: str, sub_domain: str, record_id: str, record_type: str, value: str, line: str = "default", ttl: int = 600) -> bool:
        update_domain_record_request = alidns_20150109_models.UpdateDomainRecordRequest(
            record_id=record_id,
            rr=sub_domain,
            type=record_type,
            value=value,
            ttl=ttl,
            line=parse_line(line),
        )
        runtime = util_models.RuntimeOptions()
        try:
            # 复制代码运行请自行打印 API 的返回值
            result = self._client.update_domain_record_with_options(
                update_domain_record_request, runtime
            )
            return result.body.record_id == record_id
        except Exception as error:
            print(error.message)
            print(error.data.get("Recommend"))
            UtilClient.assert_as_string(error.message)

    def del_record(self, record_id: str, **kwargs) -> bool:
        """根据解析记录ID,删除解析记录"""
        runtime = util_models.RuntimeOptions()
        try:
            delete_domain_record_request = (
                alidns_20150109_models.DeleteDomainRecordRequest(record_id=record_id)
            )

            result = self._client.delete_domain_record_with_options(
                delete_domain_record_request, runtime
            )
            return result.body.record_id == record_id
        except Exception as error:
            print(error.message)
            print(error.data.get("Recommend"))
            UtilClient.assert_as_string(error.message)

    def del_record_by_domain(self, domain: str, sub_domain: str) -> bool:
        """根据域名删除解析记录"""
        runtime = util_models.RuntimeOptions()
        try:
            delete_sub_domain_records_request = (
                alidns_20150109_models.DeleteSubDomainRecordsRequest(
                    domain_name=domain, rr=sub_domain
                )
            )
            result = self._client.delete_sub_domain_records_with_options(
                delete_sub_domain_records_request, runtime
            )
            return result.body.rr == sub_domain
        except Exception as error:
            print(error.message)
            print(error.data.get("Recommend"))
            UtilClient.assert_as_string(error.message)
