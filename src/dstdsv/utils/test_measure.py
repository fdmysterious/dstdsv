# SPDX-FileCopyrightText: 2024-present Florian Dupeyron <florian.dupeyron@mugcat.fr>
#
# SPDX-License-Identifier: MIT

"""
Utility script that finds the first available device, and try to do some measurements
"""

from dstdsv import (
    GaugeMeasureUnit,
    GaugeMeasureMode,
    GaugeUSBDevice,

    find_devices
)

import time

if __name__ == "__main__":
    # Try to find devices
    devices = find_devices()
    if not devices:
        raise RuntimeError("Found no compatible device")

    target_dev = devices[0][0] # Get path to first found compatible device


    # Run the measurements
    with GaugeUSBDevice(target_dev) as gauge:
        # Setup initial measure
        gauge.unit_set(GaugeMeasureUnit.Newton)
        gauge.mode_set(GaugeMeasureMode.Realtime)
        #gauge.zero()

        # Do the measurements
        measures = []
        for i in range(10):
            curtime  = time.time()
            nexttime = curtime+0.1

            measure = gauge.measure()
            measures.append(measure.value)
            time.sleep(nexttime-time.time())

        print("Measured data", measures)
