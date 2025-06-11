#!/usr/bin/env python3

# Copyright (c) 2025, Signaloid.
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
from typing import Optional

from src.python.c0microsdplus.interface import C0microSDPlusInterface

APP_VERSION = "1.0"  # Application version
MAX_FLASH_ATTEMPTS = 5  # Maximum flashing attempts


class C0microSDPlusToolkit(C0microSDPlusInterface):
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

    def unlock_bitstream(self) -> None:
        """
        Unlocks the bitstream section of the non-volatile memory.
        """
        print("Unlocking bitstream section...")
        config_register = self.get_config_register()
        config_register |= 0x00000002
        self.set_config_register(config_register)

    def lock_bitstream(self) -> None:
        """
        Locks the bitstream section of the non-volatile memory.
        """
        print("Locking bitstream section...")
        config_register = self.get_config_register()
        config_register &= 0xFFFFFFFD
        self.set_config_register(config_register)

    def flash_and_verify(
        self, file_data: bytes, flash_offset: int, max_attempts: int
    ) -> bool:
        """
        Flashes data to the C0-microSD+ and verifies that the flashing
        process was successful.

        :param file_data: A byte buffer with the data to be written
        :param flash_offset: Device offset (in bytes) for the data
                             to be written
        :param max_attempts: Maximum failed attempts before aborting operation
        """

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

    def get_bitstream_prefix(self, bitstream_offset: int) -> bytes:
        """
        Reads the prefix section of a bitstream

        :param offset: Offset of bitstream in flash memory
        """

        # We assume that the prefix is never going to be larger than 4K
        prefix_chunk = self._read(bitstream_offset, 4096)

        prefix_start_word = b'\xFF\x00'
        prefix_end_word = b'\x00\xFF'

        prefix_start = prefix_chunk.find(prefix_start_word)
        prefix_end = prefix_chunk.find(prefix_end_word, prefix_start)

        if prefix_start == -1 or prefix_end == -1:
            raise ValueError("Could not find bitstream prefix section.")

        prefix_end += len(prefix_end_word)

        prefix_data = prefix_chunk[
            prefix_start + len(prefix_start_word):
            prefix_end - len(prefix_end_word)
        ]

        return prefix_data

    def verify_bitstream_crc(
            self,
            bitstream_offset: int,
            bitstream_crc: int,
            bitstream_prefix_size: int,
            bitstream_size: int
    ) -> bool:
        """
        Verifies the crc32 checksum of a bitstream

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
        bitstream_prefix_data = self.get_bitstream_prefix(offset)

        bitstream_prefix_string = bitstream_prefix_data.decode('utf-8')

        print(f"    Bitstream prefix section: {bitstream_prefix_string}")

        try:
            prefix_json = json.loads(bitstream_prefix_string)
            bitstream_crc = prefix_json["bitstream_crc"]
            bitstream_size = prefix_json["bitstream_size"]
            crc_pass = self.verify_bitstream_crc(
                offset,
                bitstream_crc,
                len(bitstream_prefix_data) + 4,
                bitstream_size
            )

            if crc_pass:
                print("    Bitstream CRC verification: PASS")
            else:
                print("    Bitstream CRC verification: FAIL")
        except ValueError or KeyError:
            print("    Unable to parse prefix for CRC verification")


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


def open_and_pad_file(input_file: str, pad_size: Optional[int]):
    file_data = None
    try:
        with open(input_file, "rb") as src:
            file_data = src.read()
    except PermissionError:
        raise PermissionError(
            "Permission denied: You do not have the "
            f"necessary permissions to access {input_file}."
        )
    except FileNotFoundError:
        raise FileNotFoundError(
            f"File not found: The file {input_file} does not exist."
        )

    print("Filename: ", input_file)
    print("File size: ", len(file_data), "bytes.")

    # Parse the pad size if provided
    if pad_size is not None:
        pad_size = parse_size(pad_size)

        if pad_size > len(file_data):
            # Pad the content with zeros
            file_data = file_data + (b'\x00' * (pad_size - len(file_data)))
            print(f"Input file padded to {pad_size} bytes.")
        elif pad_size < len(file_data):
            print("Warning: The specified padding size is smaller than the "
                  "input file size. No padding applied.")
    return file_data


def handle_info(args):
    try:
        toolkit = C0microSDPlusToolkit(args.target_device)
        print("Reading bitstream:")
        # Bitstream start from address 0 in the C0-microSD+
        toolkit.print_bitstream_information(0)
        print("Done.")
        exit(os.EX_OK)
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


def handle_core(args):
    # Create a new toolkit object
    toolkit = C0microSDPlusToolkit(args.target_device)
    # args.action is either "start" or "stop"
    try:
        if args.action == "start":
            print("Starting Signaloid SoC core")
            toolkit.set_command(0x00000000)
            toolkit.set_config_register(0x00000001)
        elif args.action == "stop":
            print("Stopping Signaloid SoC core")
            toolkit.set_config_register(0x00000000)
            toolkit.set_command(0x00000000)
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


def handle_flash_application(args):
    try:
        # Create a new toolkit object
        toolkit = C0microSDPlusToolkit(args.target_device)
        # Open and pad file
        file_data = open_and_pad_file(args.app_path, args.p)
        # Flash file to C0-microSD
        print("Flashing Signaloid SoC application...")
        toolkit.flash_and_verify(
            file_data,
            toolkit.APPLICATION_BINARY_OFFSET,
            MAX_FLASH_ATTEMPTS
        )
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


def handle_flash_bitstream(args):
    try:
        # Create a new toolkit object
        toolkit = C0microSDPlusToolkit(args.target_device)
        # Open and pad file
        file_data = open_and_pad_file(args.bs_path, args.p)
        # Flash file to C0-microSD
        if not confirm_action():
            print("Aborting.")
            exit(os.EX_USAGE)
        toolkit.unlock_bitstream()
        print("Flashing bootloader bitstream...")
        toolkit.flash_and_verify(
            file_data,
            toolkit.BITSTREAM_OFFSET,
            MAX_FLASH_ATTEMPTS
        )
        toolkit.lock_bitstream
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


def create_parser():
    parser = argparse.ArgumentParser(
        description="Signaloid C0-microSD-plus-toolkit. "
                    f"Version {APP_VERSION}",
        add_help=True
    )

    parser.add_argument(
        "target_device",
        help="Target device path"
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        metavar="<command>"
    )

    # info (no additional args)
    p_info = subparsers.add_parser(
        "info",
        help="Print target C0-microSD+ info and run bitstream verification."
    )
    p_info.set_defaults(func=handle_info)

    # core (positional: start|stop)
    p_core = subparsers.add_parser(
        "core",
        help="Start or stop the Signaloid SoC core"
    )
    p_core.add_argument(
        "action",
        choices=["start", "stop"],
        help="Action to perform on the core"
    )
    p_core.set_defaults(func=handle_core)

    # flash-application (positional path + optional -p)
    p_flash_app = subparsers.add_parser(
        "flash-application",
        help="Flash an application binary"
    )
    p_flash_app.add_argument(
        "app_path",
        help="Path to the application binary to flash"
    )
    p_flash_app.add_argument(
        "-p",
        required=False,
        type=str,
        help=("Pad input file with zeros to target size.")
    )
    p_flash_app.set_defaults(func=handle_flash_application)

    # flash-bitstream (same pattern as flash-application)
    p_flash_bs = subparsers.add_parser(
        "flash-bitstream",
        help="Flash a bitstream file"
    )
    p_flash_bs.add_argument(
        "bs_path",
        help="Path to the bitstream file to flash"
    )
    p_flash_bs.add_argument(
        "-p",
        required=False,
        type=str,
        help=("Pad input file with zeros to target size.")
    )
    p_flash_bs.set_defaults(func=handle_flash_bitstream)

    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()
    # Dispatch to the appropriate handler
    args.func(args)


if __name__ == "__main__":
    main()
