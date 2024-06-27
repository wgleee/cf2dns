from collections import namedtuple

from dateutil import parser


Domain = namedtuple("Domain", ["domain_name", "create_time", "record_count"])
Record = namedtuple(
    "Record",
    [
        "sub_domain",
        "type",
        "value",
        "line",
        "ttl",
        "record_id",
        "create_timestamp",
        "update_timestamp",
    ],
)


def date_to_timestamp(date_time_str: str) -> float:
    date_time = parser.parse(date_time_str)
    return date_time.timestamp()



