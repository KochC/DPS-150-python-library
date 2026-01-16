"""Tests for protocol layer."""

import struct
import pytest

from dps150.protocol import (
    bytes_to_float,
    calculate_checksum,
    decode_packet,
    encode_packet,
    encode_float_packet,
    encode_byte_packet,
    float_to_bytes,
    PacketBuffer,
)
from dps150.constants import HEADER_INPUT, HEADER_OUTPUT, CMD_GET, CMD_SET, VOLTAGE_SET
from dps150.exceptions import DPS150ProtocolError


def test_float_conversion():
    """Test float to bytes and back conversion."""
    value = 12.345
    bytes_data = float_to_bytes(value)
    assert len(bytes_data) == 4
    assert bytes_to_float(bytes_data) == pytest.approx(value, rel=1e-6)


def test_checksum_calculation():
    """Test checksum calculation."""
    data = bytes([0x01, 0x02, 0x03])
    checksum = calculate_checksum(HEADER_OUTPUT, CMD_SET, VOLTAGE_SET, data)
    # type (193) + length (3) + data (1+2+3) = 193 + 3 + 6 = 202
    assert checksum == 202 % 256


def test_encode_packet():
    """Test packet encoding."""
    data = bytes([0x01, 0x02])
    packet = encode_packet(CMD_SET, VOLTAGE_SET, data)
    
    assert len(packet) == 7  # header + command + type + length + data(2) + checksum
    assert packet[0] == HEADER_OUTPUT
    assert packet[1] == CMD_SET
    assert packet[2] == VOLTAGE_SET
    assert packet[3] == 2  # length
    assert packet[4:6] == data
    # Checksum is last byte
    expected_checksum = (VOLTAGE_SET + 2 + 0x01 + 0x02) % 256
    assert packet[6] == expected_checksum


def test_encode_float_packet():
    """Test float packet encoding."""
    value = 5.5
    packet = encode_float_packet(CMD_SET, VOLTAGE_SET, value)
    
    assert len(packet) == 9  # header + command + type + length(4) + float(4) + checksum
    assert packet[0] == HEADER_OUTPUT
    assert packet[1] == CMD_SET
    assert packet[2] == VOLTAGE_SET
    assert packet[3] == 4  # float is 4 bytes
    
    # Verify float data
    float_data = packet[4:8]
    decoded_value = bytes_to_float(float_data)
    assert decoded_value == pytest.approx(value, rel=1e-6)


def test_encode_byte_packet():
    """Test byte packet encoding."""
    value = 5
    packet = encode_byte_packet(CMD_SET, VOLTAGE_SET, value)
    
    assert len(packet) == 6  # header + command + type + length(1) + byte(1) + checksum
    assert packet[0] == HEADER_OUTPUT
    assert packet[1] == CMD_SET
    assert packet[2] == VOLTAGE_SET
    assert packet[3] == 1
    assert packet[4] == value


def test_decode_packet():
    """Test packet decoding."""
    # Create a valid packet
    data = bytes([0x01, 0x02])
    packet = encode_packet(CMD_GET, VOLTAGE_SET, data)
    
    # Change header to input
    packet = bytes([HEADER_INPUT]) + packet[1:]
    
    command, type_code, length, decoded_data = decode_packet(packet)
    
    assert command == CMD_GET
    assert type_code == VOLTAGE_SET
    assert length == 2
    assert decoded_data == data


def test_decode_packet_invalid_header():
    """Test decoding with invalid header."""
    packet = bytes([0xFF, CMD_GET, VOLTAGE_SET, 0, 0])
    
    with pytest.raises(DPS150ProtocolError, match="Invalid header"):
        decode_packet(packet)


def test_decode_packet_incomplete():
    """Test decoding incomplete packet."""
    # Create a packet that has minimum length but length byte indicates more data
    # Length byte says 5, so we need 5+5=10 bytes total, but only provide 8
    packet = bytes([HEADER_INPUT, CMD_GET, VOLTAGE_SET, 5, 0x01, 0x02, 0x03])  # Missing data and checksum
    
    with pytest.raises(DPS150ProtocolError, match="Packet incomplete"):
        decode_packet(packet)


def test_decode_packet_bad_checksum():
    """Test decoding packet with bad checksum."""
    packet = bytes([HEADER_INPUT, CMD_GET, VOLTAGE_SET, 2, 0x01, 0x02, 0xFF])  # Wrong checksum
    
    with pytest.raises(DPS150ProtocolError, match="Checksum mismatch"):
        decode_packet(packet)


def test_packet_buffer():
    """Test packet buffer."""
    buffer = PacketBuffer()
    
    # Add partial packet
    partial = bytes([HEADER_INPUT, CMD_GET, VOLTAGE_SET, 2, 0x01])
    buffer.append(partial)
    packets = buffer.extract_packets()
    assert len(packets) == 0  # Incomplete
    
    # Complete the packet
    complete = bytes([0x02])
    buffer.append(complete)
    # Calculate checksum
    checksum = (VOLTAGE_SET + 2 + 0x01 + 0x02) % 256
    buffer.append(bytes([checksum]))
    
    packets = buffer.extract_packets()
    assert len(packets) == 1
    assert len(packets[0]) == 7  # Complete packet


def test_packet_buffer_multiple():
    """Test buffer with multiple packets."""
    buffer = PacketBuffer()
    
    # Create two complete packets
    data1 = bytes([0x01])
    packet1 = encode_packet(CMD_GET, VOLTAGE_SET, data1)
    packet1 = bytes([HEADER_INPUT]) + packet1[1:]
    
    data2 = bytes([0x02])
    packet2 = encode_packet(CMD_GET, VOLTAGE_SET, data2)
    packet2 = bytes([HEADER_INPUT]) + packet2[1:]
    
    # Add both
    buffer.append(packet1 + packet2)
    packets = buffer.extract_packets()
    
    assert len(packets) == 2
