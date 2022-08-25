import CurveSim
import time

if __name__ == "__main__":
    # res = CurveSim.autosim("3pool", fee=[0.0003, 0.0004], ncpu=1)
    # res = CurveSim.autosim("3pool", fee=[0.0003], ncpu=1)
    t = time.time()
    res = CurveSim.autosim("3pool", test=True, ncpu=1)
    elapsed = time.time() - t
    print("Elapsed time:", elapsed)
