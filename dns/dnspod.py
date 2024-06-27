#!/bin/env python3

import json

from typing import List

from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import (
    TencentCloudSDKException,
)
from tencentcloud.dnspod.v20210323 import dnspod_client, models

from .base import DnsBase
from .utils import Domain, Record, date_to_timestamp


dnspod_endpoint = "dnspod.tencentcloudapi.com"


class DnsPodApi(DnsBase):
    def __init__(self, secret_id, secret_key, endpoint=None):
        cred = credential.Credential(secret_id, secret_key)
        http_profile = HttpProfile()
        http_profile.endpoint = endpoint or dnspod_endpoint
        client_profile = ClientProfile()
        client_profile.httpProfile = http_profile
        self._client = dnspod_client.DnspodClient(cred, "", client_profile)
        self._lines = {}

    def get_domain(self) -> List[Domain]:
        data = []
        req = models.DescribeDomainListRequest()
        try:
            result = self._client.DescribeDomainList(req)
            for domain in result.DomainList:
                data.append(
                    Domain(
                        domain_name=domain.Name,
                        create_time=date_to_timestamp(domain.CreatedOn),
                        record_count=domain.RecordCount,
                    )
                )
            return data
        except TencentCloudSDKException as err:
            raise SystemExit(err.message)

    def get_lines(self, domain: str, domain_grade: str = "D_FREE") -> List:
        """DomainGrade: 
            旧套餐: D_FREE、D_PLUS、D_EXTRA、D_EXPERT、D_ULTRA 分别对应免费套餐、个人豪华、企业1、企业2、企业3。
            新套餐: DP_FREE、DP_PLUS、DP_EXTRA、DP_EXPERT、DP_ULTRA 分别对应新免费、个人专业版、企业创业版、企业标准版、企业旗舰版。
        """
        if self._lines.get(domain):
            return self._lines.get(domain)
        req = models.DescribeRecordLineListRequest()
        try:
            params = {"Domain": domain, "DomainGrade": domain_grade}
            req.from_json_string(json.dumps(params))
            result = self._client.DescribeRecordLineList(req)
            self._lines[domain] = [line.Name for line in result.LineList]
            return self._lines.get(domain)
        except TencentCloudSDKException as err:
            raise SystemExit(err.message)

    def verify_line(self, domain: str, line: str) -> None:
        lines = self.get_lines(domain)
        assert (
            line in lines
        ), f"{line} 不是有效的线路名, 请通过 get_lines 方法获取所有线路名"

    def get_record(self, domain: str, sub_domain: str = None, record_type: str = None, line: str = None, keyword: str = None, limit: int = 200, offset: int = 0, **kwargs) -> List[Record]:
        """获取域名解析记录 # https://cloud.tencent.com/document/api/1427/56166
        >>> cloud = DnsPod(secret_id, secret_key)
        # 获取域名所有解析记录
        >>> cloud.get_record("test.com")
        # 获取子域名所有解析记录
        >>> cloud.get_record("test.com", sub_domain="www")
        # 通过记录值，获取解析记录
        >>> cloud.get_record("test.com", keyword="1.2.2.1")
        """
        data = []
        params = {"Domain": domain, "Limit": limit, "Offset": offset}
        if sub_domain is not None:
            params["Subdomain"] = sub_domain
        if record_type is not None:
            params["RecordType"] = record_type
        if line is not None:
            self.verify_line(domain, line)
            params["RecordLine"] = line
        if keyword is not None:
            params["Keyword"] = keyword
        params.update(kwargs)
        has_next_page = True
        try:
            while has_next_page:
                req = models.DescribeRecordListRequest()
                req.from_json_string(json.dumps(params))
                result = self._client.DescribeRecordList(req)
                list_count = result.RecordCountInfo.ListCount + params["Offset"]
                if list_count == result.RecordCountInfo.TotalCount:
                    has_next_page = False
                params["Offset"] += limit
                for record in result.RecordList:
                    data.append(
                        Record(
                            sub_domain=record.Name,
                            type=record.Type,
                            record_id=record.RecordId,
                            value=record.Value,
                            line=record.Line,
                            ttl=record.TTL,
                            create_timestamp=date_to_timestamp(record.UpdatedOn),
                            update_timestamp=date_to_timestamp(record.UpdatedOn),
                        )
                    )
            return data
        except TencentCloudSDKException as err:
            return []
    def create_record(self, domain: str, sub_domain: str, record_type: str, value: str, line: str = "默认", ttl: int = 600, **kwargs) -> str:
        """添加域名解析记录"""
        try:
            req = models.CreateRecordRequest()
            self.verify_line(domain, line)
            params = {
                "Domain": domain,
                "SubDomain": sub_domain,
                "Value": value,
                "RecordType": record_type,
                "RecordLine": line,
                "TTL": ttl,
            }
            params.update(kwargs)
            req.from_json_string(json.dumps(params))
            result = self._client.CreateRecord(req)
            return result.RecordId
        except TencentCloudSDKException as err:
            raise SystemExit(sub_domain, err.message)

    def change_record( self, domain: str, sub_domain: str, record_id: int, record_type: str, value: str, line: str = "默认", ttl=600, **kwargs) -> bool:
        self.verify_line(domain, line)
        params = {
            "Domain": domain,
            "SubDomain": sub_domain,
            "Value": value,
            "RecordType": record_type,
            "RecordLine": line,
            "RecordId": record_id,
        }
        try:
            req = models.ModifyRecordRequest()
            req.from_json_string(json.dumps(params))
            result = self._client.ModifyRecord(req)
            return result.RecordId == record_id
        except TencentCloudSDKException as err:
            raise SystemExit(err)

    def del_record(self, domain: str, record_id: int) -> bool:
        try:
            req = models.DeleteRecordRequest()
            params = {"Domain": domain, "RecordId": record_id}
            req.from_json_string(json.dumps(params))
            self._client.DeleteRecord(req)
            return True
        except TencentCloudSDKException as err:
            raise SystemExit(err)

    def del_record_by_domain(self, domain: str, sub_domain: str = None) -> bool:
        record_list = self.get_record(domain=domain, sub_domain=sub_domain)
        for record in record_list:
            self.del_record(domain=domain, record_id=record.record_id)
        return True
