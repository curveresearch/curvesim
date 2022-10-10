import time

import curvesim

if __name__ == "__main__":
    t = time.time()
    # res = curvesim.autosim("3pool", test=True, ncpu=1)
    # res = curvesim.autosim(
    #     "crvFRAX", fee=[0.0001, 0.0002, 0.0003, 0.0004, 0.0005], ncpu=4
    # )
    res = curvesim.autosim("GUSDFRAXBP3CRV-f", ncpu=4)
    # res = curvesim.autosim("SUSDFRAXBP3CRV-f", ncpu=4, src="nomics")
    elapsed = time.time() - t
    print("Elapsed time:", elapsed)
