#!/usr/bin/env python3

# Copyright (c) 2024, Signaloid.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import argparse
import sys
import os
import json
import binascii
import re
from typing import Optional, Tuple

from src.python.c0microsd.interface import C0microSDInterface
from src.python.c0microsd.constants import BOOTLOADER_CONSTANTS

APP_VERSION = "2.0"  # Application version
MAX_FLASH_ATTEMPTS = 5  # Maximum flashing attempts


class C0microSDToolkit(C0microSDInterface):
    def __init__(self, target_device, force_transactions=False):
        super().__init__(target_device, force_transactions)
        self.get_status()

        btldr_maj_ver = self.configuration_version[0]

        if (btldr_maj_ver not in BOOTLOADER_CONSTANTS):
            print("Warning. Bootloader version unrecognised. "
                  "Falling back to Ver 1 configuration")
            btldr_maj_ver = 1

        self.BOOTLOADER_SWITCH_CONFIG_OFFSET = \
            BOOTLOADER_CONSTANTS[btldr_maj_ver].kBootloaderSwitchConfigOffset
        self.BOOTLOADER_UNLOCK_OFFSET = \
            BOOTLOADER_CONSTANTS[btldr_maj_ver].kBootloaderUnlockOffset
        self.BOOTLOADER_BITSTREAM_OFFSET = \
            BOOTLOADER_CONSTANTS[btldr_maj_ver].kBootloaderBitstreamOffset
        self.SOC_BITSTREAM_OFFSET = \
            BOOTLOADER_CONSTANTS[btldr_maj_ver].kSOCBitstreamOffset
        self.USER_BITSTREAM_OFFSET = \
            BOOTLOADER_CONSTANTS[btldr_maj_ver].kUserBitstreamOffset
        self.USER_DATA_OFFSET = \
            BOOTLOADER_CONSTANTS[btldr_maj_ver].kUserDataOffset

        self.SERIAL_NUMBER_OFFSET = \
            BOOTLOADER_CONSTANTS[btldr_maj_ver].kSerialNumberOffset
        self.SERIAL_NUMBER_SIZE = \
            BOOTLOADER_CONSTANTS[btldr_maj_ver].kSerialNumberSize

        self.UUID_OFFSET = \
            BOOTLOADER_CONSTANTS[btldr_maj_ver].kUUIDOffset
        self.UUID_SIZE = \
            BOOTLOADER_CONSTANTS[btldr_maj_ver].kUUIDSize

        self.BOOTLOADER_UNLOCK_WORD = \
            BOOTLOADER_CONSTANTS[btldr_maj_ver].kBootloaderUnlockWord

        self.WARMBOOT_TEMPLATE = \
            BOOTLOADER_CONSTANTS[btldr_maj_ver].kWamrbootTemplate

    def _strip_trailing_bytes(
            self, byte_array: bytearray, byte: int
            ) -> bytearray:
        """
        Strip the trailing bytes of a bytearray

        :param byte_array (iterable of bytes): Array of bytes to strip.
        :param byte (int): The byte to remove.
        :return (bytearray): Stripped array of bytes
        """
        end = len(byte_array)
        while end > 0 and byte_array[end - 1] == byte:
            end -= 1
        return byte_array[:end]

    def switch_boot_config(self) -> None:
        """
        Switches the boot configuration of C0-microSD.
        """
        self.get_status()

        if (self.configuration) == "bootloader":
            print(
                "Switching device boot mode from "
                "Bootloader to Signaloid SoC..."
            )
        elif (self.configuration) == "soc":
            print(
                "Switching device boot mode from "
                "Signaloid SoC to Bootloader..."
            )
        elif self.force_transactions:
            print("Switching device boot mode...")

        self._write(self.BOOTLOADER_SWITCH_CONFIG_OFFSET, bytes([0] * 512))

        print(
            "Device configured successfully. "
            "Power cycle the device to boot in new mode."
        )

        if (self.configuration == "bootloader"):
            print(
                "To use the Signaloid C0-microSD in Custom User Bitstream mode"
                ", power it on without an SD-protocol host present."
            )

    def unlock_bootloader(self) -> None:
        """
        Unlocks the bootloader. Used to flash new bootloader or Signaloid SoC.
        """
        self.get_status()
        print("Unlocking bootloader...")
        self._write(self.BOOTLOADER_UNLOCK_OFFSET, self.BOOTLOADER_UNLOCK_WORD)

    def lock_bootloader(self) -> None:
        """
        Locks the bootloader and Signaloid SoC sections.
        """
        self.get_status()
        print("Locking bootloader...")
        self._write(self.BOOTLOADER_UNLOCK_OFFSET, bytes([0] * 32))

    def flash_and_verify(
        self,
        file_data: bytes,
        flash_offset: int,
        max_attempts: int,
        unlock_bootloader: bool = False
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

        if (unlock_bootloader):
            self.unlock_bootloader()

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
                if (unlock_bootloader):
                    self.lock_bootloader()
                return True
            else:
                print("Error: The data do not match.")
        if (unlock_bootloader):
            self.lock_bootloader()
        return False

    def find_json_string(self, data: bytes) -> Optional[dict]:
        #
        #    Attempts to decode the first valid JSON string from a byte stream
        #    Assumes input is <= 4 KB and encoded in ASCII
        #
        try:
            ascii_str = data.decode('ascii', errors='ignore')
        except Exception as e:
            raise ValueError(f"Prefix decoding failed: {e}")

        brace_stack = []
        stack_index = -1

        for i, ch in enumerate(ascii_str):
            if ch == '{':
                if not brace_stack:
                    stack_index = i
                brace_stack.append('{')
            elif ch == '}':
                if brace_stack:
                    brace_stack.pop()
                    if not brace_stack and stack_index != -1:
                        candidate = ascii_str[stack_index:i+1]
                        try:
                            return json.loads(candidate)
                        except json.JSONDecodeError:
                            pass    # Not a valid JSON object, continue search
        return None

    def get_bitstream_prefix(
            self,
            bitstream_offset: int) -> Tuple[Optional[dict], int, int]:
        """
        Reads the prefix section of a bitstream

        :param offset: Offset of bitstream in flash memory
        """

        # We assume that the prefix is never going to be larger than 4K
        self.get_status()
        prefix_chunk = self._read(bitstream_offset, 4096)

        # Decode prefix chunk to find prefix
        prefix = self.find_json_string(prefix_chunk)

        if (prefix is None):
            raise ValueError("Could not find bitstream prefix section.")

        try:
            major_bitstream_version = int(str(prefix["v"]).split(".")[0])
        except Exception:
            major_bitstream_version = 1

        # Use the bitstream version to know exactly how to
        # find start and end of prefix. This is required to calculate
        # the CRC
        prefix_start_word = \
            BOOTLOADER_CONSTANTS[major_bitstream_version].kBitstreamPrefixStart
        prefix_end_word = \
            BOOTLOADER_CONSTANTS[major_bitstream_version].kBitstreamPrefixEnd

        prefix_start = prefix_chunk.find(prefix_start_word)
        prefix_end = prefix_chunk.find(prefix_end_word, prefix_start)
        prefix_end += len(prefix_end_word)

        return prefix, prefix_start, prefix_end

    def verify_bitstream_crc(
            self,
            bitstream_offset: int,
            bitstream_crc: int,
            bitstream_prefix_size: int,
            bitstream_size: int
    ) -> bool:
        """
        Verifies a the crc32 checksum of a bitstream

        :param bitstream_offset: Offset of bitstream in flash memory
        :param bitstream_crc: Expected crc of bitstream
        :param bitstream_size: Expected size of bitstream in bytes
        """

        bitstream = self._read(
            bitstream_offset, bitstream_prefix_size + bitstream_size
        )

        bitstream_data = bitstream[bitstream_prefix_size:]
        actual_crc = binascii.crc32(bitstream_data) & 0xFFFFFFFF

        return actual_crc == bitstream_crc

    def print_bitstream_information(self, offset) -> None:
        """
        Reads and prints bitstream prefix from a specific offset in the
        device. Also runs crc verification if prefix is in json format and
        includes `bitstream_crc` and `bitstream_size` attributes

        :param bitstream_offset: Offset of bitstream in flash memory
        :param bitstream_crc: Expected crc of bitstream
        :param bitstream_size: Expected size of bitstream in bytes
        """

        prefix, _, prefix_end = self.get_bitstream_prefix(offset)
        print("    Bitstream prefix section: "
              f"{json.dumps(prefix, separators=(', ', ': '))}")

        try:
            if "bitstream_crc" in prefix:
                bitstream_crc = prefix["bitstream_crc"]
            elif "crc" in prefix:
                bitstream_crc = prefix["crc"]

            if "bitstream_size" in prefix:
                bitstream_size = prefix["bitstream_size"]
            elif "size" in prefix:
                bitstream_size = prefix["size"]

            crc_pass = self.verify_bitstream_crc(
                offset,
                bitstream_crc,
                prefix_end,
                bitstream_size
            )

            if crc_pass:
                print("    Bitstream CRC verification: PASS")
            else:
                print("    Bitstream CRC verification: FAIL")
        except Exception:
            print("    Unable to parse prefix for CRC verification")

    def verify_warmboot_section(self, template: Optional[str] = None) -> bool:
        warmboot_section = self._read(0, 5*32).hex()
        if template is None:
            template = self.WARMBOOT_TEMPLATE
        return warmboot_section == template

    def get_serial_number(self) -> str:
        serial_number_section = self._read(
            self.SERIAL_NUMBER_OFFSET, self.SERIAL_NUMBER_SIZE
        )
        serial_number_section = self._strip_trailing_bytes(
            serial_number_section, 0xFF
        )

        serial_number_section = ''.join(
            to_printable(byte) for byte in serial_number_section
        )
        return serial_number_section

    def get_uuid(self) -> str:
        uuid_section = self._read(
            self.UUID_OFFSET, self.UUID_SIZE
        )
        uuid_section = self._strip_trailing_bytes(
            uuid_section, 0xFF
        )

        uuid_section = ''.join(
            to_printable(byte) for byte in uuid_section
        )
        return uuid_section


def to_printable(byte: bytearray) -> str:
    """
    Decode byte to character using UTF-8 encoding.
    Decode anything that is not UTF-8 as '.'
    """
    return chr(byte) if 32 <= byte <= 126 else '.'


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


def parse_size(size_str):
    """
    Parses a size string with optional suffixes (K, M, G)
    and converts it to bytes.

    :param size_str: Size string (e.g., '1K', '5M', '3G')
    :return: Size in bytes as an integer
    """
    match = re.match(r"(\d+)([KMG]?)", size_str.upper())
    if not match:
        raise ValueError("Invalid padding size format. "
                         "Use a number or a number with suffix (K, M, G).")

    size = int(match.group(1))
    suffix = match.group(2)

    if suffix == 'K':
        return size * 1024
    elif suffix == 'M':
        return size * (1024 ** 2)
    elif suffix == 'G':
        return size * (1024 ** 3)
    else:
        return size


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

    parser.add_argument(
        "-p",
        dest="pad_size",
        type=str,
        help=("Pad input file with zeros to target size.")
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
        dest="flash_signaloid_soc",
        action="store_true",
        help="Flash new Signaloid SoC bitstream."
    )
    group.add_argument(
        "-s",
        dest="switch_boot_mode",
        action="store_true",
        help="Switch boot mode."
    )
    group.add_argument(
        "-i",
        dest="print_information",
        action="store_true",
        help="Print target C0-microSD information, and run data verification."
    )
    group.add_argument(
        "-y",
        dest="flash_warmboot",
        action="store_true",
        help="Flash warmboot sector."
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

        # Print additional information and exit
        if args.print_information:
            if toolkit.configuration != "bootloader":
                print("Device is not in Bootloader mode.")
                print(
                    "To display device Serial Number, device UUID, and verify "
                    "the bitstream and warmboot sections \nof the "
                    "non-volatile memory, switch to Bootloader mode and "
                    "try again."
                )
                exit(os.EX_CONFIG)

            print(f"Device Serial Number: {toolkit.get_serial_number()}")
            print(f"Device UUID: {toolkit.get_uuid()}")
            print()
            print("Reading Bootloader bitstream:")
            toolkit.print_bitstream_information(
                toolkit.BOOTLOADER_BITSTREAM_OFFSET)
            print("Reading Signaloid SoC bitstream:")
            toolkit.print_bitstream_information(
                toolkit.SOC_BITSTREAM_OFFSET)
            toolkit.verify_warmboot_section()
            if (toolkit.verify_warmboot_section()):
                print("Warmboot section verification: PASS")
            else:
                print("Warmboot section verification: FAIL")
                # Bootloader V2.0 and up supports flashing the warmboot
                if (toolkit.configuration_version[0] >= 2):
                    print("You can attempt to fix the Warmboot "
                          "section by using the -y argument")
            print("Done.")
            exit(os.EX_OK)

        # Print additional information and exit
        if args.flash_warmboot:
            if toolkit.configuration != "bootloader":
                print("Device is not in Bootloader mode.")
                print(
                    "To display device Serial Number, device UUID, and verify "
                    "the bitstream and warmboot sections \nof the "
                    "non-volatile memory, switch to Bootloader mode and "
                    "try again."
                )
                exit(os.EX_CONFIG)

            if (toolkit.configuration_version[0] < 2):
                print(
                    "Error: Bootloader version "
                    f"{toolkit.configuration_version[0]}."
                    f"{toolkit.configuration_version[1]} "
                    "cannot flash the warmboot section."
                )
                exit(os.EX_CONFIG)

            if not confirm_action():
                print("Aborting.")
                exit(os.EX_USAGE)
            print("Flashing wamrboot section...")
            warmboot_bytes = bytes.fromhex(toolkit.WARMBOOT_TEMPLATE)
            print(toolkit.WARMBOOT_TEMPLATE)
            toolkit.flash_and_verify(warmboot_bytes, 0, 10, True)
            print("Done.")
            exit(os.EX_OK)

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

        # Parse the pad size if provided
        pad_size = None
        if args.pad_size is not None:
            pad_size = parse_size(args.pad_size)

        if pad_size is not None and pad_size > len(file_data):
            # Pad the content with zeros
            file_data = file_data + (b'\x00' * (pad_size - len(file_data)))
            print(f"Input file padded to {pad_size} bytes.")
        elif pad_size is not None and pad_size < len(file_data):
            print("Warning: The specified padding size is smaller than the "
                  "input file size. No padding applied.")

        if args.flash_bootloader:
            # Make sure the user is flashing a bootloader bitstream
            bitstream_prefix = toolkit.find_json_string(file_data[:4096])
            if (
                (bitstream_prefix is None) or
                ("type" not in bitstream_prefix) or
                (bitstream_prefix["type"] != "bldr")
            ):
                print("Warning: Target bitstream is not a Bootloader.")
                print("Please use this option only to flash an official "
                      "Bootloader bitstream from Signaloid. Visit "
                      "https://github.com/signaloid/C0-microSD-Hardware "
                      "to get the latest Bootloader bitstream")
                if (args.force_flash):
                    print("Flashing bitstream (used -f argument)")
                else:
                    print("Aborting.")
                    exit(os.EX_USAGE)

            if not confirm_action():
                print("Aborting.")
                exit(os.EX_USAGE)

            print("Flashing bootloader bitstream...")
            toolkit.flash_and_verify(
                file_data, toolkit.BOOTLOADER_BITSTREAM_OFFSET,
                MAX_FLASH_ATTEMPTS,
                unlock_bootloader=True
            )

        elif args.flash_signaloid_soc:
            # Make sure the user is flashing an soc bitstream
            bitstream_prefix = toolkit.find_json_string(file_data[:4096])
            if (
                (bitstream_prefix is None) or
                ("type" not in bitstream_prefix) or
                (bitstream_prefix["type"] != "soc")
            ):
                print("Warning: Target bitstream is not a Signaloid SoC.")
                print("Please use this option only to flash an official "
                      "Signaloid SoC bitstream from Signaloid. Visit "
                      "https://github.com/signaloid/C0-microSD-Hardware "
                      "to get the latest Signaloid SoC bitstream")
                if (args.force_flash):
                    print("Flashing bitstream (used -f argument)")
                else:
                    print("Aborting.")
                    exit(os.EX_USAGE)

            if not confirm_action():
                print("Aborting.")
                exit(os.EX_USAGE)

            print("Flashing Signaloid SoC bitstream...")
            toolkit.flash_and_verify(
                file_data,
                toolkit.SOC_BITSTREAM_OFFSET,
                MAX_FLASH_ATTEMPTS,
                unlock_bootloader=True
            )
        elif args.flash_user_data:
            print("Flashing user data bitstream...")
            toolkit.flash_and_verify(
                file_data,
                toolkit.USER_DATA_OFFSET,
                MAX_FLASH_ATTEMPTS,
                unlock_bootloader=False
            )
        else:
            print("Flashing custom user bitstream...")
            toolkit.flash_and_verify(
                file_data, toolkit.USER_BITSTREAM_OFFSET, MAX_FLASH_ATTEMPTS
            )
        print("Done.")
    except Exception as e:
        print(f"{e}\nAn error occurred, aborting.", file=sys.stderr)
        if isinstance(e, ValueError):
            exit(os.EX_DATAERR)
        elif isinstance(e, FileNotFoundError):
            exit(os.EX_NOINPUT)
        elif isinstance(e, PermissionError):
            exit(os.EX_NOPERM)
        else:
            exit(os.EX_SOFTWARE)


if __name__ == "__main__":
    main()
