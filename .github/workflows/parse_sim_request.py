#!/usr/bin/env python3

# need to parse out (for now):
# - poolname: actually LP token name or pool address
# - chain, default to "mainnet"
# other param choices may be allowed in the future

import configparser
import io
import json
import os

SECTION_HEADING = "[SETTINGS]"

body = os.getenv("BODY")
if not body:
    raise Exception("BODY env var is not populated.")

parts = body.split(SECTION_HEADING)
if len(parts) != 2:
    raise Exception("Need exactly one section heading.")
config_string = SECTION_HEADING + "\n" + parts[1]

config = configparser.ConfigParser()
config.read_string(config_string)

pool_settings = config[SECTION_HEADING]
poolname = pool_settings.get("address") or pool_settings.get("symbol")
chain = pool_settings.get("chain", "mainnet")

settings_dict = {"poolname": poolname, "chain": chain}

print(json.dumps(settings_dict))
