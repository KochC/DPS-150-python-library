"""Main DPS150 device class with high-level API.

This module provides the high-level API for controlling the DPS-150
power supply. It handles:
- Device connection and initialization
- Command encoding and sending
- Response parsing and state management
- Callback-based state monitoring
- All device operations (voltage, current, protection, etc.)
"""


import asyncio
import struct
from typing import Callable, List, Optional

from .constants import (
    ALL,
    BAUD_RATE_OPTIONS,
    BRIGHTNESS,
    CMD_GET,
    CMD_SET,
    CMD_XXX_176,
    CMD_XXX_193,
    CURRENT_SET,
    FIRMWARE_VERSION,
    GROUP1_CURRENT_SET,
    GROUP1_VOLTAGE_SET,
    HARDWARE_VERSION,
    INPUT_VOLTAGE,
    LVP,
    METERING_ENABLE,
    MODEL_NAME,
    MODE,
    OCP,
    OPP,
    OTP,
    OUTPUT_CAPACITY,
    OUTPUT_ENERGY,
    OUTPUT_ENABLE,
    OUTPUT_VOLTAGE_CURRENT_POWER,
    OVP,
    PROTECTION_STATE,
    PROTECTION_STATES,
    TEMPERATURE,
    UPPER_LIMIT_CURRENT,
    UPPER_LIMIT_VOLTAGE,
    VOLUME,
    VOLTAGE_SET,
)
from .exceptions import DPS150ConnectionError, DPS150ProtectionError
from .models import DeviceInfo, DeviceState, Mode, ProtectionState
from .protocol import bytes_to_float, encode_packet
from .transport import SerialTransport
from .utils import find_dps150_port, list_serial_ports


class DPS150:
    """Main class for controlling FNIRSI DPS-150 power supply."""
    
    def __init__(self, port: Optional[str] = None):
        """Initialize DPS150 device.
        
        Args:
            port: Serial port path. If None, will attempt auto-detection.
        """
        self.port = port
        self.transport: Optional[SerialTransport] = None
        self.state = DeviceState()
        self.info = DeviceInfo()
        self._callbacks: List[Callable[[DeviceState], None]] = []
        self._polling_task: Optional[asyncio.Task] = None
        self._polling_interval = 1.0  # seconds
        self._lock = asyncio.Lock()
    
    async def connect(self, port: Optional[str] = None) -> None:
        """Connect to the device.
        
        Args:
            port: Serial port path. If None, uses port from __init__ or auto-detection.
        
        Raises:
            DPS150ConnectionError: If connection fails
        """
        if self.transport and self.transport.is_connected:
            return
        
        # Determine port
        if port:
            self.port = port
        elif not self.port:
            self.port = find_dps150_port()
            if not self.port:
                # List available ports for user
                ports = list_serial_ports()
                raise DPS150ConnectionError(
                    f"No DPS-150 port found. Available ports: {[p['device'] for p in ports]}"
                )
        
        # Create and connect transport
        self.transport = SerialTransport(self.port, callback=self._on_packet_received)
        await self.transport.connect()
        
        # Initialize device
        await self._init_device()
    
    async def disconnect(self) -> None:
        """Disconnect from the device."""
        # Stop polling
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
            self._polling_task = None
        
        # Send disconnect command
        if self.transport and self.transport.is_connected:
            try:
                await self._send_command(CMD_XXX_193, 0, bytes([0]))
            except Exception:
                pass
        
        # Disconnect transport
        if self.transport:
            await self.transport.disconnect()
            self.transport = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
    
    async def _init_device(self) -> None:
        """Initialize device after connection.
        
        Performs the initialization sequence required by the DPS-150:
        1. Send connection command (0xC1)
        2. Set baud rate to 115200
        3. Request device information (model, hardware, firmware versions)
        4. Get complete device state
        
        The delays between commands are necessary to allow the device
        time to process each command and respond.
        """
        # Step 1: Send connection/initialization command
        # Command 0xC1 with value 1 initiates the connection
        await self._send_command(CMD_XXX_193, 0, bytes([1]))
        await asyncio.sleep(0.2)  # Wait for device to process
        
        # Step 2: Set baud rate to 115200
        # Baud rate is specified as an index (1-5) in the BAUD_RATE_OPTIONS list
        # 115200 is at index 4, so we send index + 1 = 5
        baud_index = BAUD_RATE_OPTIONS.index(115200) + 1
        await self._send_command(CMD_XXX_176, 0, bytes([baud_index]))
        await asyncio.sleep(0.2)  # Wait for device to process
        
        # Step 3: Request device information
        # These commands request model name, hardware version, and firmware version
        # Responses will be received asynchronously and parsed by _on_packet_received
        await self._send_command(CMD_GET, MODEL_NAME, b"")
        await asyncio.sleep(0.3)  # Wait for response
        
        await self._send_command(CMD_GET, HARDWARE_VERSION, b"")
        await asyncio.sleep(0.3)  # Wait for response
        
        await self._send_command(CMD_GET, FIRMWARE_VERSION, b"")
        await asyncio.sleep(0.3)  # Wait for response
        
        # Step 4: Get complete device state
        # This populates the DeviceState object with all current values
        await self.get_all()
        await asyncio.sleep(0.2)  # Wait for response
    
    async def _send_command(self, command: int, type_code: int, data: bytes) -> None:
        """Send a command to the device.
        
        Encodes the command into a packet and sends it via the transport layer.
        Uses a lock to ensure commands are sent sequentially and not interleaved.
        
        Args:
            command: Command code (e.g., CMD_GET=0xA1, CMD_SET=0xB1)
            type_code: Type code indicating what parameter to get/set
            data: Data bytes to send (empty for GET commands, encoded value for SET)
        
        Raises:
            DPS150ConnectionError: If not connected to device
        """
        if not self.transport or not self.transport.is_connected:
            raise DPS150ConnectionError("Not connected")
        
        packet = encode_packet(command, type_code, data)
        async with self._lock:
            await self.transport.write(packet)
    
    def _on_packet_received(self, command: int, type_code: int, data: bytes) -> None:
        """Handle received packet from device.
        
        This callback is invoked by the transport layer whenever a complete
        packet is received and decoded. It parses the packet data and updates
        the device state and information objects.
        
        Args:
            command: Command code from the packet (usually 0xA1 for GET responses)
            type_code: Type code indicating what data this packet contains
            data: Raw data bytes from the packet (already checksum-verified)
        """
        try:
            parsed_data = self._parse_packet_data(type_code, data)
            if parsed_data:
                # Update state
                self.state.update_from_dict(parsed_data)
                
                # Update info if applicable
                if "modelName" in parsed_data:
                    self.info.model_name = parsed_data["modelName"]
                if "hardwareVersion" in parsed_data:
                    self.info.hardware_version = parsed_data["hardwareVersion"]
                if "firmwareVersion" in parsed_data:
                    self.info.firmware_version = parsed_data["firmwareVersion"]
                
                # Invoke callbacks
                for callback in self._callbacks:
                    try:
                        callback(self.state)
                    except Exception:
                        # Don't let callback errors break the system
                        pass
        except Exception:
            # Ignore parsing errors
            pass
    
    def _parse_packet_data(self, type_code: int, data: bytes) -> Optional[dict]:
        """Parse packet data based on type code.
        
        This method handles parsing of different packet types received from the device.
        Each type code corresponds to a specific data format:
        - Float values: 4 bytes, little-endian IEEE 754
        - Byte values: Single byte (0-255)
        - String values: UTF-8 encoded, null-terminated
        - Combined values: Multiple floats concatenated (e.g., voltage+current+power)
        
        Args:
            type_code: Type code from the packet (determines data format)
            data: Raw data bytes from the packet
        
        Returns:
            Dictionary with parsed data (keys match DeviceState field names) or None if type not recognized
        """
        if len(data) == 0:
            return None
        
        result = {}
        
        try:
            if type_code == INPUT_VOLTAGE:
                result["inputVoltage"] = bytes_to_float(data)
            
            elif type_code == OUTPUT_VOLTAGE_CURRENT_POWER:
                # This packet contains three float values: voltage, current, and power
                # Each float is 4 bytes, so we need at least 12 bytes total
                if len(data) >= 12:
                    result["outputVoltage"] = bytes_to_float(data[0:4])   # Bytes 0-3: voltage
                    result["outputCurrent"] = bytes_to_float(data[4:8])   # Bytes 4-7: current
                    result["outputPower"] = bytes_to_float(data[8:12])    # Bytes 8-11: power
            
            elif type_code == TEMPERATURE:
                result["temperature"] = bytes_to_float(data)
            
            elif type_code == OUTPUT_CAPACITY:
                result["outputCapacity"] = bytes_to_float(data)
            
            elif type_code == OUTPUT_ENERGY:
                result["outputEnergy"] = bytes_to_float(data)
            
            elif type_code == OUTPUT_ENABLE:
                # Output enable is a single byte: 0 = disabled, 1 = enabled
                # Note: "outputClosed" means output is closed/enabled (confusing naming from JS)
                result["outputClosed"] = data[0] == 1
            
            elif type_code == PROTECTION_STATE:
                # Protection state is a single byte index into PROTECTION_STATES array
                # 0 = Normal, 1 = OVP, 2 = OCP, 3 = OPP, 4 = OTP, 5 = LVP, 6 = REP
                state_index = data[0] if len(data) > 0 else 0
                if 0 <= state_index < len(PROTECTION_STATES):
                    result["protectionState"] = PROTECTION_STATES[state_index]
            
            elif type_code == MODE:
                # Mode is a single byte: 0 = Constant Current (CC), 1 = Constant Voltage (CV)
                result["mode"] = "CC" if (data[0] == 0) else "CV"
            
            elif type_code == MODEL_NAME:
                # Decode string, remove null bytes and whitespace
                result["modelName"] = data.decode("utf-8", errors="ignore").rstrip("\x00").strip()
            
            elif type_code == HARDWARE_VERSION:
                # Decode string, remove null bytes and whitespace
                result["hardwareVersion"] = data.decode("utf-8", errors="ignore").rstrip("\x00").strip()
            
            elif type_code == FIRMWARE_VERSION:
                # Decode string, remove null bytes and whitespace
                result["firmwareVersion"] = data.decode("utf-8", errors="ignore").rstrip("\x00").strip()
            
            elif type_code == UPPER_LIMIT_VOLTAGE:
                result["upperLimitVoltage"] = bytes_to_float(data)
            
            elif type_code == UPPER_LIMIT_CURRENT:
                result["upperLimitCurrent"] = bytes_to_float(data)
            
            elif type_code == ALL:
                # Parse complete state (type 255)
                # This is a special packet containing all device state in one response
                # Format: Multiple 4-byte floats followed by single-byte values
                # Byte offsets are based on the JavaScript implementation
                if len(data) >= 139:  # Minimum expected length for complete state packet
                    view = data
                    # Parse all device state from the combined packet
                    # Byte offsets are based on the JavaScript implementation
                    # Each float is 4 bytes, single bytes are 1 byte
                    result = {
                        # Measurements (floats, 4 bytes each)
                        "inputVoltage": bytes_to_float(view[0:4]),           # Bytes 0-3
                        "setVoltage": bytes_to_float(view[4:8]),             # Bytes 4-7
                        "setCurrent": bytes_to_float(view[8:12]),            # Bytes 8-11
                        "outputVoltage": bytes_to_float(view[12:16]),        # Bytes 12-15
                        "outputCurrent": bytes_to_float(view[16:20]),        # Bytes 16-19
                        "outputPower": bytes_to_float(view[20:24]),          # Bytes 20-23
                        "temperature": bytes_to_float(view[24:28]),         # Bytes 24-27
                        
                        # Group presets (floats, 4 bytes each, groups 1-6)
                        "group1setVoltage": bytes_to_float(view[28:32]),     # Bytes 28-31
                        "group1setCurrent": bytes_to_float(view[32:36]),     # Bytes 32-35
                        "group2setVoltage": bytes_to_float(view[36:40]),     # Bytes 36-39
                        "group2setCurrent": bytes_to_float(view[40:44]),     # Bytes 40-43
                        "group3setVoltage": bytes_to_float(view[44:48]),     # Bytes 44-47
                        "group3setCurrent": bytes_to_float(view[48:52]),     # Bytes 48-51
                        "group4setVoltage": bytes_to_float(view[52:56]),     # Bytes 52-55
                        "group4setCurrent": bytes_to_float(view[56:60]),     # Bytes 56-59
                        "group5setVoltage": bytes_to_float(view[60:64]),     # Bytes 60-63
                        "group5setCurrent": bytes_to_float(view[64:68]),     # Bytes 64-67
                        "group6setVoltage": bytes_to_float(view[68:72]),     # Bytes 68-71
                        "group6setCurrent": bytes_to_float(view[72:76]),     # Bytes 72-75
                        
                        # Protection settings (floats, 4 bytes each)
                        "overVoltageProtection": bytes_to_float(view[76:80]),      # Bytes 76-79
                        "overCurrentProtection": bytes_to_float(view[80:84]),      # Bytes 80-83
                        "overPowerProtection": bytes_to_float(view[84:88]),        # Bytes 84-87
                        "overTemperatureProtection": bytes_to_float(view[88:92]),   # Bytes 88-91
                        "lowVoltageProtection": bytes_to_float(view[92:96]),        # Bytes 92-95
                        
                        # Display and audio (single bytes)
                        "brightness": view[96] if len(view) > 96 else 0,          # Byte 96
                        "volume": view[97] if len(view) > 97 else 0,              # Byte 97
                        "meteringClosed": view[98] == 0 if len(view) > 98 else False,  # Byte 98 (0=open, 1=closed)
                        
                        # Energy metering (floats, 4 bytes each)
                        "outputCapacity": bytes_to_float(view[99:103]) if len(view) > 102 else 0.0,  # Bytes 99-102 (Ah)
                        "outputEnergy": bytes_to_float(view[103:107]) if len(view) > 106 else 0.0,    # Bytes 103-106 (Wh)
                        
                        # Status (single bytes)
                        "outputClosed": view[107] == 1 if len(view) > 107 else False,  # Byte 107 (0=off, 1=on)
                        "protectionState": PROTECTION_STATES[view[108]] if len(view) > 108 and 0 <= view[108] < len(PROTECTION_STATES) else "",  # Byte 108
                        "mode": "CC" if (len(view) > 109 and view[109] == 0) else "CV",  # Byte 109 (0=CC, 1=CV)
                        
                        # Limits (floats, 4 bytes each)
                        # Note: Byte 110 is unknown/unused
                        "upperLimitVoltage": bytes_to_float(view[111:115]) if len(view) > 114 else 0.0,  # Bytes 111-114
                        "upperLimitCurrent": bytes_to_float(view[115:119]) if len(view) > 118 else 0.0, # Bytes 115-118
                    }
        
        except (IndexError, struct.error, ValueError) as e:
            # Parsing error, return None
            return None
        
        return result if result else None
    
    # Reading methods
    
    async def get_all(self) -> DeviceState:
        """Get complete device state.
        
        Returns:
            DeviceState object with all current values
        """
        await self._send_command(CMD_GET, ALL, b"")
        await asyncio.sleep(0.1)  # Wait for response
        return self.state
    
    async def get_voltage(self) -> float:
        """Get output voltage.
        
        Returns:
            Output voltage in volts
        """
        await self.get_all()
        return self.state.output_voltage
    
    async def get_current(self) -> float:
        """Get output current.
        
        Returns:
            Output current in amperes
        """
        await self.get_all()
        return self.state.output_current
    
    async def get_power(self) -> float:
        """Get output power.
        
        Returns:
            Output power in watts
        """
        await self.get_all()
        return self.state.output_power
    
    async def get_temperature(self) -> float:
        """Get device temperature.
        
        Returns:
            Temperature in degrees Celsius
        """
        await self.get_all()
        return self.state.temperature
    
    async def get_info(self) -> DeviceInfo:
        """Get device information.
        
        Returns:
            DeviceInfo object with model name and versions
        """
        # Request info if not already populated
        if not self.info.model_name:
            await self._send_command(CMD_GET, MODEL_NAME, b"")
            await asyncio.sleep(0.3)  # Wait longer for response
        
        if not self.info.hardware_version:
            await self._send_command(CMD_GET, HARDWARE_VERSION, b"")
            await asyncio.sleep(0.3)  # Wait longer for response
        
        if not self.info.firmware_version:
            await self._send_command(CMD_GET, FIRMWARE_VERSION, b"")
            await asyncio.sleep(0.3)  # Wait longer for response
        
        return self.info
    
    # Writing methods
    
    async def set_voltage(self, value: float) -> None:
        """Set target voltage.
        
        Args:
            value: Voltage in volts
        """
        data = struct.pack("<f", value)
        await self._send_command(CMD_SET, VOLTAGE_SET, data)
    
    async def set_current(self, value: float) -> None:
        """Set target current.
        
        Args:
            value: Current in amperes
        """
        data = struct.pack("<f", value)
        await self._send_command(CMD_SET, CURRENT_SET, data)
    
    async def enable_output(self) -> None:
        """Enable output."""
        await self._send_command(CMD_SET, OUTPUT_ENABLE, bytes([1]))
    
    async def disable_output(self) -> None:
        """Disable output."""
        await self._send_command(CMD_SET, OUTPUT_ENABLE, bytes([0]))
    
    async def set_ovp(self, value: float) -> None:
        """Set over-voltage protection.
        
        Args:
            value: Voltage threshold in volts
        """
        data = struct.pack("<f", value)
        await self._send_command(CMD_SET, OVP, data)
    
    async def set_ocp(self, value: float) -> None:
        """Set over-current protection.
        
        Args:
            value: Current threshold in amperes
        """
        data = struct.pack("<f", value)
        await self._send_command(CMD_SET, OCP, data)
    
    async def set_opp(self, value: float) -> None:
        """Set over-power protection.
        
        Args:
            value: Power threshold in watts
        """
        data = struct.pack("<f", value)
        await self._send_command(CMD_SET, OPP, data)
    
    async def set_otp(self, value: float) -> None:
        """Set over-temperature protection.
        
        Args:
            value: Temperature threshold in degrees Celsius
        """
        data = struct.pack("<f", value)
        await self._send_command(CMD_SET, OTP, data)
    
    async def set_lvp(self, value: float) -> None:
        """Set low-voltage protection.
        
        Args:
            value: Voltage threshold in volts
        """
        data = struct.pack("<f", value)
        await self._send_command(CMD_SET, LVP, data)
    
    async def set_brightness(self, value: int) -> None:
        """Set display brightness.
        
        Args:
            value: Brightness level (0-10)
        """
        if not 0 <= value <= 10:
            raise ValueError("Brightness must be between 0 and 10")
        await self._send_command(CMD_SET, BRIGHTNESS, bytes([value]))
    
    async def set_volume(self, value: int) -> None:
        """Set beep volume.
        
        Args:
            value: Volume level (0-10)
        """
        if not 0 <= value <= 10:
            raise ValueError("Volume must be between 0 and 10")
        await self._send_command(CMD_SET, VOLUME, bytes([value]))
    
    async def start_metering(self) -> None:
        """Start energy metering."""
        await self._send_command(CMD_SET, METERING_ENABLE, bytes([1]))
    
    async def stop_metering(self) -> None:
        """Stop energy metering."""
        await self._send_command(CMD_SET, METERING_ENABLE, bytes([0]))
    
    # Preset methods
    
    async def set_group(self, group: int, voltage: float, current: float) -> None:
        """Set preset group values.
        
        Args:
            group: Group number (1-6)
            voltage: Voltage in volts
            current: Current in amperes
        """
        if not 1 <= group <= 6:
            raise ValueError("Group must be between 1 and 6")
        
        # Calculate type codes
        voltage_type = GROUP1_VOLTAGE_SET + (group - 1) * 2
        current_type = GROUP1_CURRENT_SET + (group - 1) * 2
        
        # Set main voltage/current first
        await self.set_voltage(voltage)
        await self.set_current(current)
        
        # Set group values
        data_v = struct.pack("<f", voltage)
        await self._send_command(CMD_SET, voltage_type, data_v)
        
        data_c = struct.pack("<f", current)
        await self._send_command(CMD_SET, current_type, data_c)
    
    async def load_group(self, group: int) -> None:
        """Load preset group values.
        
        Args:
            group: Group number (1-6)
        """
        if not 1 <= group <= 6:
            raise ValueError("Group must be between 1 and 6")
        
        await self.get_all()
        
        # Get group values from state
        voltage_attr = f"group{group}_set_voltage"
        current_attr = f"group{group}_set_current"
        
        voltage = getattr(self.state, voltage_attr, 0.0)
        current = getattr(self.state, current_attr, 0.0)
        
        # Set as current values
        await self.set_voltage(voltage)
        await self.set_current(current)
    
    # Callback methods
    
    def on_state_update(self, callback: Callable[[DeviceState], None]) -> None:
        """Register a callback for state updates.
        
        Args:
            callback: Function that will be called with DeviceState when state updates
        """
        self._callbacks.append(callback)
        
        # Start polling if not already started
        if not self._polling_task or self._polling_task.done():
            self._polling_task = asyncio.create_task(self._polling_loop())
    
    async def _polling_loop(self) -> None:
        """Background task to periodically poll device state."""
        try:
            while self.transport and self.transport.is_connected:
                try:
                    await self.get_all()
                    await asyncio.sleep(self._polling_interval)
                except asyncio.CancelledError:
                    break
                except Exception:
                    # On error, wait a bit and continue
                    await asyncio.sleep(self._polling_interval)
        except asyncio.CancelledError:
            pass
