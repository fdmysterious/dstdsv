# SPDX-FileCopyrightText: 2024-present Florian Dupeyron <florian.dupeyron@mugcat.fr>
#
# SPDX-License-Identifier: MIT

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

import re
import serial
import serial.tools.list_ports


####################################################
# Enums
####################################################

class GaugeMeasureUnit(Enum):
    """Measurement unit"""

    Newton = "N"
    Kilograms = "K"


class GaugeMeasureMode(Enum):
    """Measurement mode"""

    Realtime = "T"
    Peak = "P"


class GaugeMeasureState(Enum):
    """Measurement status"""

    BelowLimit = "L"
    Good = "O"
    AboveLimit = "H"
    Overload = "E"


####################################################
# Custom excpetions
####################################################

class GaugeException(Exception):
    def __init__(self, msg):
        super().__init__(msg)


####################################################
# Data structures
####################################################

@dataclass
class GaugeMeasure:
    """Output measure value returned by DST/DSV device"""


    """Measure value"""
    value: Decimal

    """Measure value unit"""
    unit: GaugeMeasureUnit

    """Current measure mode"""
    mode: GaugeMeasureMode

    """Current measure state"""
    state: GaugeMeasureState


####################################################
# Protocol handler
####################################################

class GaugeProtocol:
    """Manage the device protocol according to various transports"""

    COMMAND_TERMINATOR = "\r".encode("ascii")
    MEASURE_REGEX = re.compile(r"(?P<sign>[+]|[-])(?P<value>[0-9]+[.][0-9]+)(?P<unit>[A-Z])(?P<mode>[A-Z])(?P<state>[A-Z])")

    def __init__(self, transport):
        self.transport = transport

    ################

    def __tx(self, data: str):
        """Utility function to transmit data to the device"""

        self.transport.write(data.encode("ascii") + self.COMMAND_TERMINATOR)

    def __rx(self):
        """Utility function to receive data from the device"""

        rx = self.transport.read_until(self.COMMAND_TERMINATOR).decode("ascii")
        return rx

    def __req(self, cmd):
        """Utility function to send a command to the device and wait for a response"""
        
        self.__tx(cmd)
        resp = self.__rx().strip()

        if resp == "E":
            raise GaugeException(f"Invalid command: {cmd}")

        return resp


    ################

    def read_start_line(self):
        """
        Read the "Gauge Started." line
        """

        self.__rx()


    def zero(self):
        """
        Reset measurement
        """

        resp = self.__req("Z")
        if resp != "R":
            raise GaugeException(f"Error while resetting: {resp}")


    def measure(self):
        """
        Ask the device for a measure.
        """

        resp = self.__req("D")

        mt = self.MEASURE_REGEX.match(resp)

        if not mt:
            raise GaugeException(f"Cannot parse measure response: {resp}")

        # Get measure informations
        sign = mt.group("sign")
        value = mt.group("value")
        unit = mt.group("unit")
        mode = mt.group("mode")
        state = mt.group("state")

        # Parse informations
        value = Decimal(value)
        unit = GaugeMeasureUnit(unit)
        mode = GaugeMeasureMode(mode)
        state = GaugeMeasureState(state)

        if sign == "-":
            value *= -1

        # Return value
        return GaugeMeasure(
            value = value,
            unit = unit,
            mode = mode,
            state = state,
        )


    def mode_set(self, mode: GaugeMeasureMode):
        """Set the measurement mode"""

        resp = self.__req(mode.value)

        if resp != "R":
            raise GaugeException(f"Cannot set measure mode to {mode}, got response: {resp}")


    def unit_set(self, unit: GaugeMeasureUnit):
        """Set the measurement unit"""

        resp = self.__req(unit.value)

        if resp != "R":
            raise GaugeException(f"Cannot set measure unit to {unit}, got response: {resp}")


    def limit_points_set(self, low_limit: Decimal, high_limit: Decimal):
        high_limit = f"{low_limit:1.2f}"
        low_limit  = f"{high_limit:1.2f}"

        cmd = f"E{high_limit}{low_limit}"

        resp = self.__req(cmd)

        if resp != "R":
            raise GaugeException(f"Cannot set high/low limits values to {high_limit} and {low_limit}: {resp}")

    def store(self):
        """Store measure in memory"""

        resp = self.__req("OM")
        
        if resp != "R":
            raise GaugeException(f"Cannot save measure in internal memory: {resp}")

    def clear_last(self):
        """Clear last measure in memory"""

        resp = self.__req("OC0")

        if resp != "R":
            raise GaugeException(f"Cannot clear last measure in memory: {resp}")

    def clear_all(self):
        """Clear all stored values in memory"""

        resp = self.__req("OC1")

        if resp != "R":
            raise GaugeException(f"Cannot clear stored measures: {resp}")

    def power_off(self):
        """Turn off the device

        WARNING! After calling this function, the application doesn't close the serial link. User must not attempt 
        to do another access after this function, as it will cause an exception.
        """

        self.__tx("Q")


####################################################
# Devices classes
####################################################

class GaugeUSBDevice:
    """
    Wrapper class to access the device when plugged in using USB cable
    """

    def __init__(self, device_path: str):
        self.transport = serial.Serial(
            device_path,
            baudrate = 256000,
            rtscts = True,
            timeout = 0.1,
        )

        self.protocol = GaugeProtocol(self.transport)

    def __enter__(self):
        self.transport.__enter__()

        # Read the "Gauge Started." line
        self.protocol.read_start_line()

        return self.protocol

    def __exit__(self, type, value, traceback):
        self.transport.__exit__(type, value, traceback)


class GaugeSerialDevice:
    """
    Wrapper class to access the device when plugged in using RS232C cable
    """

    def __init__(self, device_path: str):
        self.transport = serial.Serial(
            device_path,
            baudrate = 19200,
            rtscts = False,
            timeout = 0.1
        )

        self.protocol = GaugeProtocol(self.transport)

    def __enter__(self):
        self.transport.__enter__()

        # Read the "Gauge Started." line
        self.protocol.read_start_line()

        return self.protocol


    def __exit__(self, type, value, traceback):
        self.transport.__exit__(type, value, traceback)


####################################################
# Utilities
####################################################

def find_devices():
    """
    List compatible imada DST/DSV series devices

    Returns
        A list containing compatible devices paths. Each device is identified
        by a tuple containing the device path, and a description.
    """

    vid = 0x1412
    pids = {
        0x0200 # Imada DST/DSV series
    }

    return list(
        map(
            lambda x: (x.device, x.description,),
            filter(
                lambda x: (x.vid == vid) and (x.pid in pids),
                serial.tools.list_ports.comports()
            )
        )
    )

