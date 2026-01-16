"""Utility functions for DPS-150 library.

This module provides helper functions for serial port detection and
enumeration. Useful for finding the DPS-150 device automatically or
listing available ports for user selection.
"""


import serial.tools.list_ports
from typing import Optional

from .constants import USB_VID, USB_PID


def find_dps150_port() -> Optional[str]:
    """Find the serial port for DPS-150 device.
    
    Attempts to find the device by USB VID/PID if known, otherwise
    returns the first available serial port.
    
    Returns:
        Port name (e.g., '/dev/ttyUSB0' or 'COM3') or None if not found
    """
    ports = serial.tools.list_ports.comports()
    
    # If we have VID/PID, try to match
    if USB_VID is not None and USB_PID is not None:
        for port in ports:
            if port.vid == USB_VID and port.pid == USB_PID:
                return port.device
    
    # Otherwise, return first available port
    # In practice, user should specify port or we could look for
    # common patterns, but for now just return None to force explicit port
    return None


def list_serial_ports() -> list[dict]:
    """List all available serial ports.
    
    Returns:
        List of dictionaries with port information:
        [{'device': '/dev/ttyUSB0', 'description': '...', 'vid': ..., 'pid': ...}, ...]
    """
    ports = serial.tools.list_ports.comports()
    return [
        {
            "device": port.device,
            "description": port.description,
            "vid": port.vid,
            "pid": port.pid,
            "serial_number": port.serial_number,
        }
        for port in ports
    ]
