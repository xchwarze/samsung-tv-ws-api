import os
import re

HEADER = (
    "# SamsungTVWS - Samsung Smart TV WS API wrapper\n\n"
    "# Copyright (C) 2019 Xchwarze\n"
    "#\n"
    "#     This library is free software; you can redistribute it and/or\n"
    "#     modify it under the terms of the GNU Lesser General Public\n"
    "#     License as published by the Free Software Foundation; either\n"
    "#     version 2.1 of the License, or (at your option) any later version.\n\n"
    "#     This library is distributed in the hope that it will be useful,\n"
    "#     but WITHOUT ANY WARRANTY; without even the implied warranty of\n"
    "#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU\n"
    "#     Lesser General Public License for more details.\n\n"
    "#     You should have received a copy of the GNU Lesser General Public\n"
    "#     License along with this library; if not, write to the Free Software\n"
    "#     Foundation, Inc., 51 Franklin Street, Fifth Floor,\n"
    "#     Boston, MA  02110-1335  USA\n"
    ""
    ""
    "\n\nclass SamsungTVShortcuts:\n"
    "\tdef __init__(self, remote):\n"
    "\t\tself.remote = remote\n"
)

KEYS_FILE = os.path.join(os.path.dirname(__file__), "keys.txt")

print(HEADER)
with open(KEYS_FILE, "r") as file:
    registers = file.read().splitlines()
    # registers = [re.sub(r":\(\)", '_', register[0]) for register in registers]
    registers = [register.split(": ") for register in registers]
    for idx, reg in enumerate(registers):
        command = reg[0].strip()
        if (
            len(reg) == 1
            and idx != (len(registers) - 1)
            and registers[idx + 1][0].find("--") != -1
        ):
            print(f"# {command}")
        elif len(reg) == 1 and reg[0].find("KEY_") != -1:
            shortcut_name = command.replace("KEY_", "").lower()
            print(f"\tdef {shortcut_name}(self):")
            print(f"\t\tself.remote.send_key('{command}')\n")
        elif len(reg) > 1 and reg[0].find("KEY_") != -1:
            shortcut_name = (
                reg[1]
                .replace("  ", "")
                .replace(" ", "_")
                .lower()
                .replace(":", "")
                .replace("(", "")
                .replace(")", "")
                .replace("/", "")
                .replace("+", "")
                .replace("3d", "three_d")
            )
            if shortcut_name[0] == "_":
                shortcut_name = shortcut_name[1:]
            print(f"\tdef {shortcut_name}(self):")
            print(f"\t\tself.remote.send('{command}')\n")

    pass
    ...
