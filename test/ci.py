import os
import pickle

import numpy as np

import CurveSim

if __name__ == "__main__":
    data_dir = os.path.join("test", "data")
    pool_names = ["3pool", "aave", "frax", "mim"]

    tolerances = {
        "ar": 1e-11,
        "bal": 1e-11,
        "depth": 1e-11,
        "err": 1e-11,
        "log_returns": 1e-11,
        "p": 1e5,
        "pool_value": 1e-11,
        "volume": 1e-11,
        "x": 1e12,
    }

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

            tol = tolerances[key]

            if key not in ["p", "x"]:
                for i in df1:
                    if len(df1[i]) != len(df2[i]):
                        raise AssertionError(f"Different row lengths for row: {i}")
                    assert all(
                        np.isclose(df1[i], df2[i], atol=tol, rtol=0)
                    ), f"mismatch in key: {key}, row: {i}"
            else:
                for i in df1:
                    if len(df1[i]) != len(df2[i]):
                        raise AssertionError(f"Different row lengths for row: {i}")
                    for (array1, array2) in zip(df1[i], df2[i]):
                        array1 = np.array(array1, dtype=float)
                        array2 = np.array(array2, dtype=float)
                        if len(array1) != len(array2):
                            raise AssertionError(f"Different array lengths for row: {i}")
                        assert all(
                            np.isclose(array1, array2, atol=tol, rtol=0)
                        ), f"mismatch in key: {key}, row: {i}"
