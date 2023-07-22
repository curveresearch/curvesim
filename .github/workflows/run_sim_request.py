#!/usr/bin/env python3

import json
import os
import sys

sys.path.insert(0, ".")
import curvesim  # noqa

json_data = sys.stdin.read()
pool_settings = json.loads(json_data)

pool_address = pool_settings["pool_address"]
chain = pool_settings["chain"]
test = pool_settings["test"]
A = pool_settings["A"]
fee = pool_settings["fee"]
vol_mult = pool_settings["vol_mult"]
vol_mode = pool_settings["vol_mode"]

sim_results = curvesim.autosim(
    pool_address,
    chain=chain,
    test=test,
    A=A,
    fee=fee,
    vol_mult=vol_mult,
    vol_mode=vol_mode,
)


os.makedirs("./results", exist_ok=True)
sim_results.plot(save_as="./results/plots.html")
