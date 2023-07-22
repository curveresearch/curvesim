#!/usr/bin/env python3

import configparser
import json
import os

SECTION_HEADING = "[SETTINGS]"


def get_int_or_int_list(int_string):
    """
    Convert stringified comma-separated list of ints
    to an actual list of ints (or just a single int)
    """
    if not int_string:
        return None

    int_list = [x.strip() for x in int_string.split(",")]

    if int_list[-1] == "":
        int_list = int_list[:-1]

    int_list = [int(x) for x in int_list]
    if len(int_list) == 1:
        return int_list[0]

    return int_list


body = os.getenv("BODY")
if not body:
    raise Exception("BODY env var is not populated.")

body = body.replace(r"\r", "\r").replace(r"\n", "\n")

parts = body.split(SECTION_HEADING)
if len(parts) != 2:
    raise Exception("Need exactly one section heading.")
config_string = SECTION_HEADING + parts[1]

config = configparser.ConfigParser()
config.read_string(config_string)

pool_settings = config[SECTION_HEADING.strip("][")]
pool_address = pool_settings.get("address")
chain = pool_settings.get("chain", "mainnet")
test = pool_settings.getboolean("test", False)
A = pool_settings.get("A")
A = get_int_or_int_list(A)
fee = pool_settings.get("fee")
fee = get_int_or_int_list(fee)
vol_mult = pool_settings.getfloat("vol_mult", None)  # only handle float for now
vol_mode = pool_settings.getint("vol_mode", 1)

settings_dict = {
    "pool_address": pool_address,
    "chain": chain,
    "test": test,
    "A": A,
    "fee": fee,
    "vol_mult": vol_mult,
    "vol_mode": vol_mode,
}

print(json.dumps(settings_dict))
