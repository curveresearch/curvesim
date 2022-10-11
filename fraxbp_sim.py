import time

import curvesim

if __name__ == "__main__":
    t = time.time()
    pools = {
        "SUSDFRAXBP3CRV-f": range(50, 850, 50),  # 200 -> 500
        "GUSDFRAXBP3CRV-f": range(50, 2000, 100),  # 200 -> 1500
        "BUSDFRAXBP3CRV-f": range(50, 2000, 100),  # 200 -> 1500
        "TUSDFRAXBP3CRV-f": range(50, 1000, 50),  # 200 - 700
    }
    for poolname, A_list in pools.items():
        res = curvesim.autosim(poolname, ncpu=4, src="nomics", fee=[0.0004], A=A_list)
    for poolname, A_list in pools.items():
        res = curvesim.autosim(
            poolname, ncpu=4, src="nomics", fee=[0.0004], fee_base=0.0001, A=A_list
        )
    elapsed = time.time() - t
    minutes, seconds = divmod(elapsed, 60)
    print(f"Elapsed time: {minutes}m, {seconds}s")
