"""Custom exceptions for DPS-150 library.

This module defines a hierarchy of custom exceptions for better error
handling and debugging. All exceptions inherit from DPS150Error.
"""



class DPS150Error(Exception):
    """Base exception for all DPS-150 errors."""
    pass


class DPS150ConnectionError(DPS150Error):
    """Raised when there are connection issues with the device."""
    pass


class DPS150ProtocolError(DPS150Error):
    """Raised when there are protocol errors (bad checksum, malformed packet, etc.)."""
    pass


class DPS150TimeoutError(DPS150Error):
    """Raised when a communication timeout occurs."""
    pass


class DPS150ProtectionError(DPS150Error):
    """Raised when a protection state is triggered."""
    def __init__(self, message: str, protection_state: str):
        super().__init__(message)
        self.protection_state = protection_state
