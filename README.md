# Python Library for FNIRSI DPS-150

A pure Python library for controlling the FNIRSI DPS-150 programmable power supply via serial communication. This library provides a clean async/await API for all device operations without any UI dependencies.

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## Features

- **Async/await support** - Non-blocking operations for efficient device control
- **Complete protocol implementation** - Based on the [JavaScript reference implementation](https://github.com/cho45/fnirsi-dps-150)
- **Full device control** - All device features accessible via Python
- **State monitoring** - Real-time state updates with callback support
- **Type hints** - Full type annotations for better IDE support
- **Comprehensive examples** - Jupyter notebook with practical examples

### Supported Features

- ✅ Voltage and current control (0-30V, 0-5A typical)
- ✅ Protection settings (OVP, OCP, OPP, OTP, LVP)
- ✅ Preset groups (6 configurable presets)
- ✅ Energy metering (capacity in Ah, energy in Wh)
- ✅ Device information (model, firmware, hardware versions)
- ✅ Display and audio settings (brightness, volume)
- ✅ Real-time monitoring (voltage, current, power, temperature)

## Installation

### From Source

```bash
git clone <repository-url>
cd DPS-150
pip install -r requirements.txt
```

Or install as a package:

```bash
pip install .
```

### Requirements

- Python 3.9 or higher
- pyserial-asyncio >= 0.6
- pyserial >= 3.5

## Quick Start

### Basic Usage

```python
import asyncio
from dps150 import DPS150

async def main():
    # Connect to device
    async with DPS150(port="/dev/ttyUSB0") as device:  # or "COM3" on Windows
        # Get device information
        info = await device.get_info()
        print(f"Model: {info.model_name}")
        print(f"Firmware: {info.firmware_version}")
        
        # Set voltage and current
        await device.set_voltage(12.0)
        await device.set_current(1.0)
        
        # Enable output
        await device.enable_output()
        
        # Read current state
        state = await device.get_all()
        print(f"Output: {state.output_voltage:.3f}V @ {state.output_current:.3f}A")
        
        # Disable output
        await device.disable_output()

if __name__ == "__main__":
    asyncio.run(main())
```

### Finding Your Serial Port

```python
from dps150 import list_serial_ports

# List all available serial ports
ports = list_serial_ports()
for port in ports:
    print(f"Device: {port['device']}")
    print(f"  Description: {port['description']}")
    print(f"  VID: {port['vid']}, PID: {port['pid']}")
```

## Examples

### Voltage Sweep

```python
import asyncio
from dps150 import DPS150

async def main():
    async with DPS150(port="/dev/ttyUSB0") as device:
        await device.set_current(1.0)  # Set current limit
        await device.enable_output()
        
        # Sweep voltage from 0 to 12V
        for voltage in range(0, 13):
            await device.set_voltage(float(voltage))
            await asyncio.sleep(0.5)  # Wait at each voltage
            state = await device.get_all()
            print(f"{voltage}V: {state.output_voltage:.3f}V, "
                  f"{state.output_current:.3f}A, {state.output_power:.3f}W")
        
        await device.disable_output()

asyncio.run(main())
```

### Setting Protection Limits

```python
import asyncio
from dps150 import DPS150

async def main():
    async with DPS150(port="/dev/ttyUSB0") as device:
        # Set protection limits
        await device.set_ovp(15.0)  # Over-voltage protection at 15V
        await device.set_ocp(2.0)   # Over-current protection at 2A
        await device.set_opp(20.0)  # Over-power protection at 20W
        
        # Verify settings
        state = await device.get_all()
        print(f"OVP: {state.over_voltage_protection:.2f}V")
        print(f"OCP: {state.over_current_protection:.2f}A")
        print(f"OPP: {state.over_power_protection:.2f}W")

asyncio.run(main())
```

### State Monitoring with Callbacks

```python
import asyncio
from dps150 import DPS150

async def main():
    async with DPS150(port="/dev/ttyUSB0") as device:
        # Register callback for state updates
        def on_update(state):
            print(f"V: {state.output_voltage:.3f}V, "
                  f"I: {state.output_current:.3f}A, "
                  f"P: {state.output_power:.3f}W")
            if state.protection_state.value:
                print(f"⚠ Protection: {state.protection_state.value}")
        
        device.on_state_update(on_update)
        
        await device.set_voltage(10.0)
        await device.set_current(1.0)
        await device.enable_output()
        
        # Monitor for 10 seconds
        await asyncio.sleep(10)
        
        await device.disable_output()

asyncio.run(main())
```

### Using Preset Groups

```python
import asyncio
from dps150 import DPS150

async def main():
    async with DPS150(port="/dev/ttyUSB0") as device:
        # Configure preset groups
        await device.set_group(1, 5.0, 0.5)   # Group 1: 5V @ 0.5A
        await device.set_group(2, 12.0, 1.0)  # Group 2: 12V @ 1.0A
        
        # Load and use group 1
        await device.load_group(1)
        await device.enable_output()
        await asyncio.sleep(2)
        
        # Switch to group 2
        await device.load_group(2)
        await asyncio.sleep(2)
        
        await device.disable_output()

asyncio.run(main())
```

## API Reference

### Connection Management

#### `DPS150(port: Optional[str] = None)`

Create a DPS150 device instance.

**Parameters:**
- `port` (str, optional): Serial port path (e.g., `/dev/ttyUSB0` on Linux/Mac, `COM3` on Windows). If `None`, attempts auto-detection.

**Example:**
```python
device = DPS150(port="/dev/ttyUSB0")
```

#### `async connect(port: Optional[str] = None) -> None`

Connect to the device and initialize communication.

**Raises:**
- `DPS150ConnectionError`: If connection fails

#### `async disconnect() -> None`

Disconnect from the device and clean up resources.

#### Context Manager Support

The `DPS150` class supports async context manager for automatic connection management:

```python
async with DPS150(port="/dev/ttyUSB0") as device:
    # Device is automatically connected
    await device.set_voltage(12.0)
# Device is automatically disconnected
```

### Reading Device State

#### `async get_all() -> DeviceState`

Get complete device state including all measurements and settings.

**Returns:**
- `DeviceState`: Complete device state object

#### `async get_voltage() -> float`

Get current output voltage.

**Returns:**
- `float`: Output voltage in volts

#### `async get_current() -> float`

Get current output current.

**Returns:**
- `float`: Output current in amperes

#### `async get_power() -> float`

Get current output power.

**Returns:**
- `float`: Output power in watts

#### `async get_temperature() -> float`

Get device temperature.

**Returns:**
- `float`: Temperature in degrees Celsius

#### `async get_info() -> DeviceInfo`

Get device information (model name, firmware version, hardware version).

**Returns:**
- `DeviceInfo`: Device information object

### Setting Output Values

#### `async set_voltage(value: float) -> None`

Set target output voltage.

**Parameters:**
- `value` (float): Voltage in volts (typically 0-30V)

#### `async set_current(value: float) -> None`

Set target output current (current limit).

**Parameters:**
- `value` (float): Current in amperes (typically 0-5A)

#### `async enable_output() -> None`

Enable the output (turn on power supply).

#### `async disable_output() -> None`

Disable the output (turn off power supply).

### Protection Settings

#### `async set_ovp(value: float) -> None`

Set over-voltage protection threshold.

**Parameters:**
- `value` (float): Voltage threshold in volts

#### `async set_ocp(value: float) -> None`

Set over-current protection threshold.

**Parameters:**
- `value` (float): Current threshold in amperes

#### `async set_opp(value: float) -> None`

Set over-power protection threshold.

**Parameters:**
- `value` (float): Power threshold in watts

#### `async set_otp(value: float) -> None`

Set over-temperature protection threshold.

**Parameters:**
- `value` (float): Temperature threshold in degrees Celsius

#### `async set_lvp(value: float) -> None`

Set low-voltage protection threshold.

**Parameters:**
- `value` (float): Voltage threshold in volts

### Preset Groups

#### `async set_group(group: int, voltage: float, current: float) -> None`

Set preset group values.

**Parameters:**
- `group` (int): Group number (1-6)
- `voltage` (float): Voltage in volts
- `current` (float): Current in amperes

**Raises:**
- `ValueError`: If group number is not 1-6

#### `async load_group(group: int) -> None`

Load preset group values as current settings.

**Parameters:**
- `group` (int): Group number (1-6)

**Raises:**
- `ValueError`: If group number is not 1-6

### Energy Metering

#### `async start_metering() -> None`

Start energy metering (accumulates capacity and energy).

#### `async stop_metering() -> None`

Stop energy metering.

### Display and Audio

#### `async set_brightness(value: int) -> None`

Set display brightness.

**Parameters:**
- `value` (int): Brightness level (0-10)

**Raises:**
- `ValueError`: If value is not 0-10

#### `async set_volume(value: int) -> None`

Set beep volume.

**Parameters:**
- `value` (int): Volume level (0-10)

**Raises:**
- `ValueError`: If value is not 0-10

### State Monitoring

#### `on_state_update(callback: Callable[[DeviceState], None]) -> None`

Register a callback function for state updates. The callback will be called whenever the device state changes.

**Parameters:**
- `callback` (Callable): Function that takes a `DeviceState` parameter

**Example:**
```python
def my_callback(state: DeviceState):
    print(f"Voltage: {state.output_voltage}V")
    print(f"Current: {state.output_current}A")
    if state.protection_state != ProtectionState.NORMAL:
        print(f"⚠ Protection: {state.protection_state.value}")

device.on_state_update(my_callback)
```

## Data Models

### `DeviceState`

Complete device state dataclass containing all measurements and settings.

**Key Fields:**
- `output_voltage` (float): Current output voltage
- `output_current` (float): Current output current
- `output_power` (float): Current output power
- `temperature` (float): Device temperature
- `set_voltage` (float): Set voltage value
- `set_current` (float): Set current value
- `over_voltage_protection` (float): OVP threshold
- `over_current_protection` (float): OCP threshold
- `over_power_protection` (float): OPP threshold
- `output_capacity` (float): Energy capacity in Ah
- `output_energy` (float): Energy in Wh
- `output_closed` (bool): Output enabled/disabled
- `protection_state` (ProtectionState): Current protection state
- `mode` (Mode): Output mode (CC or CV)

### `DeviceInfo`

Device information dataclass.

**Fields:**
- `model_name` (str): Model name
- `hardware_version` (str): Hardware version
- `firmware_version` (str): Firmware version

### `ProtectionState` (Enum)

Protection state enumeration.

**Values:**
- `NORMAL`: Normal operation
- `OVP`: Over Voltage Protection triggered
- `OCP`: Over Current Protection triggered
- `OPP`: Over Power Protection triggered
- `OTP`: Over Temperature Protection triggered
- `LVP`: Low Voltage Protection triggered
- `REP`: Reverse Connection Protection triggered

### `Mode` (Enum)

Output mode enumeration.

**Values:**
- `CC`: Constant Current mode
- `CV`: Constant Voltage mode

## Exceptions

### `DPS150Error`

Base exception for all DPS-150 errors.

### `DPS150ConnectionError`

Raised when there are connection issues with the device.

### `DPS150ProtocolError`

Raised when there are protocol errors (bad checksum, malformed packet, etc.).

### `DPS150TimeoutError`

Raised when a communication timeout occurs.

### `DPS150ProtectionError`

Raised when a protection state is triggered.

**Attributes:**
- `protection_state` (str): The protection state that was triggered

## Protocol Details

The library implements the DPS-150 serial communication protocol:

### Serial Settings

- **Baud Rate**: 115200
- **Data Bits**: 8
- **Stop Bits**: 1
- **Parity**: None
- **Flow Control**: Hardware (RTS/CTS)

### Packet Format

**Outgoing packets:**
```
[0xF1, command, type, length, data..., checksum]
```

**Incoming packets:**
```
[0xF0, command, type, length, data..., checksum]
```

**Checksum calculation:**
```
checksum = (type + length + sum(data_bytes)) % 256
```

**Data encoding:**
- Float values: Little-endian 32-bit IEEE 754 format
- String values: UTF-8 encoded, null-terminated
- Byte values: Single byte (0-255)

### Command Codes

- `0xA1`: GET - Request value from device
- `0xB1`: SET - Set value on device
- `0xC1`: Connection/initialization command

## Project Structure

```
DPS-150/
├── dps150/              # Main package
│   ├── __init__.py      # Package exports
│   ├── device.py        # Main DPS150 class
│   ├── protocol.py      # Packet encoding/decoding
│   ├── transport.py       # Serial communication layer
│   ├── models.py        # Data models (DeviceState, DeviceInfo)
│   ├── constants.py    # Protocol constants
│   ├── exceptions.py   # Custom exceptions
│   └── utils.py        # Utility functions
├── tests/               # Test suite
├── example.ipynb        # Jupyter notebook examples
├── setup.py            # Package setup
├── requirements.txt    # Dependencies
└── README.md           # This file
```

## Testing

Run the test suite:

```bash
pytest
```

For coverage:

```bash
pytest --cov=dps150 --cov-report=html
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details.

## Acknowledgments

This library is based on the JavaScript implementation by [cho45](https://github.com/cho45/fnirsi-dps-150). Special thanks for reverse-engineering the protocol and providing the reference implementation.

## Related Projects

- [JavaScript/WebSerial Implementation](https://github.com/cho45/fnirsi-dps-150) - Original JavaScript implementation
- [FNIRSI DPS-150 Product Page](https://www.fnirsi.com/products/dps-150)

## Support

For issues, questions, or feature requests, please open an issue on GitHub.
