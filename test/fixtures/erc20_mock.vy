# @dev Implementation of ERC-20 token standard.
# @author Takayuki Jimba (@yudetamago)
# https://github.com/ethereum/EIPs/blob/master/EIPS/eip-20.md


NAME: immutable(String[33])  # trigger different codegen
SYMBOL: immutable(String[32])
DECIMALS: immutable(uint8)

# NOTE: By declaring `balanceOf` as public, vyper automatically generates a 'balanceOf()' getter
#       method to allow access to account balances.
#       The _KeyType will become a required parameter for the getter and it will return _ValueType.
#       See: https://vyper.readthedocs.io/en/v0.1.0-beta.8/types.html?highlight=getter#mappings
balanceOf: public(HashMap[address, uint256])
# By declaring `allowance` as public, vyper automatically generates the `allowance()` getter
allowance: public(HashMap[address, HashMap[address, uint256]])
# By declaring `totalSupply` as public, we automatically create the `totalSupply()` getter
totalSupply: public(uint256)
minter: address


@external
def __init__(name: String[32], symbol: String[32], decimals: uint8, supply: uint256):
    NAME = name
    SYMBOL = symbol
    DECIMALS = decimals
    self.balanceOf[msg.sender] = supply
    self.totalSupply = supply


@external
def transfer(_to : address, _value : uint256) -> bool:
    """
    @dev Transfer token for a specified address
    @param _to The address to transfer to.
    @param _value The amount to be transferred.
    """
    return True


@external
def transferFrom(_from : address, _to : address, _value : uint256) -> bool:
    """
     @dev Transfer tokens from one address to another.
     @param _from address The address which you want to send tokens from
     @param _to address The address which you want to transfer to
     @param _value uint256 the amount of tokens to be transferred
    """
    return True


# manually write getters for now; cf. vyper#2903
@external
def name() -> String[33]:
    return NAME


@external
def symbol() -> String[32]:
    return SYMBOL


@external
def decimals() -> uint8:
    return DECIMALS
