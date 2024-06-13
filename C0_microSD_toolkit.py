#!/usr/bin/env python3

# 	Copyright (c) 2024, Signaloid.
#
# 	Permission is hereby granted, free of charge, to any person obtaining a copy
# 	of this software and associated documentation files (the "Software"), to
# 	deal in the Software without restriction, including without limitation the
# 	rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# 	sell copies of the Software, and to permit persons to whom the Software is
# 	furnished to do so, subject to the following conditions:
#
# 	The above copyright notice and this permission notice shall be included in
# 	all copies or substantial portions of the Software.
#
# 	THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# 	IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# 	FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# 	AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# 	LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# 	FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# 	DEALINGS IN THE SOFTWARE.

import argparse
import sys
import os

from src.python.c0microsd.interface import C0microSDInterface

APP_VERSION = "1.0"  # Application version
MAX_FLASH_ATTEMPTS = 5  # Maximum flashing attempts


class C0microSDToolkit(C0microSDInterface):
    # 256 KiB offset for switch config
    BOOTLOADER_SWITCH_CONFIG_OFFSET = 0x40000
    # 384 KiB offset for unlocking bootloader
    BOOTLOADER_UNLOCK_OFFSET = 0x60000
    # 512 KiB offset for bootloader bitstream
    BOOTLOADER_BITSTREAM_OFFSET = 0x80000
    # 1.0 MiB offset for Signaloid Core bitstream
    SOC_BITSTREAM_OFFSET = 0x100000
    # 1.5 MiB offset for application bitstream
    USER_BITSTREAM_OFFSET = 0x180000
    # 2.0 MiB offset for userspace
    USER_DATA_OFFSET = 0x200000

    BOOTLOADER_UNLOCK_WORD = b"UBLD"

    def switch_boot_config(self) -> None:
        """
        Switches the boot configuration of C0-microSD.
        """
        self.get_status()

        if (self.configuration) == "bootloader":
            print(
                "Switching device boot mode from "
                "Bootloader to Signaloid Core..."
            )
        elif (self.configuration) == "soc":
            print(
                "Switching device boot mode from "
                "Signaloid Core to Bootloader..."
            )
        elif self.force_transactions:
            print("Switching device boot mode...")

        self._write(self.BOOTLOADER_SWITCH_CONFIG_OFFSET, bytes([0] * 512))

        print(
            "Device configured successfully. "
            "Power cycle the device to boot in new mode."
        )

    def unlock_bootloader(self) -> None:
        """
        Unlocks the bootloader. Used to flash new bootloader or Signaloid Core.
        """
        self.get_status()
        print("Unlocking bootloader...")
        self._write(self.BOOTLOADER_UNLOCK_OFFSET, self.BOOTLOADER_UNLOCK_WORD)

    def lock_bootloader(self) -> None:
        """
        Locks the bootloader and Signaloid Core sections.
        """
        self.get_status()
        print("Locking bootloader...")
        self._write(self.BOOTLOADER_UNLOCK_OFFSET, bytes([0] * 32))

    def flash_and_verify(
        self, file_data: bytes, flash_offset: int, max_attempts: int
    ) -> bool:
        """
        Flashes data to the C0-microSD and verifies that the flashing
        process was successful.

        :param file_data: A byte buffer with the data to be written
        :param flash_offset: Device offset (in bytes) for the data
                             to be written
        :param max_attempts: Maximum failed attempts before aborting operation
        """
        self.get_status()

        if self.configuration != "bootloader" and not self.force_transactions:
            raise RuntimeError(
                "Error: device is not in Bootloader mode. "
                "Switch to Bootloader mode and try again"
            )

        input_file_bytes = len(file_data)
        for i in range(1, max_attempts + 1):
            print(
                f"Attempt {i} of {max_attempts}: Flashing... ",
                end="",
                flush=True
            )
            self._write(flash_offset, file_data)
            print("Verifying...")
            data_to_verify = self._read(flash_offset, input_file_bytes)
            if data_to_verify == file_data:
                print("Success: The data matches.")
                return True
            else:
                print("Error: The data do not match.")
        return False

    def __str__(self) -> str:
        value = "Signaloid C0-microSD"
        if self.configuration == "bootloader":
            value += " | Loaded configuration: Bootloader"
        elif self.configuration == "soc":
            value += " | Loaded configuration: Signaloid Core"
        else:
            value += " | Loaded configuration: UNKNOWN"

        if self.configuration:
            major_version = self.configuration_version[0]
            minor_version = self.configuration_version[1]
            value += f" | Version: {major_version}.{minor_version}"
        else:
            value += " | Version: N/A"

        if self.configuration_switching:
            value += " | State SWITCHING"
        else:
            value += " | State IDLE"
        return value


def confirm_action() -> bool:
    """
    Prompts the user to accept/reject action

    :return: response
    """
    while True:
        # Prompt the user with the warning message
        response = input(
            "WARNING: This action may render the device inoperable. "
            "Proceed? (y/n): "
        ).lower()
        if response == "y":
            return True
        elif response == "n":
            return False
        else:
            print("Invalid input. Please enter 'y' for yes or 'n' for no.")


def main():
    parser = argparse.ArgumentParser(
        description=f"Signaloid C0-microSD-toolkit. Version {APP_VERSION}",
        add_help=False
    )

    parser.add_argument(
        '-h', '--help',
        action='help',
        default=argparse.SUPPRESS,
        help='Show this help message and exit.'
    )

    parser.add_argument(
        "-t",
        dest="target_device",
        required=True,
        help="Specify the target device path.",
    )
    parser.add_argument(
        "-b",
        dest="input_file",
        help=("Specify the input file for flashing "
              "(required with -u, -q, or -w)."),
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-u",
        dest="flash_user_data",
        action="store_true",
        help="Flash user data."
    )
    group.add_argument(
        "-q",
        dest="flash_bootloader",
        action="store_true",
        help="Flash new Bootloader bitstream."
    )
    group.add_argument(
        "-w",
        dest="flash_signaloid_core",
        action="store_true",
        help="Flash new Signaloid Core bitstream."
    )
    group.add_argument(
        "-s",
        dest="switch_boot_mode",
        action="store_true",
        help="Switch boot mode."
    )

    parser.add_argument(
        "-f",
        dest="force_flash",
        action="store_true",
        help="Force flash sequence (do not check for bootloader).",
    )

    args = parser.parse_args()

    # Create a new toolkit instance
    try:
        # Create a new toolkit object
        toolkit = C0microSDToolkit(
            args.target_device, force_transactions=args.force_flash
        )

        # Get status of the C0-microSD, also used to verify that communication
        # is correct, and that the C0-microSD is in bootloader mode.
        toolkit.get_status()

        print(toolkit)

        # This is the time to switch boot mode if needed.
        if args.switch_boot_mode:
            toolkit.switch_boot_config()
            print("Done.")
            exit(os.EX_OK)

        # All commands after this point need an input file
        if not args.input_file:
            parser.print_help()
            print("\nOption -b is required when flashing data.")
            sys.exit(os.EX_USAGE)

        # Open the input file and store data in memory.
        file_data = None
        try:
            with open(args.input_file, "rb") as src:
                file_data = src.read()
        except PermissionError:
            raise PermissionError(
                "Permission denied: You do not have the "
                f"necessary permissions to access {args.input_file}."
            )
        except FileNotFoundError:
            raise FileNotFoundError(
                f"File not found: The file {args.input_file} does not exist."
            )

        print("Filename: ", args.input_file)
        print("File size: ", len(file_data), "bytes.")

        if args.flash_bootloader:
            if not confirm_action():
                print("Aborting.")
                exit(os.EX_OK)
            toolkit.unlock_bootloader()
            print("Flashing bootloader bitstream...")
            toolkit.flash_and_verify(
                file_data, toolkit.BOOTLOADER_BITSTREAM_OFFSET,
                MAX_FLASH_ATTEMPTS
            )
            toolkit.lock_bootloader
        elif args.flash_signaloid_core:
            if not confirm_action():
                print("Aborting.")
                exit(os.EX_OK)
            toolkit.unlock_bootloader()
            print("Flashing Signaloid Core bitstream...")
            toolkit.flash_and_verify(
                file_data,
                toolkit.SOC_BITSTREAM_OFFSET,
                MAX_FLASH_ATTEMPTS
            )
            toolkit.lock_bootloader
        elif args.flash_user_data:
            print("Flashing user data bitstream...")
            toolkit.flash_and_verify(
                file_data,
                toolkit.USER_DATA_OFFSET,
                MAX_FLASH_ATTEMPTS
            )
        else:
            print("Flashing custom user bitstream...")
            toolkit.flash_and_verify(
                file_data, toolkit.USER_BITSTREAM_OFFSET, MAX_FLASH_ATTEMPTS
            )
        print("Done.")
    except Exception as e:
        print(f"{e}\nAn error occurred, aborting.", file=sys.stderr)


if __name__ == "__main__":
    main()
