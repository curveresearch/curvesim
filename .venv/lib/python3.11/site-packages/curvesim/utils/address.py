"""
Utility functions for working with EVM-like account addresses.

This module provides custom versions of common address operations to ensure
standard handling of EVM addresses.
"""
__all__ = ["to_address", "is_address", "Address"]

from typing import NewType

from eth_typing import ChecksumAddress
from eth_utils import is_checksum_address, is_normalized_address, to_checksum_address

Address = NewType("Address", str)


def to_address(address_string: str) -> Address:
    """
    Convert given string to an EVM-like checksum address.

    Parameters
    ----------
    address_string: str
        string to convert to checksum address.

    Raises
    ------
    ValueError
        string cannot be coerced to a checksum address
    """
    checksum_address: ChecksumAddress = to_checksum_address(address_string)
    return Address(checksum_address)


def is_address(address_string: str, checksum=True) -> bool:
    """
    Check if given string is properly formatted as an
    EVM-like address, optionally as a checksum address.

    Parameters
    ----------
    address_string: str
        string to check for proper address formatting
    checksum: bool, default=True
        verify it is properly checksummed
    """
    if checksum:  # pylint: disable=no-else-return
        return is_checksum_address(address_string)
    else:
        return is_normalized_address(address_string)
