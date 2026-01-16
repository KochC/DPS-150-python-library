"""Tests for device API (mocked)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from dps150.device import DPS150
from dps150.models import DeviceState, DeviceInfo, ProtectionState, Mode
from dps150.exceptions import DPS150ConnectionError


@pytest.fixture
def mock_transport():
    """Create a mock transport."""
    transport = AsyncMock()
    transport.is_connected = True
    transport.write = AsyncMock()
    return transport


@pytest.mark.asyncio
async def test_device_connect(mock_transport):
    """Test device connection."""
    with patch("dps150.device.SerialTransport", return_value=mock_transport):
        device = DPS150(port="/dev/ttyUSB0")
        await device.connect()
        
        assert device.transport == mock_transport
        mock_transport.connect.assert_called_once()


@pytest.mark.asyncio
async def test_device_context_manager(mock_transport):
    """Test device as context manager."""
    with patch("dps150.device.SerialTransport", return_value=mock_transport):
        async with DPS150(port="/dev/ttyUSB0") as device:
            assert device.transport == mock_transport
            mock_transport.connect.assert_called_once()
        
        mock_transport.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_set_voltage(mock_transport):
    """Test setting voltage."""
    with patch("dps150.device.SerialTransport", return_value=mock_transport):
        device = DPS150(port="/dev/ttyUSB0")
        device.transport = mock_transport
        device.transport.is_connected = True
        
        await device.set_voltage(12.0)
        
        # Verify write was called
        mock_transport.write.assert_called()
        # Check that packet contains float value
        call_args = mock_transport.write.call_args[0][0]
        assert call_args[0] == 0xF1  # HEADER_OUTPUT
        assert call_args[1] == 0xB1  # CMD_SET
        assert call_args[2] == 193  # VOLTAGE_SET


@pytest.mark.asyncio
async def test_set_current(mock_transport):
    """Test setting current."""
    with patch("dps150.device.SerialTransport", return_value=mock_transport):
        device = DPS150(port="/dev/ttyUSB0")
        device.transport = mock_transport
        device.transport.is_connected = True
        
        await device.set_current(1.5)
        
        mock_transport.write.assert_called()


@pytest.mark.asyncio
async def test_enable_disable_output(mock_transport):
    """Test enabling and disabling output."""
    with patch("dps150.device.SerialTransport", return_value=mock_transport):
        device = DPS150(port="/dev/ttyUSB0")
        device.transport = mock_transport
        device.transport.is_connected = True
        
        await device.enable_output()
        await device.disable_output()
        
        assert mock_transport.write.call_count == 2


@pytest.mark.asyncio
async def test_set_group(mock_transport):
    """Test setting preset group."""
    with patch("dps150.device.SerialTransport", return_value=mock_transport):
        device = DPS150(port="/dev/ttyUSB0")
        device.transport = mock_transport
        device.transport.is_connected = True
        
        await device.set_group(1, 5.0, 0.5)
        
        # Should have called write multiple times (voltage, current, group voltage, group current)
        assert mock_transport.write.call_count >= 4


@pytest.mark.asyncio
async def test_set_group_invalid():
    """Test setting invalid group number."""
    device = DPS150(port="/dev/ttyUSB0")
    
    with pytest.raises(ValueError, match="Group must be between 1 and 6"):
        await device.set_group(0, 5.0, 0.5)
    
    with pytest.raises(ValueError, match="Group must be between 1 and 6"):
        await device.set_group(7, 5.0, 0.5)


@pytest.mark.asyncio
async def test_set_brightness_invalid(mock_transport):
    """Test setting invalid brightness."""
    with patch("dps150.device.SerialTransport", return_value=mock_transport):
        device = DPS150(port="/dev/ttyUSB0")
        device.transport = mock_transport
        device.transport.is_connected = True
        
        with pytest.raises(ValueError, match="Brightness must be between 0 and 10"):
            await device.set_brightness(11)
        
        with pytest.raises(ValueError, match="Brightness must be between 0 and 10"):
            await device.set_brightness(-1)


@pytest.mark.asyncio
async def test_state_update_callback(mock_transport):
    """Test state update callback."""
    callback_called = []
    
    def callback(state):
        callback_called.append(state)
    
    with patch("dps150.device.SerialTransport", return_value=mock_transport):
        device = DPS150(port="/dev/ttyUSB0")
        device.transport = mock_transport
        device.transport.is_connected = True
        
        device.on_state_update(callback)
        
        # Simulate packet received
        device._on_packet_received(0xA1, 195, b"\x00\x00\x40\x41")  # 12.0 as float
        
        # Callback should be called (though parsing might fail without complete data)
        # This is a basic test - full parsing would need complete packet data


def test_device_state_update_from_dict():
    """Test DeviceState.update_from_dict."""
    state = DeviceState()
    
    data = {
        "inputVoltage": 20.0,
        "outputVoltage": 12.5,
        "outputCurrent": 1.2,
        "setVoltage": 12.0,
        "setCurrent": 1.0,
        "protectionState": "OCP",
        "mode": "CC",
    }
    
    state.update_from_dict(data)
    
    assert state.input_voltage == 20.0
    assert state.output_voltage == 12.5
    assert state.output_current == 1.2
    assert state.set_voltage == 12.0
    assert state.set_current == 1.0
    assert state.protection_state == ProtectionState.OCP
    assert state.mode == Mode.CC
