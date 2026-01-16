"""Async serial transport layer for DPS-150.

This module provides the low-level serial communication layer using
pyserial-asyncio. It handles:
- Async serial port connection/disconnection
- Background reading and packet extraction
- Thread-safe writing with proper locking
- Packet buffer management for stream parsing
"""


import asyncio
from typing import Callable, Optional

import serial_asyncio

from .constants import (
    BAUD_RATE,
    DATA_BITS,
    FLOW_CONTROL,
    PARITY,
    STOP_BITS,
)
from .exceptions import DPS150ConnectionError, DPS150ProtocolError
from .protocol import PacketBuffer, decode_packet


class SerialTransport:
    """Async serial transport for DPS-150 device."""
    
    def __init__(self, port: str, callback: Optional[Callable] = None):
        """Initialize transport.
        
        Args:
            port: Serial port path (e.g., '/dev/ttyUSB0' or 'COM3')
            callback: Optional callback function for received packets
        """
        self.port = port
        self.callback = callback
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.reader_task: Optional[asyncio.Task] = None
        self.buffer = PacketBuffer()
        self._lock = asyncio.Lock()
        self._connected = False
    
    async def connect(self) -> None:
        """Connect to the serial port."""
        try:
            self.reader, self.writer = await serial_asyncio.open_serial_connection(
                url=self.port,
                baudrate=BAUD_RATE,
                bytesize=DATA_BITS,
                parity=PARITY,
                stopbits=STOP_BITS,
                rtscts=True,  # Hardware flow control
            )
            self._connected = True
            self.buffer.clear()
            self.reader_task = asyncio.create_task(self._read_loop())
        except Exception as e:
            self._connected = False
            raise DPS150ConnectionError(f"Failed to connect to {self.port}: {e}") from e
    
    async def disconnect(self) -> None:
        """Disconnect from the serial port."""
        self._connected = False
        
        if self.reader_task:
            self.reader_task.cancel()
            try:
                await self.reader_task
            except asyncio.CancelledError:
                pass
            self.reader_task = None
        
        if self.writer:
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except Exception:
                pass
            self.writer = None
        
        self.reader = None
        self.buffer.clear()
    
    async def write(self, data: bytes) -> None:
        """Write data to the serial port.
        
        Uses a lock to ensure writes are serialized and not interleaved.
        Includes a small delay after writing to match the JavaScript
        implementation's timing behavior.
        
        Args:
            data: Bytes to write (should be a complete packet)
        
        Raises:
            DPS150ConnectionError: If not connected to device
        """
        if not self._connected or not self.writer:
            raise DPS150ConnectionError("Not connected")
        
        # Use lock to serialize writes and prevent packet corruption
        async with self._lock:
            self.writer.write(data)
            await self.writer.drain()  # Wait for data to be written
            # Small delay after write (matches JS implementation timing)
            # Gives device time to process the command
            await asyncio.sleep(0.05)
    
    async def _read_loop(self) -> None:
        """Background task to continuously read from serial port.
        
        This method runs as a background task and continuously reads data
        from the serial port. It handles:
        - Accumulating partial packets in a buffer
        - Extracting complete packets
        - Decoding packets and verifying checksums
        - Invoking the callback with parsed packet data
        
        The loop continues until the connection is closed or an error occurs.
        Timeouts are normal and expected when no data is available.
        """
        try:
            while self._connected and self.reader:
                try:
                    # Read available data (with timeout)
                    data = await asyncio.wait_for(self.reader.read(1024), timeout=1.0)
                    if not data:
                        # EOF or connection closed
                        break
                    
                    # Add to buffer
                    self.buffer.append(data)
                    
                    # Extract and process complete packets
                    packets = self.buffer.extract_packets()
                    for packet in packets:
                        try:
                            command, type_code, length, data_bytes = decode_packet(packet)
                            if self.callback:
                                self.callback(command, type_code, data_bytes)
                        except DPS150ProtocolError as e:
                            # Log but continue processing
                            # In production, you might want to log this
                            pass
                
                except asyncio.TimeoutError:
                    # Timeout is normal, just continue
                    continue
                except Exception as e:
                    # Unexpected error, break loop
                    if self._connected:
                        # Only log if we're still supposed to be connected
                        pass
                    break
        
        except asyncio.CancelledError:
            # Normal cancellation
            pass
        except Exception as e:
            # Unexpected error
            if self._connected:
                pass
    
    @property
    def is_connected(self) -> bool:
        """Check if transport is connected."""
        return self._connected
