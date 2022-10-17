#!/usr/bin/env python3

import json
import sys

sys.path.insert(0, ".")
import curvesim  # noqa

json_data = sys.stdin.read()
pool_settings = json.loads(json_data)

poolname = pool_settings["poolname"]
chain = pool_settings["chain"]
test = pool_settings.get("test", False)

res = curvesim.autosim(poolname, chain=chain, ncpu=4, test=test)
