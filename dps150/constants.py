"""Constants for DPS-150 protocol.

This module contains all protocol constants including:
- Packet headers (input/output)
- Command codes (GET, SET, etc.)
- Type codes for different parameters
- Protection state mappings
- Serial port configuration
"""


# Packet headers
HEADER_INPUT = 0xF0  # 240 - incoming packets from device
HEADER_OUTPUT = 0xF1  # 241 - outgoing packets to device

# Command codes
CMD_GET = 0xA1  # 161 - get value
CMD_XXX_176 = 0xB0  # 176 - unknown (used for baud rate setting)
CMD_SET = 0xB1  # 177 - set value
CMD_XXX_192 = 0xC0  # 192 - unknown
CMD_XXX_193 = 0xC1  # 193 - connection/initialization

# Type codes for float values
VOLTAGE_SET = 193
CURRENT_SET = 194

# Group preset type codes (float)
GROUP1_VOLTAGE_SET = 197
GROUP1_CURRENT_SET = 198
GROUP2_VOLTAGE_SET = 199
GROUP2_CURRENT_SET = 200
GROUP3_VOLTAGE_SET = 201
GROUP3_CURRENT_SET = 202
GROUP4_VOLTAGE_SET = 203
GROUP4_CURRENT_SET = 204
GROUP5_VOLTAGE_SET = 205
GROUP5_CURRENT_SET = 206
GROUP6_VOLTAGE_SET = 207
GROUP6_CURRENT_SET = 208

# Protection type codes (float)
OVP = 209  # Over Voltage Protection
OCP = 210  # Over Current Protection
OPP = 211  # Over Power Protection
OTP = 212  # Over Temperature Protection
LVP = 213  # Low Voltage Protection

# Type codes for byte values
BRIGHTNESS = 214
VOLUME = 215

# Type codes for control
METERING_ENABLE = 216
OUTPUT_ENABLE = 219

# Type codes for reading
INPUT_VOLTAGE = 192
OUTPUT_VOLTAGE_CURRENT_POWER = 195
TEMPERATURE = 196
OUTPUT_CAPACITY = 217
OUTPUT_ENERGY = 218
PROTECTION_STATE = 220
MODE = 221  # CC=0 or CV=1
MODEL_NAME = 222
HARDWARE_VERSION = 223
FIRMWARE_VERSION = 224
UPPER_LIMIT_VOLTAGE = 226
UPPER_LIMIT_CURRENT = 227

# Special type code
ALL = 255  # Get all device state

# Protection states
PROTECTION_STATES = [
    "",      # 0 - Normal
    "OVP",   # 1 - Over Voltage Protection
    "OCP",   # 2 - Over Current Protection
    "OPP",   # 3 - Over Power Protection
    "OTP",   # 4 - Over Temperature Protection
    "LVP",   # 5 - Low Voltage Protection
    "REP",   # 6 - Reverse Connection Protection
]

# Serial port settings
BAUD_RATE = 115200
DATA_BITS = 8
STOP_BITS = 1
PARITY = "N"  # pyserial uses 'N' for no parity
FLOW_CONTROL = "hardware"

# Baud rate options (for initialization)
BAUD_RATE_OPTIONS = [9600, 19200, 38400, 57600, 115200]

# USB Vendor/Product IDs (if available for auto-detection)
# Note: These may need to be determined from actual device
USB_VID = None  # To be determined
USB_PID = None  # To be determined
