"""Protocol layer for DPS-150 packet encoding and decoding.

This module handles the low-level protocol details:
- Packet encoding (outgoing commands)
- Packet decoding (incoming responses)
- Checksum calculation and verification
- Float/byte conversion (little-endian)
- Packet buffer management for stream parsing
"""


import struct
from typing import Optional, Tuple

from .constants import HEADER_INPUT, HEADER_OUTPUT
from .exceptions import DPS150ProtocolError


def float_to_bytes(value: float) -> bytes:
    """Convert float to little-endian 32-bit IEEE 754 format."""
    return struct.pack("<f", value)


def bytes_to_float(data: bytes) -> float:
    """Convert little-endian 32-bit IEEE 754 format to float."""
    if len(data) < 4:
        raise DPS150ProtocolError(f"Insufficient data for float: {len(data)} bytes")
    return struct.unpack("<f", data[:4])[0]


def calculate_checksum(header: int, command: int, type_code: int, data: bytes) -> int:
    """Calculate checksum for packet.
    
    The DPS-150 protocol uses a simple checksum: sum of type code, length,
    and all data bytes, modulo 256. Note that the header and command bytes
    are NOT included in the checksum calculation.
    
    Formula: checksum = (type_code + length + sum(data_bytes)) % 256
    
    Args:
        header: Header byte (0xF0 or 0xF1) - not used in calculation
        command: Command byte - not used in calculation
        type_code: Type code byte
        data: Data bytes
    
    Returns:
        Checksum value (0-255)
    """
    length = len(data)
    checksum = type_code + length
    for byte in data:
        checksum += byte
    return checksum % 256


def encode_packet(command: int, type_code: int, data: bytes = b"") -> bytes:
    """Encode a packet for transmission to the device.
    
    Packet format: [0xF1, command, type, length, data..., checksum]
    
    Args:
        command: Command code (e.g., CMD_GET, CMD_SET)
        type_code: Type code (e.g., VOLTAGE_SET, CURRENT_SET)
        data: Data bytes (empty for commands without data)
    
    Returns:
        Complete packet as bytes
    """
    length = len(data)
    packet = bytearray()
    packet.append(HEADER_OUTPUT)
    packet.append(command)
    packet.append(type_code)
    packet.append(length)
    packet.extend(data)
    
    # Calculate checksum: sum of bytes[2] to bytes[n-1] mod 256
    checksum = calculate_checksum(HEADER_OUTPUT, command, type_code, data)
    packet.append(checksum)
    
    return bytes(packet)


def encode_float_packet(command: int, type_code: int, value: float) -> bytes:
    """Encode a packet with a float value.
    
    Args:
        command: Command code (e.g., CMD_SET)
        type_code: Type code (e.g., VOLTAGE_SET)
        value: Float value to encode
    
    Returns:
        Complete packet as bytes
    """
    data = float_to_bytes(value)
    return encode_packet(command, type_code, data)


def encode_byte_packet(command: int, type_code: int, value: int) -> bytes:
    """Encode a packet with a single byte value.
    
    Args:
        command: Command code (e.g., CMD_SET)
        type_code: Type code (e.g., BRIGHTNESS)
        value: Byte value (0-255)
    
    Returns:
        Complete packet as bytes
    """
    if not 0 <= value <= 255:
        raise ValueError(f"Byte value must be 0-255, got {value}")
    return encode_packet(command, type_code, bytes([value]))


def decode_packet(packet: bytes) -> Tuple[int, int, int, bytes]:
    """Decode a packet received from the device.
    
    Packet format: [0xF0, command, type, length, data..., checksum]
    
    Args:
        packet: Raw packet bytes
    
    Returns:
        Tuple of (command, type_code, length, data)
    
    Raises:
        DPS150ProtocolError: If packet is malformed or checksum is invalid
    """
    if len(packet) < 5:
        raise DPS150ProtocolError(f"Packet too short: {len(packet)} bytes (minimum 5)")
    
    if packet[0] != HEADER_INPUT:
        raise DPS150ProtocolError(f"Invalid header: expected 0x{HEADER_INPUT:02X}, got 0x{packet[0]:02X}")
    
    command = packet[1]
    type_code = packet[2]
    length = packet[3]
    
    # Check packet length
    expected_length = 5 + length  # header(1) + command(1) + type(1) + length(1) + data(length) + checksum(1)
    if len(packet) < expected_length:
        raise DPS150ProtocolError(
            f"Packet incomplete: expected {expected_length} bytes, got {len(packet)}"
        )
    
    data = packet[4:4 + length]
    checksum = packet[4 + length]
    
    # Verify checksum
    calculated_checksum = calculate_checksum(HEADER_INPUT, command, type_code, data)
    if checksum != calculated_checksum:
        raise DPS150ProtocolError(
            f"Checksum mismatch: expected 0x{calculated_checksum:02X}, got 0x{checksum:02X}"
        )
    
    return command, type_code, length, data


class PacketBuffer:
    """Buffer for accumulating partial packets from serial stream.
    
    The serial port may deliver data in chunks that don't align with packet
    boundaries. This buffer accumulates incoming data and extracts complete
    packets when they're available, leaving incomplete packets in the buffer
    for the next read cycle.
    """
    
    def __init__(self):
        """Initialize an empty packet buffer."""
        self.buffer = bytearray()
    
    def append(self, data: bytes) -> None:
        """Append new data to buffer.
        
        Args:
            data: Raw bytes received from serial port
        """
        self.buffer.extend(data)
    
    def extract_packets(self) -> list[bytes]:
        """Extract complete packets from buffer.
        
        Scans the buffer for complete packets starting with HEADER_INPUT (0xF0).
        A complete packet has the format:
        [header, command, type, length, data..., checksum]
        where total length = 5 + length (header + command + type + length + data + checksum)
        
        Returns:
            List of complete packet bytes. Incomplete packets remain in buffer
            for the next call.
        """
        packets = []
        i = 0
        
        while i < len(self.buffer) - 5:  # Need at least 5 bytes (header + command + type + length + checksum)
            # Look for start byte
            if self.buffer[i] == HEADER_INPUT:
                # Found potential packet start
                if i + 3 >= len(self.buffer):
                    # Don't have length byte yet
                    break
                
                length = self.buffer[i + 3]
                packet_length = 5 + length  # header + command + type + length + data + checksum
                
                if i + packet_length > len(self.buffer):
                    # Don't have complete packet yet
                    break
                
                # Extract complete packet
                packet = bytes(self.buffer[i:i + packet_length])
                packets.append(packet)
                i += packet_length
            else:
                i += 1
        
        # Remove extracted packets from buffer
        if packets:
            self.buffer = self.buffer[i:]
        
        return packets
    
    def clear(self) -> None:
        """Clear the buffer."""
        self.buffer.clear()
