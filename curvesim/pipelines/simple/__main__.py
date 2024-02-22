from . import pipeline

if __name__ == "__main__":
    pool_address = "0xbebc44782c7db0a1a60cb6fe97d0b483032ff1c7"
    chain = "mainnet"
    results = pipeline(pool_address, chain=chain, ncpu=1)
