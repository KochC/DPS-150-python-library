"""Data models for DPS-150 device state.

This module defines the data structures used to represent device state
and information. Uses dataclasses for clean, typed data structures and
enums for protection states and output modes.
"""


from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ProtectionState(Enum):
    """Protection state enumeration."""
    NORMAL = ""
    OVP = "OVP"  # Over Voltage Protection
    OCP = "OCP"  # Over Current Protection
    OPP = "OPP"  # Over Power Protection
    OTP = "OTP"  # Over Temperature Protection
    LVP = "LVP"  # Low Voltage Protection
    REP = "REP"  # Reverse Connection Protection

    @classmethod
    def from_string(cls, value: str) -> "ProtectionState":
        """Create ProtectionState from string value."""
        for state in cls:
            if state.value == value:
                return state
        return cls.NORMAL


class Mode(Enum):
    """Output mode enumeration."""
    CC = "CC"  # Constant Current
    CV = "CV"  # Constant Voltage


@dataclass
class DeviceInfo:
    """Device information."""
    model_name: str = ""
    hardware_version: str = ""
    firmware_version: str = ""


@dataclass
class DeviceState:
    """Complete device state."""
    # Input/Output measurements
    input_voltage: float = 0.0
    output_voltage: float = 0.0
    output_current: float = 0.0
    output_power: float = 0.0
    temperature: float = 0.0

    # Set values
    set_voltage: float = 0.0
    set_current: float = 0.0

    # Group presets (1-6)
    group1_set_voltage: float = 0.0
    group1_set_current: float = 0.0
    group2_set_voltage: float = 0.0
    group2_set_current: float = 0.0
    group3_set_voltage: float = 0.0
    group3_set_current: float = 0.0
    group4_set_voltage: float = 0.0
    group4_set_current: float = 0.0
    group5_set_voltage: float = 0.0
    group5_set_current: float = 0.0
    group6_set_voltage: float = 0.0
    group6_set_current: float = 0.0

    # Protection settings
    over_voltage_protection: float = 0.0
    over_current_protection: float = 0.0
    over_power_protection: float = 0.0
    over_temperature_protection: float = 0.0
    low_voltage_protection: float = 0.0

    # Display and audio
    brightness: int = 0
    volume: int = 0

    # Metering
    metering_closed: bool = False
    output_capacity: float = 0.0  # Ah
    output_energy: float = 0.0  # Wh

    # Status
    output_closed: bool = False  # Output enabled/disabled
    protection_state: ProtectionState = ProtectionState.NORMAL
    mode: Mode = Mode.CV

    # Limits
    upper_limit_voltage: float = 0.0
    upper_limit_current: float = 0.0

    def update_from_dict(self, data: dict) -> None:
        """Update state from dictionary (from parsed packet data).
        
        This method updates the DeviceState fields from a dictionary
        containing parsed packet data. Keys in the dictionary use camelCase
        (matching the JavaScript implementation) and are mapped to
        snake_case Python attributes.
        
        Args:
            data: Dictionary with parsed packet data (keys like "outputVoltage",
                  "setCurrent", "protectionState", etc.)
        """
        if "inputVoltage" in data:
            self.input_voltage = data["inputVoltage"]
        if "outputVoltage" in data:
            self.output_voltage = data["outputVoltage"]
        if "outputCurrent" in data:
            self.output_current = data["outputCurrent"]
        if "outputPower" in data:
            self.output_power = data["outputPower"]
        if "temperature" in data:
            self.temperature = data["temperature"]
        if "setVoltage" in data:
            self.set_voltage = data["setVoltage"]
        if "setCurrent" in data:
            self.set_current = data["setCurrent"]
        if "group1setVoltage" in data:
            self.group1_set_voltage = data["group1setVoltage"]
        if "group1setCurrent" in data:
            self.group1_set_current = data["group1setCurrent"]
        if "group2setVoltage" in data:
            self.group2_set_voltage = data["group2setVoltage"]
        if "group2setCurrent" in data:
            self.group2_set_current = data["group2setCurrent"]
        if "group3setVoltage" in data:
            self.group3_set_voltage = data["group3setVoltage"]
        if "group3setCurrent" in data:
            self.group3_set_current = data["group3setCurrent"]
        if "group4setVoltage" in data:
            self.group4_set_voltage = data["group4setVoltage"]
        if "group4setCurrent" in data:
            self.group4_set_current = data["group4setCurrent"]
        if "group5setVoltage" in data:
            self.group5_set_voltage = data["group5setVoltage"]
        if "group5setCurrent" in data:
            self.group5_set_current = data["group5setCurrent"]
        if "group6setVoltage" in data:
            self.group6_set_voltage = data["group6setVoltage"]
        if "group6setCurrent" in data:
            self.group6_set_current = data["group6setCurrent"]
        if "overVoltageProtection" in data:
            self.over_voltage_protection = data["overVoltageProtection"]
        if "overCurrentProtection" in data:
            self.over_current_protection = data["overCurrentProtection"]
        if "overPowerProtection" in data:
            self.over_power_protection = data["overPowerProtection"]
        if "overTemperatureProtection" in data:
            self.over_temperature_protection = data["overTemperatureProtection"]
        if "lowVoltageProtection" in data:
            self.low_voltage_protection = data["lowVoltageProtection"]
        if "brightness" in data:
            self.brightness = data["brightness"]
        if "volume" in data:
            self.volume = data["volume"]
        if "meteringClosed" in data:
            self.metering_closed = data["meteringClosed"]
        if "outputCapacity" in data:
            self.output_capacity = data["outputCapacity"]
        if "outputEnergy" in data:
            self.output_energy = data["outputEnergy"]
        if "outputClosed" in data:
            self.output_closed = data["outputClosed"]
        if "protectionState" in data:
            self.protection_state = ProtectionState.from_string(data["protectionState"])
        if "mode" in data:
            self.mode = Mode.CC if data["mode"] == "CC" else Mode.CV
        if "upperLimitVoltage" in data:
            self.upper_limit_voltage = data["upperLimitVoltage"]
        if "upperLimitCurrent" in data:
            self.upper_limit_current = data["upperLimitCurrent"]
