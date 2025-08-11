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


try:
    from typing import List, Union
except:
    pass

from busio import SPI
from microcontroller import Pin

from c0microsd.sd_interface import C0microSDSignaloidSoCInterface
from c0microsd.sd_protocol import SDOverSPI


class C0microSDSignaloidSoCInterfaceSDSPI(C0microSDSignaloidSoCInterface):
    """Communication interface for C0-microSD over SPI.

    This class provides basic functionality for interfacing with the
    Signaloid C0-microSD through the SD SPI interface.
    """

    def __init__(self, spi: SPI, cs_pin: Pin, timeout: int, force_transactions: bool = False) -> None:
        super().__init__(
            target_device="",
            force_transactions=force_transactions
        )

        self.sd: SDOverSPI = SDOverSPI(
            spi=spi,
            cs_pin=cs_pin,
            timeout=timeout
        )

    def _read(self, offset: int, bytes: int) -> bytes:
        """Reads data from the C0-microSD.

        :return: The read buffer
        """
        if bytes % 512 == 0:
            num_blocks = bytes // 512
        else:
            num_blocks = bytes // 512 + 1
        data = self.sd.read_blocks(offset, num_blocks)
        return data[0:bytes]

    def _write(self, offset: int, data: Union[List[int], bytes, bytearray]) -> int:
        """Writes data to the C0-microSD.

        :param buffer: The data buffer to write.
        :return: Number of bytes written.
        """
        # Pad the data to 512 bytes
        if len(data) % 512:
            remaining_bytes = 512 - (len(data) % 512)
            data += bytes(remaining_bytes)

        return self.sd.write_blocks(offset, data)
