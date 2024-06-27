import os
import sys
import json
import random
import argparse

import requests

from collections import namedtuple
from dns import AliApi, DnsPodApi
from log import get_logger

# 可以从 https://shop.hostmonit.com 获取
KEY = os.environ.get("KEY","o1zrmHAF")

RECORD_LINE = {"CM": "移动", "CU": "联通", "CT": "电信", "AB": "境外", "DEF": "默认"}
DNS_API = {"aliyun": AliApi, "dnspod": DnsPodApi}

logger = get_logger("cf2dns.log", level="debug")

epilog_info = """
使用示例:
    # 通过阿里云 API 为域名 shop.example.com 和 stock.example.com 添加 CM:移动 CU:联通 CT:电信 线路 A 记录解析
    $ %s aliyun -4 -i xxxx -k xxxxx -d '{"example.com": {"shop": ["CM", "CU", "CT"], "stock": ["CM", "CU", "CT"]}}'

    # 通过阿里云 API 为域名 shop.example.com 和 stock.example.com 添加 CM:移动 CU:联通 CT:电信 线路 AAAA 记录解析
    $ %s aliyun -6 -i xxxx -k xxxxx -d '{"example.com": {"shop": ["CM", "CU", "CT"], "stock": ["CM", "CU", "CT"]}}'

    # 从文件中获取域名信息
    $ cat example.json
    {"example.com": {"shop": ["CM", "CU", "CT"], "stock": ["CM", "CU", "CT"]}}
    
    $ %s aliyun -6 -i xxxx -k xxxxx -f example.json

    # 从环境变量中获取域名信息
    $ export DOMAIN_INFO='{"wglee.org": {"shop": ["CM", "CU", "CT"], "stock": ["CM", "CU", "CT"]}}'
    $ %s aliyun -4 -i xxxx -k xxxxx

""" % (sys.argv[0], sys.argv[0], sys.argv[0], sys.argv[0])

def get_optimization_ip(key=None, ip_version="v4"):
    try:
        headers = headers = {"Content-Type": "application/json"}
        data = {"key": key or KEY, "type": ip_version}
        response = requests.post(
            "https://api.hostmonit.com/get_optimization_ip", json=data, headers=headers
        )
        if response.status_code == 200:
            return response.json()
        else:
            logger.error("CHANGE OPTIMIZATION IP ERROR, REQUEST STATUS CODE IS NOT 200")
            return None
    except Exception as e:
        logger.error(f"CHANGE OPTIMIZATION IP ERROR, {str(e)}")
        return None

def change_dns(cloud, domain, sub_domain, record_type, lines, cf_ips, record_num):
    for line in lines:
        ip_list = cf_ips.get(line)
        record_id_list = cloud.get_record(domain=domain, sub_domain=sub_domain, record_type=record_type, line=RECORD_LINE.get(line))
        record_ip_list = [record.value for record in record_id_list]
        if record_id_list:
            for record, ip in zip(record_id_list, random.sample(ip_list, record_num)):
                if ip.get("ip") in record_ip_list:
                    logger.info(f"跳过，记录值存在，域名: {sub_domain}.{domain} 记录: {record_type} 值: {ip.get('ip')} 线路: {RECORD_LINE.get(line)} 记录ID: {record.record_id}")
                    continue
                logger.info(f"更新记录: {sub_domain}.{domain} 记录: {record_type} 值: {ip.get('ip')} 线路: {RECORD_LINE.get(line)} 记录ID: {record.record_id}")
                cloud.change_record(
                    domain=domain, record_id=record.record_id, sub_domain=sub_domain, value=ip.get('ip'), record_type=record_type, line=RECORD_LINE.get(line)
                )
        else:
            for ip in random.sample(ip_list, record_num):
                logger.info(f"创建记录: {sub_domain}.{domain} 记录: {record_type} 值: {ip.get('ip')} 线路: {RECORD_LINE.get(line)}")
                cloud.create_record(
                    domain=domain, sub_domain=sub_domain, value=ip.get('ip'), record_type=record_type, line=RECORD_LINE.get(line)
                )

def validate_json(data: str) -> bool:
    try:
        json.loads(data)
        return True
    except ValueError:
        return False

def validate_file(filename: str) -> bool:
    if not os.path.exists(filename):
        return False
    try:
        json.load(open(filename))
        return True
    except ValueError:
        return False

def parse_args() -> namedtuple:
    parser = argparse.ArgumentParser(
        description="Cloudflare CDN ip 优选",
        epilog=epilog_info,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "dnsserver",
        metavar="dnsserver",
        choices=DNS_API.keys(),
        type=str,
        help=f"选择域名 DNS 服务商，仅支持: {' | '.join(DNS_API.keys())}",
    )
    parser.add_argument(
        "-4",
        dest="v4",
        action="store_true",
        default=False,
        help="优选 IPV4 地址，添加解析记录",
    )
    parser.add_argument(
        "-6",
        dest="v6",
        action="store_true",
        default=False,
        help="优选 IPV6 地址，添加解析记录",
    )
    parser.add_argument(
        "-n",
        "--record-num",
        metavar="",
        dest="record_num",
        type=int,
        default=2,
        help="解析记录条数, 免费套餐相同的子域名相同解析线路最大只支持添加 2 条解析记录",
    )
    parser.add_argument(
        "--ttl",
        metavar="",
        type=int,
        default=600,
        help="解析记录 TTL 值, 免费套餐默认最小值为 600",
    )
    parser.add_argument(
        "-i",
        "--id",
        metavar="",
        dest="secret_id",
        default=os.environ.get("SECRET_ID"),
        help="服务商 API 的凭证的 SecretId, 默认从系统环境变量中获取，变量名: SECRET_ID",
    )
    parser.add_argument(
        "-k",
        "--key",
        metavar="",
        dest="secret_key",
        default=os.environ.get("SECRET_KEY"),
        help="服务商 API 的凭证的 SecretKey, 默认从系统环境变量中获取，变量名: SECRET_KEY",
    )
    parser_domain = parser.add_mutually_exclusive_group(required=False)
    parser_domain.add_argument(
        "-d",
        "--domain",
        metavar="",
        default=os.environ.get("DOMAIN_INFO"),
        help="""
    添加解析记录的域名信息，字符串格式为 Json。不提供时从系统环境变量中获取, 变量名: DOMAIN_INFO
    与 "-f" 选项互斥, Json 格式如下: 
        {"主域名": {"子域名": ["解析线路1", "解析线路2", "..."]}, ....}
    示例：
        {
            "example1.com": {"shop": ["CM", "CU", "CT"], "stock": ["CM", "CU", "CT"]},
            "example2.com": {"shop": ["CM", "CU", "CT"], "stock": ["CM", "CU", "CT"]}
        }
    """,
    )
    parser_domain.add_argument(
        "-f",
        "--domain-file",
        metavar="",
        dest="domain_file",
        default=os.environ.get("DOMAIN_INFO_FILE"),
        help='添加解析记录的域名信息，文件格式 Json, 不提供时从系统环境变量中获取, 变量名: DOMAIN_INFO_FILE\n与 "-d" 选项互斥，文件内容参数参考 "-d" 选项说明',
    )
    args = parser.parse_args()
    if args.domain and not validate_json(args.domain):
        logger.error(f"JSON 域名信息格式不正确: {args.domain}")
        raise SystemExit()
    if args.domain_file and not validate_file(args.domain_file):
        logger.error(f"文件不存在或 JSON 域名信息格式不正确：{args.domain_file}")
        raise SystemExit()
    return args

def main():
    args = parse_args()
    if args.domain:
        DOMAINS = json.loads(args.domain)
    elif args.domain_file:
        DOMAINS = json.load(open(args.domain_file))
    else:
        raise SystemExit("请提供添加解析记录的域名信息")

    cloud = DNS_API.get(args.dnsserver)(args.secret_id, args.secret_key)
    
    if args.v4:
        logger.info("优选 IPV4 地址")
        record_type = "A"
        cfips = get_optimization_ip(ip_version="v4")
        cf_ips = cfips["info"]
        for domain, sub_domains in DOMAINS.items():
            for sub_domain, lines in sub_domains.items():
                change_dns(cloud, domain, sub_domain, record_type, lines, cf_ips, args.record_num)

    if args.v6:
        logger.info("优选 IPV6 地址")
        record_type = "AAAA"
        cfips = get_optimization_ip(ip_version="v6")
        cf_ips = cfips["info"]
        for domain, sub_domains in DOMAINS.items():
            for sub_domain, lines in sub_domains.items():
                change_dns(cloud, domain, sub_domain, record_type, lines, cf_ips, args.record_num)

if __name__ == "__main__":
    main()
