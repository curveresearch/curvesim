import CurveSim
import time

if __name__ == "__main__":
    t = time.time()
    res = CurveSim.autosim("3pool", test=True, ncpu=1)
    elapsed = time.time() - t
    print("Elapsed time:", elapsed)
