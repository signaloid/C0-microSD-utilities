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

"""Read and decode the JSON metadata prefix of a Signaloid bitstream.

Two Lattice FPGA families frame the metadata differently:

* **Nexus / LIFCL** (C0-microSD+, C0-SD): an ``LSCC`` header, ``FF 00``
  comment framing, the JSON payload, a ``NUL`` terminator, then the
  ``0xFFFFBDB3`` config preamble.
* **iCE40** (the original C0-microSD): ``FF 00`` framing followed by the
  ``7E AA 99 7E`` config sync word.

Pure ``bytes``-in/``bytes``-out, so it can be exercised without hardware.
"""

from __future__ import annotations

import json
import zlib
from dataclasses import dataclass
from typing import Any


def crc32(data: bytes) -> int:
    """Return the unsigned 32-bit CRC-32 of ``data``.

    ``zlib.crc32`` and ``binascii.crc32`` compute the identical checksum;
    this is the single CRC function shared across the toolchain.
    """
    return zlib.crc32(data) & 0xFFFFFFFF


@dataclass(frozen=True)
class PrefixProfile:
    """Per-FPGA-family framing of the bitstream metadata prefix.

    Attributes:
        key: Short profile name (``"nexus"`` / ``"ice40"``).
        signature: Bytes expected at offset 0, or ``None`` if the family has
            no leading signature.
        start_marker: Bytes immediately preceding the JSON payload.
        end_marker: Bytes immediately following the JSON payload; the
            CRC-covered region begins right after it.
        default_fixed_length: Whether the prefix section is padded to its
            original size by default (True for iCE40, False for Nexus). Used
            only by the write side.
        crc_key / size_key: JSON keys under which the payload CRC and size
            are stored for this family. Used only by the write side.
    """

    key: str
    signature: bytes | None
    start_marker: bytes
    end_marker: bytes
    default_fixed_length: bool
    crc_key: str
    size_key: str


NEXUS = PrefixProfile(
    key="nexus",
    signature=b"LSCC",
    start_marker=b"\xFF\x00",
    end_marker=b"\x00\xFF",
    default_fixed_length=False,
    crc_key="bitstream_crc",
    size_key="bitstream_size",
)

ICE40 = PrefixProfile(
    key="ice40",
    signature=None,
    start_marker=b"\xFF\x00",
    end_marker=b"\x7E\xAA\x99\x7E",
    default_fixed_length=True,
    crc_key="crc",
    size_key="size",
)

# Canonical compute-module-type string -> prefix profile.
PROFILE_BY_MODULE: dict[str, PrefixProfile] = {
    "C0-microSD": ICE40,
    "C0-microSD+": NEXUS,
    "C0-SD": NEXUS,
}

# Number of bytes an on-device reader reads to locate the prefix. The
# injection tool refuses to produce a prefix whose end marker falls beyond
# this window, so a tool-written bitstream is always readable on-device.
COMMENT_WINDOW_BYTES = 4096


def locate_prefix(
    data: bytes, profile: PrefixProfile
) -> tuple[int, int, int]:
    """Return ``(prefix_start, prefix_end, crc_start)`` byte offsets.

    ``data[prefix_start:prefix_end]`` is the metadata payload (the bytes
    between the framing markers, excluding both). ``data[crc_start:]`` is
    the CRC-covered region (everything after the end marker).

    Raises:
        ValueError: if the profile's signature or either marker is absent
            (e.g. the file does not match the given compute-module type).
    """
    if profile.signature is not None and not data.startswith(
        profile.signature
    ):
        raise ValueError(
            f"missing {profile.key} signature {profile.signature!r} "
            "at start of bitstream"
        )

    start = data.find(profile.start_marker)
    if start == -1:
        raise ValueError(
            f"{profile.key} start marker {profile.start_marker!r} not found"
        )
    prefix_start = start + len(profile.start_marker)

    prefix_end = data.find(profile.end_marker, prefix_start)
    if prefix_end == -1:
        raise ValueError(
            f"{profile.key} end marker {profile.end_marker!r} not found"
        )

    crc_start = prefix_end + len(profile.end_marker)
    return prefix_start, prefix_end, crc_start


def find_json_object(data: bytes) -> dict[str, Any] | None:
    """Return the first top-level JSON object in ``data``.

    Attempts to decode a JSON value starting at each ``{`` using the
    standard-library decoder, which correctly honours string literals and
    escapes -- so braces inside string values (e.g. ``{"note": "a}b"}``)
    do not confuse the scan. Surrounding non-JSON bytes such as padding
    spaces are ignored. Returns ``None`` if no JSON object is present.

    """
    ascii_str = data.decode("ascii", errors="ignore")
    decoder = json.JSONDecoder()

    index = ascii_str.find("{")
    while index != -1:
        try:
            decoded, _ = decoder.raw_decode(ascii_str, index)
        except json.JSONDecodeError:
            decoded = None
        if isinstance(decoded, dict):
            return decoded
        index = ascii_str.find("{", index + 1)
    return None


def read_prefix_json(data: bytes, profile: PrefixProfile) -> dict[str, Any]:
    """Decode the JSON metadata object embedded in the prefix.

    Raises:
        ValueError: if the framing is missing or the payload contains no
            valid JSON object.
    """
    prefix_start, prefix_end, _ = locate_prefix(data, profile)
    obj = find_json_object(data[prefix_start:prefix_end])
    if obj is None:
        raise ValueError("no JSON metadata object found in bitstream prefix")
    return obj
