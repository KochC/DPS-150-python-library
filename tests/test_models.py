"""Tests for data models."""

from dps150.models import DeviceState, DeviceInfo, ProtectionState, Mode


def test_device_state():
    """Test DeviceState dataclass."""
    state = DeviceState()
    assert state.output_voltage == 0.0
    assert state.output_current == 0.0
    assert state.protection_state == ProtectionState.NORMAL
    assert state.mode == Mode.CV


def test_device_state_update():
    """Test updating DeviceState from dictionary."""
    state = DeviceState()
    
    data = {
        "outputVoltage": 12.5,
        "outputCurrent": 1.2,
        "outputPower": 15.0,
        "protectionState": "OVP",
        "mode": "CC",
    }
    
    state.update_from_dict(data)
    
    assert state.output_voltage == 12.5
    assert state.output_current == 1.2
    assert state.output_power == 15.0
    assert state.protection_state == ProtectionState.OVP
    assert state.mode == Mode.CC


def test_device_info():
    """Test DeviceInfo dataclass."""
    info = DeviceInfo(
        model_name="DPS-150",
        hardware_version="1.0",
        firmware_version="2.0",
    )
    
    assert info.model_name == "DPS-150"
    assert info.hardware_version == "1.0"
    assert info.firmware_version == "2.0"


def test_protection_state_enum():
    """Test ProtectionState enum."""
    assert ProtectionState.NORMAL.value == ""
    assert ProtectionState.OVP.value == "OVP"
    assert ProtectionState.from_string("OVP") == ProtectionState.OVP
    assert ProtectionState.from_string("UNKNOWN") == ProtectionState.NORMAL


def test_mode_enum():
    """Test Mode enum."""
    assert Mode.CC.value == "CC"
    assert Mode.CV.value == "CV"
