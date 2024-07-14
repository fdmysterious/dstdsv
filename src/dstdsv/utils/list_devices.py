# SPDX-FileCopyrightText: 2024-present Florian Dupeyron <florian.dupeyron@mugcat.fr>
#
# SPDX-License-Identifier: MIT

"""
Utility script to list compatible devices
"""

import dstdsv

if __name__ == "__main__":
    devices = dstdsv.find_devices()

    if not devices:
        print("Found no compatible device.")

    else:
        print("Found compatible devices:")
        for dev, description in devices:
            print(f"- {dev}: {description}")
