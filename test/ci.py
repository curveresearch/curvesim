import os
import pickle

import numpy as np

import CurveSim

if __name__ == "__main__":
    data_dir = os.path.join("test", "data")
    pool_names = ["3pool", "aave", "frax", "mim"]

    for pool_name in pool_names:
        with open(os.path.join(data_dir, f"{pool_name}-pooldata.pickle"), "rb") as f:
            pool_data = pickle.load(f)

        res = CurveSim.autosim(
            pool_name,
            test=True,
            ncpu=1,
            src="local",
            data_dir=data_dir,
            pool_data=pool_data,
        )

        with open(os.path.join(data_dir, f"{pool_name}-res.pickle"), "rb") as f:
            res_pkl = pickle.load(f)

        for (key, df1) in res.items():
            df2 = res_pkl[key]
            if len(df1) != len(df2):
                raise AssertionError(f"Different dataframe lengths for key: {key}")
            for i in df1:
                if len(df1[i]) != len(df2[i]):
                    raise AssertionError(f"Different row lengths for row: {i}")
                assert all(
                    np.isclose(df1[i], df2[i], atol=1e-11, rtol=0)
                ), f"mismatch in key: {key}, row: {i}"
