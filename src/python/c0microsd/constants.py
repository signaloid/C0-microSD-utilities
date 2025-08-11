#   Copyright (c) 2025, Signaloid.
#
#   Permission is hereby granted, free of charge, to any person obtaining a
#   copy of this software and associated documentation files (the "Software"),
#   to deal in the Software without restriction, including without limitation
#   the rights to use, copy, modify, merge, publish, distribute, sublicense,
#   and/or sell copies of the Software, and to permit persons to whom the
#   Software is furnished to do so, subject to the following conditions:
#
#   The above copyright notice and this permission notice shall be included in
#   all copies or substantial portions of the Software.
#
#   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#   AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#   FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#   DEALINGS IN THE SOFTWARE.

from dataclasses import dataclass


@dataclass
class BootloaderConfig:
    kBootloaderSwitchConfigOffset: int
    kBootloaderUnlockOffset: int
    kBootloaderBitstreamOffset: int
    kSOCBitstreamOffset: int
    kUserBitstreamOffset: int
    kUserDataOffset: int
    kSerialNumberOffset: int
    kSerialNumberSize: int
    kUUIDOffset: int
    kUUIDSize: int
    kBootloaderUnlockWord: bytes
    kWamrbootTemplate: str
    kBitstreamPrefixStart: bytes
    kBitstreamPrefixEnd: bytes


@dataclass
class SocConfig:
    kMosiBufferSizeBytes: int
    kMisoBufferSizeBytes: int
    kStatusRegisterOffset: int
    kSOCControlRegisterOffset: int
    kCommandRegisterOffset: int
    kMOSIBufferOffset: int
    kMISOBufferOffset: int


BOOTLOADER_CONSTANTS = {
    1: BootloaderConfig(
        kBootloaderSwitchConfigOffset=0x40000,
        kBootloaderUnlockOffset=0x60000,
        kBootloaderBitstreamOffset=0x80000,
        kSOCBitstreamOffset=0x100000,
        kUserBitstreamOffset=0x180000,
        kUserDataOffset=0x200000,
        kSerialNumberOffset=0x22040,
        kSerialNumberSize=0x40,
        kUUIDOffset=0x22080,
        kUUIDSize=0x40,
        kBootloaderUnlockWord=b"UBLD",
        kWamrbootTemplate=(
            "7eaa997e920000440308000082000001"
            "08000000000000000000000000000000"
            "7eaa997e920000440308000082000001"
            "08000000000000000000000000000000"
            "7eaa997e920000440310000082000001"
            "08000000000000000000000000000000"
            "7eaa997e920000440318000082000001"
            "08000000000000000000000000000000"
            "7eaa997e920000440308000082000001"
            "08000000000000000000000000000000"
        ),
        kBitstreamPrefixStart=b'\xFF\x00',
        kBitstreamPrefixEnd=b'\x00\xFF'
    ),
    2: BootloaderConfig(
        kBootloaderSwitchConfigOffset=0xF80000,
        kBootloaderUnlockOffset=0x60000,
        kBootloaderBitstreamOffset=0x80000,
        kSOCBitstreamOffset=0x100000,
        kUserBitstreamOffset=0x200000,
        kUserDataOffset=0x280000,
        kSerialNumberOffset=0x22040,
        kSerialNumberSize=0x40,
        kUUIDOffset=0x22080,
        kUUIDSize=0x40,
        kBootloaderUnlockWord=b"UBLD",
        kWamrbootTemplate=(
            "7eaa997e920000440308000082000001"
            "08000000000000000000000000000000"
            "7eaa997e920000440308000082000001"
            "08000000000000000000000000000000"
            "7eaa997e920000440310000082000001"
            "08000000000000000000000000000000"
            "7eaa997e920000440318000082000001"
            "08000000000000000000000000000000"
            "7eaa997e920000440320000082000001"
            "08000000000000000000000000000000"
        ),
        kBitstreamPrefixStart=b'\xFF\x00',
        kBitstreamPrefixEnd=b'\x7E\xAA\x99\x7E'
    )
}

SOC_CONSTANTS = {
    1: SocConfig(
        kMosiBufferSizeBytes=4096,
        kMisoBufferSizeBytes=4096,
        kStatusRegisterOffset=0x00000,
        kSOCControlRegisterOffset=0x00004,
        kCommandRegisterOffset=0x10000,
        kMOSIBufferOffset=0x50000,
        kMISOBufferOffset=0x60000
    ),
    2: SocConfig(
        kMosiBufferSizeBytes=4096,
        kMisoBufferSizeBytes=4096,
        kStatusRegisterOffset=0x00000,
        kSOCControlRegisterOffset=0x00004,
        kCommandRegisterOffset=0x10000,
        kMOSIBufferOffset=0x50000,
        kMISOBufferOffset=0x60000
    )
}
