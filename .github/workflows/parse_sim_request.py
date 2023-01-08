#!/usr/bin/env python3

# need to parse out (for now):
# - poolname: actually LP token name or pool address
# - chain, default to "mainnet"
# other param choices may be allowed in the future

import configparser
import json
import os

SECTION_HEADING = "[SETTINGS]"

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
poolname = pool_settings.get("address") or pool_settings.get("symbol")
chain = pool_settings.get("chain", "mainnet")
test = pool_settings.getboolean("test", False)
vol_mult = pool_settings.getfloat("vol_mult", None)  # only handle float for now
vol_mode = pool_settings.getint("vol_mode", 1)

settings_dict = {
    "poolname": poolname,
    "chain": chain,
    "test": test,
    "vol_mult": vol_mult,
    "vol_mode": vol_mode,
}

print(json.dumps(settings_dict))
