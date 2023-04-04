from eth_utils.address import to_checksum_address

from curvesim.exceptions import SubgraphResultError


def symbol_address_query(symbol):
    q = (
        """
        {
          pools(
            where:
              {symbol_starts_with_nocase: "%s"}
          )
          {
            symbol
            address
          }
        }
    """
        % symbol
    )
    return q


def process_symbol_address_result(data):
    if len(data["pools"]) > 1:
        pool_list = "\n\n"
        for pool in data["pools"]:
            pool_list += f"\"{pool['symbol']}\": {pool['address']}\n"

        raise SubgraphResultError(
            "Multiple pools returned for symbol query:" + pool_list
        )

    addr = to_checksum_address(data["pools"][0]["address"])

    return addr
