import CurveSim

if __name__ == "__main__":
    # res = CurveSim.autosim("3pool", fee=[0.0003, 0.0004], ncpu=1)
    # res = CurveSim.autosim("3pool", fee=[0.0003], ncpu=1)
    res = CurveSim.autosim("3pool", test=True, ncpu=1)
