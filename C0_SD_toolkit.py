#!/usr/bin/env python3

# Copyright (c) 2026, Signaloid.
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
from typing import Optional, Type

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src" / "python"))

from signaloid_utilities.c0sd.interface import (
    C0SDBaseInterface,
    C0microSDPlusInterface,
    C0SDInterface,
    UnsupportedConfigureAction,
)

APP_VERSION = "2.1"  # Application version
MAX_FLASH_ATTEMPTS = 5  # Maximum flashing attempts


class _C0SDToolkitMixin:
    """Variant-agnostic toolkit operations.

    Combined with a variant interface (which supplies the offsets, the
    config-register methods, and the `apply_configure_action` dispatch)
    to form a concrete `*Toolkit` class.
    """

    def _strip_trailing_bytes(
            self, byte_array: bytearray, byte: int
            ) -> bytearray:
        end = len(byte_array)
        while end > 0 and byte_array[end - 1] == byte:
            end -= 1
        return byte_array[:end]

    def flash_and_verify(
        self, file_data: bytes, flash_offset: int, max_attempts: int
    ) -> bool:
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
        bitstream = self._read(
            bitstream_offset, bitstream_prefix_size + bitstream_size
        )

        bitstream_data = bitstream[bitstream_prefix_size:]
        actual_crc = binascii.crc32(bitstream_data) & 0xFFFFFFFF

        return actual_crc == bitstream_crc

    def print_bitstream_information(self, offset) -> None:
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


class C0microSDPlusToolkit(_C0SDToolkitMixin, C0microSDPlusInterface):
    pass


class C0SDToolkit(_C0SDToolkitMixin, C0SDInterface):
    pass


TOOLKIT_BY_VARIANT: dict = {
    "C0-microSD+": C0microSDPlusToolkit,
    "C0-SD":       C0SDToolkit,
}


def _toolkit_cls_for(variant: str) -> Type[C0SDBaseInterface]:
    return TOOLKIT_BY_VARIANT[variant]


def _make_toolkit(args) -> C0SDBaseInterface:
    """Construct the toolkit for the selected variant.

    Forwards ``--regmap-path`` to the variant interface's ``regmap_path``
    so the offsets are sourced from the given regmap package directory
    (or the built-in regmaps when it is None).
    """
    return _toolkit_cls_for(args.variant)(
        args.target_device, regmap_path=args.regmap_path
    )


def confirm_action() -> bool:
    while True:
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

    if pad_size is not None:
        pad_size = parse_size(pad_size)

        if pad_size > len(file_data):
            file_data = file_data + (b'\x00' * (pad_size - len(file_data)))
            print(f"Input file padded to {pad_size} bytes.")
        elif pad_size < len(file_data):
            print("Warning: The specified padding size is smaller than the "
                  "input file size. No padding applied.")
    return file_data


def _exit_for_exception(e: Exception) -> None:
    print(f"{e}\nAn error occurred, aborting.", file=sys.stderr)
    if isinstance(e, ValueError):
        exit(os.EX_DATAERR)
    elif isinstance(e, FileNotFoundError):
        exit(os.EX_NOINPUT)
    elif isinstance(e, PermissionError):
        exit(os.EX_NOPERM)
    else:
        exit(os.EX_SOFTWARE)


def handle_info(args):
    try:
        toolkit = _make_toolkit(args)
        print("Reading bitstream:")
        toolkit.print_bitstream_information(toolkit.BITSTREAM_OFFSET)
        print("Done.")
        exit(os.EX_OK)
    except Exception as e:
        _exit_for_exception(e)


def handle_status(args):
    try:
        toolkit = _make_toolkit(args)
        toolkit.verbose_status()
        exit(os.EX_OK)
    except Exception as e:
        _exit_for_exception(e)


def handle_flash_application(args):
    try:
        toolkit = _make_toolkit(args)
        file_data = open_and_pad_file(args.app_path, args.p)
        print("Flashing Signaloid SoC application...")
        toolkit.flash_and_verify(
            file_data,
            toolkit.APPLICATION_BINARY_OFFSET,
            MAX_FLASH_ATTEMPTS
        )
    except Exception as e:
        _exit_for_exception(e)


def handle_flash_bitstream(args):
    try:
        toolkit = _make_toolkit(args)
        file_data = open_and_pad_file(args.bs_path, args.p)
        if not confirm_action():
            print("Aborting.")
            exit(os.EX_USAGE)
        toolkit.apply_configure_action("unlock-bitstream", lambda: True)
        print("Flashing bitstream...")
        toolkit.flash_and_verify(
            file_data,
            toolkit.BITSTREAM_OFFSET,
            MAX_FLASH_ATTEMPTS
        )
        toolkit.apply_configure_action("lock-bitstream", lambda: True)
    except Exception as e:
        _exit_for_exception(e)


def handle_configuration(args):
    try:
        toolkit = _make_toolkit(args)
        toolkit.apply_configure_action(args.action, confirm_action)
    except UnsupportedConfigureAction as e:
        print(f"Error: {e}", file=sys.stderr)
        exit(os.EX_USAGE)
    except Exception as e:
        _exit_for_exception(e)


# One-line summary of what each subcommand does, shown in the toolkit
# help epilog so a single `--help` lists every capability of the tool.
_COMMAND_DESCRIPTIONS: list[tuple[str, str]] = [
    ("info",
     "Print device info and run bitstream CRC verification."),
    ("status",
     "Print the COMMAND, CONFIG and STATUS registers "
     "(plus SD_CONFIG where present)."),
    ("flash-application <app_path> [-p SIZE]",
     "Flash an application binary to the device's user-data flash "
     "region (optionally zero-padded to SIZE)."),
    ("flash-bitstream <bs_path> [-p SIZE]",
     "Unlock the bitstream region, flash a bitstream, then re-lock it "
     "(optionally zero-padded to SIZE)."),
    ("configure / config <action>",
     "Apply a single configuration action (see 'configure actions' "
     "below)."),
]


def _config_actions_for(variant: str) -> list[tuple[str, bool]]:
    """Return the sorted ``(action, needs_confirmation)`` list for a variant.

    Constructs the variant toolkit with a placeholder device path purely
    to read its ``SUPPORTED_ACTIONS`` table; no device I/O happens at
    construction time.
    """
    toolkit = _toolkit_cls_for(variant)
    return [
        (name, bool(toolkit.SUPPORTED_ACTIONS[name][3]))
        for name in sorted(toolkit.SUPPORTED_ACTIONS)
    ]


def _format_config_actions(selected_variant: Optional[str]) -> str:
    """Build the 'configure actions' help block.

    Lists the actions for ``selected_variant`` when it names a known
    variant; otherwise lists them for every supported variant.
    """
    if selected_variant in TOOLKIT_BY_VARIANT:
        variants = [selected_variant]
    else:
        variants = list(TOOLKIT_BY_VARIANT)

    lines = ["configure actions (use as: configure <action>):"]
    for variant in variants:
        lines.append(f"  {variant}:")
        for name, needs_confirm in _config_actions_for(variant):
            suffix = "  (prompts for confirmation)" if needs_confirm else ""
            lines.append(f"    {name}{suffix}")
    return "\n".join(lines)


def _build_epilog(selected_variant: Optional[str]) -> str:
    """Assemble the full help epilog: command summaries + config actions."""
    lines = ["commands:"]
    for name, description in _COMMAND_DESCRIPTIONS:
        lines.append(f"  {name}")
        lines.append(f"      {description}")
    return "\n".join(lines) + "\n\n" + _format_config_actions(selected_variant)


def create_parser(selected_variant: Optional[str] = None):
    parser = argparse.ArgumentParser(
        description=f"Signaloid C0-SD toolkit. Version {APP_VERSION}",
        epilog=_build_epilog(selected_variant),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=True
    )

    parser.add_argument(
        "target_device",
        help="Target device path"
    )

    parser.add_argument(
        "--variant",
        choices=["C0-microSD+", "C0-SD"],
        default="C0-microSD+",
        help="Hardware variant (default: C0-microSD+)"
    )

    parser.add_argument(
        "--regmap-path",
        default=None,
        help="Path to the regmap package directory for the selected "
             "--variant (defaults to the built-in regmaps)."
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        metavar="<command>"
    )

    p_info = subparsers.add_parser(
        "info",
        help="Print target device info and run bitstream verification."
    )
    p_info.set_defaults(func=handle_info)

    p_status = subparsers.add_parser(
        "status",
        help="Print verbose status (COMMAND, CONFIG, STATUS, "
             "and SD_CONFIG on C0-SD)."
    )
    p_status.set_defaults(func=handle_status)

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

    # Per-variant validation happens in handle_configuration; argparse
    # accepts any string and we print the variant-specific list of
    # available actions on mismatch.
    p_configure = subparsers.add_parser(
        "configure",
        aliases=["config"],
        help="Apply a configuration action (per-variant; "
             "see the action list in the main --help).",
        epilog=_format_config_actions(selected_variant),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p_configure.add_argument(
        "action",
        help="Configuration action to perform "
             "(supported set depends on --variant)"
    )
    p_configure.set_defaults(func=handle_configuration)

    return parser


def _preparse_variant(argv: list[str]) -> Optional[str]:
    """Extract ``--variant`` from ``argv`` to shape the help text.

    Returns the variant only when it names a known one, so the help
    epilog can narrow to that variant; otherwise None (help lists all
    variants). Validation of an unknown value is left to the real parser.
    """
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--variant")
    known, _ = pre.parse_known_args(argv)
    return known.variant if known.variant in TOOLKIT_BY_VARIANT else None


def main(explicit_args: list[str] | None = None):
    argv = list(explicit_args) if explicit_args is not None else sys.argv[1:]
    parser = create_parser(selected_variant=_preparse_variant(argv))
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
