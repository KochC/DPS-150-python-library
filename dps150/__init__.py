"""Python library for FNIRSI DPS-150 power supply device.

This package provides a complete Python interface for controlling the
FNIRSI DPS-150 programmable power supply via serial communication.

Main Components:
    - DPS150: Main device class with high-level API
    - DeviceState: Complete device state dataclass
    - DeviceInfo: Device information dataclass
    - ProtectionState: Enum for protection states
    - Mode: Enum for output modes (CC/CV)

Example:
    ```python
    import asyncio
    from dps150 import DPS150
    
    async def main():
        async with DPS150(port="/dev/ttyUSB0") as device:
            await device.set_voltage(12.0)
            await device.set_current(1.0)
            await device.enable_output()
            state = await device.get_all()
            print(f"Output: {state.output_voltage}V @ {state.output_current}A")
    
    asyncio.run(main())
    ```
"""

__version__ = "0.1.0"

from .device import DPS150
from .exceptions import (
    DPS150Error,
    DPS150ConnectionError,
    DPS150ProtocolError,
    DPS150ProtectionError,
    DPS150TimeoutError,
)
from .models import DeviceInfo, DeviceState, Mode, ProtectionState
from .utils import find_dps150_port, list_serial_ports

__all__ = [
    "DPS150",
    "DeviceInfo",
    "DeviceState",
    "Mode",
    "ProtectionState",
    "DPS150Error",
    "DPS150ConnectionError",
    "DPS150ProtocolError",
    "DPS150ProtectionError",
    "DPS150TimeoutError",
    "find_dps150_port",
    "list_serial_ports",
]
