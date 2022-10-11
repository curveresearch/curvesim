import time

import curvesim

if __name__ == "__main__":
    t = time.time()
    pools = [
        "SUSDFRAXBP3CRV-f",
        "GUSDFRAXBP3CRV-f",
        "BUSDFRAXBP3CRV-f",
        "TUSDFRAXBP3CRV-f",
    ]
    for poolname in pools:
        res = curvesim.autosim(
            poolname,
            ncpu=4,
            src="nomics",
            A=range(100, 1700, 100),
        )
    for poolname in pools:
        res = curvesim.autosim(
            poolname,
            ncpu=4,
            src="nomics",
            fee_base=0.0001,
            A=range(100, 1700, 100),
        )
    elapsed = time.time() - t
    print("Elapsed time:", elapsed)
