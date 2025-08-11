#   Copyright (c) 2024, Signaloid.
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
    from typing import Callable, List, Optional, Union
except:
    pass

import digitalio
from busio import SPI
from microcontroller import Pin


class SDOverSPI:
    class CMDs:
        """
        SD card command codes.

        Not all commands are supported by the Signaloid C0-microSD.
        """
        CMD0_GO_IDLE_STATE = 0
        CMD1_SEND_OP_COND = 1
        CMD6_SWITCH_FUNC = 6
        CMD8_SEND_IF_COND = 8
        CMD9_SEND_CSD = 9
        CMD10_SEND_CID = 10
        CMD12_STOP_TRANSMISSION = 12
        CMD13_SEND_STATUS = 13
        CMD16_SET_BLOCKLEN = 16
        CMD17_READ_SINGLE_BLOCK = 17
        CMD18_READ_MULTIPLE_BLOCK = 18
        CMD24_WRITE_BLOCK = 24
        CMD25_WRITE_MULTIPLE_BLOCK = 25
        CMD27_PROGRAM_CSD = 27
        CMD28_SET_WRITE_PROT = 28
        CMD29_CLR_WRITE_PROT = 29
        CMD30_SEND_WRITE_PROT = 30
        CMD32_ERASE_WR_BLK_START_ADDR = 32
        CMD33_ERASE_WR_BLK_END_ADDR = 33
        CMD38_ERASE = 38
        CMD42_LOCK_UNLOCK = 42
        CMD55_APP_CMD = 55
        CMD56_GEN_CMD = 56
        CMD58_READ_OCR = 58
        CMD59_CRC_ON_OFF = 59
        ACMD13_SD_STATUS = 13
        ACMD22_SEND_NUM_WR_BLOCKS = 22
        ACMD23_SET_WR_BLK_ERASE_COUNT = 23
        ACMD41_SD_SEND_OP_COND = 41
        ACMD42_SET_CLR_CARD_DETECT = 42
        ACMD51_SEND_SCR = 51

    class RESPONSES:
        """SD card response codes."""
        BUSY = 0x00
        READY = 0xfe
        R1_IN_IDLE_STATE = 0x01
        R1_INITIALIZED = 0x00

    class CONTROL_TOKENS:
        """SD card control tokens."""
        CMD17_START_BLOCK_TOKEN = 0b11111110
        CMD18_START_BLOCK_TOKEN = 0b11111110
        CMD24_START_BLOCK_TOKEN = 0b11111110
        CMD25_START_BLOCK_TOKEN = 0b11111100
        CMD25_STOP_BLOCK_TOKEN  = 0b11111101

    def __init__(self, spi: SPI, cs_pin: Pin, timeout: int = 1000, dummy_bytes_count: int = 2) -> None:
        """
        Initializes the SD card interface.

        :param spi: The SPI bus to use for communication.
        :param cs_pin: The pin to use for the chip select signal.
        :param timeout: The timeout for communication in times of retries.
        :param dummy_bytes_count: The number of dummy bytes to send whenever
                                    needed.
        """
        self.timeout = timeout
        self.dummy_bytes_count = dummy_bytes_count

        self.spi = spi

        # Initialize the chip select pin as an output and set it to high
        self.cs = digitalio.DigitalInOut(cs_pin)
        self.cs.direction = digitalio.Direction.OUTPUT
        self.cs.value = True

        self.init_cmd_tables()

        self.init()

    @staticmethod
    def CRC7(data_arr: Union[List[int], bytes, bytearray]) -> int:
        """
        Calculates the CRC7 of a byte array.

        :param data_arr: The byte array to calculate the CRC7 of.

        :return: The CRC7 of the byte array.
        """

        CRC = [0] * 7
        data_out = 0

        for i in range(len(data_arr)):
            data = data_arr[i]

            for j in range(8):
                data_in = (data >> (7 - j)) & 0b1

                data_out = CRC[6]
                data_in_after_xor = data_in ^ data_out

                CRC[6] = CRC[5]
                CRC[5] = CRC[4]
                CRC[4] = CRC[3]
                CRC[3] = CRC[2] ^ data_in_after_xor
                CRC[2] = CRC[1]
                CRC[1] = CRC[0]
                CRC[0] = data_in_after_xor

        crc7 = 0
        for i in range(7):
            crc7 |= CRC[i] << i

        return crc7

    @staticmethod
    def CRC16(data_arr: Union[List[int], bytes, bytearray]) -> bytearray:
        """
        Calculates the CRC16 of a byte array.

        :param data_arr: The byte array to calculate the CRC16 of.

        :return: The CRC16 of the byte array.
        """

        CRC = [0] * 16
        data_out = 0

        for i in range(len(data_arr)):
            data = data_arr[i]

            for j in range(8):
                data_in = (data >> (7 - j)) & 0b1

                data_out = CRC[15]
                data_in_after_xor = data_in ^ data_out

                CRC[15] = CRC[14]
                CRC[14] = CRC[13]
                CRC[13] = CRC[12]
                CRC[12] = CRC[11] ^ data_in_after_xor
                CRC[11] = CRC[10]
                CRC[10] = CRC[9]
                CRC[9] = CRC[8]
                CRC[8] = CRC[7]
                CRC[7] = CRC[6]
                CRC[6] = CRC[5]
                CRC[5] = CRC[4] ^ data_in_after_xor
                CRC[4] = CRC[3]
                CRC[3] = CRC[2]
                CRC[2] = CRC[1]
                CRC[1] = CRC[0]
                CRC[0] = data_in_after_xor

        crc16 = bytearray(2)
        for i in range(8):
            crc16[1] |= CRC[i] << i
            crc16[0] |= CRC[i + 8] << i

        return crc16

    @staticmethod
    def test_crc() -> None:
        """
        Tests the CRC7 and CRC16 functions.
        """

        crc7 = SDOverSPI.CRC7([0x40, 0x00, 0x00, 0x00, 0x00])
        correct_crc7 = 0x4a
        assert crc7 == correct_crc7, "CRC7 test failed."

        crc16 = SDOverSPI.CRC16([0xff]*512)
        correct_crc16 = bytearray([0x7f, 0xa1])
        assert crc16 == correct_crc16, "CRC16 test failed."

    @staticmethod
    def raw_data_to_hex_str(data: Optional[Union[List[int], bytes, bytearray]]) -> str:
        """
        Converts a byte array to a hex string representation.

        :param data: The byte array to convert.

        :return: The hex string representation of the byte array.
        """

        if data is None:
            return '[]'

        return '[' + ':'.join('{:02x}'.format(x) for x in data) + ']'

    @staticmethod
    def generate_cmd(cmd_index: int, arguments: Union[List[int], bytes, bytearray]) -> bytearray:
        """
        Generates a command byte array for a SD card command ready to be sent
        through the SPI bus.

        :param cmd_index: The command index.
        :param arguments: The command arguments.

        :return: The command byte array.
        """

        start_bit = 0b0
        transmission_bit = 0b1
        end_bit = 0b1

        cmd_byte_arr = bytearray(5)

        cmd_byte_arr[0] = cmd_index
        cmd_byte_arr[0] |= start_bit << 7
        cmd_byte_arr[0] |= transmission_bit << 6

        cmd_byte_arr[1] = arguments[0]
        cmd_byte_arr[2] = arguments[1]
        cmd_byte_arr[3] = arguments[2]
        cmd_byte_arr[4] = arguments[3]

        crc7 = SDOverSPI.CRC7(cmd_byte_arr)

        crc7_byte = crc7 << 1 | end_bit
        cmd_byte_arr.append(crc7_byte)

        return cmd_byte_arr

    def read_bytes(self, num_bytes: int) -> bytearray:
        """
        Reads a number of bytes from the SD card.

        :param num_bytes: The number of bytes to read.

        :return: The read bytes.
        """

        result=bytearray(num_bytes)
        self.spi.write_readinto(bytearray([0xff]*len(result)), result)
        return result

    def wait_response(
        self,
        expected_responses: Optional[List[int]] = None,
        timeout: Optional[int] = None
    ) -> bytearray:
        """
        Waits for a response from the SD card.

        If expected responses are provided, it waits for one of the expected
        responses, until the timeout is reached.
        If no expected responses are provided, it waits for a single byte
        response.

        If a timeout is provided, it replaces the default number of retries.

        :param expected_responses: The expected responses.
        :param timeout: The timeout for the wait.

        :return: The response received.
        """

        if timeout is None:
            timeout = self.timeout

        if expected_responses is None:
            return self.read_bytes(1)

        res = bytearray([0xff])
        for _ in range(self.timeout):
            res = self.read_bytes(1)
            if res[0] in expected_responses:
                break

        return res

    def wait_busy(self) -> None:
        """
        Waits while the SD card is busy.
        """
        hasBeenBusy = 0
        while True:
            if self.read_bytes(1)[0] == SDOverSPI.RESPONSES.BUSY:
                hasBeenBusy += 1
                continue

            if hasBeenBusy:
                break

    def wait_ready(self) -> bytearray:
        """
        Waits for the SD card to respond with a READY response.
        """
        return self.wait_response(expected_responses=[SDOverSPI.RESPONSES.READY])

    def get_R1(self) -> bytearray:
        """
        Tries to read a valid R1 type response from the SD card, until the
        timeout is reached.

        :return: The R1 response.
        """
        result = bytearray([0xff])
        for _ in range(self.timeout):
            result = self.read_bytes(1)
            if result[0] != 0xff:
                break
        return result

    def get_R1b(self) -> bytearray:
        """
        Tries to read a valid R1b type response from the SD card, until the
        timeout is reached.

        :return: The R1b response.
        """
        result = bytearray([0xff])
        for _ in range(self.timeout):
            result = self.read_bytes(1)
            if result[0] != 0xff:
                break

        return result

    def get_R2(self) -> bytearray:
        """
        Reads a valid R2 response from the SD card.

        :return: The R2 response.
        """

        result = self.get_R1()
        result.extend(self.read_bytes(1))
        return result

    def get_R3(self) -> bytearray:
        """
        Reads a valid R3 response from the SD card.

        :return: The R3 response.
        """

        result = self.get_R1()
        result.extend(self.read_bytes(4))
        return result

    def get_R7(self) -> bytearray:
        """
        Reads a valid R7 response from the SD card.

        :return: The R7 response.
        """

        result = self.get_R1()
        result.extend(self.read_bytes(4))
        return result

    def init_cmd_tables(self) -> None:
        """
        Initializes the command response tables.
        """
        self.CMD_RESP_TABLE: List[Optional[Callable[[SDOverSPI], bytearray]]] = [
            SDOverSPI.get_R1, SDOverSPI.get_R1, None, None, None, None, SDOverSPI.get_R1, None,
            SDOverSPI.get_R7, SDOverSPI.get_R1, SDOverSPI.get_R1, None, SDOverSPI.get_R1b, SDOverSPI.get_R2, None,
            None, SDOverSPI.get_R1, SDOverSPI.get_R1, SDOverSPI.get_R1, None, None, None, None,
            None, SDOverSPI.get_R1, SDOverSPI.get_R1, None, SDOverSPI.get_R1, SDOverSPI.get_R1b,
            SDOverSPI.get_R1b, SDOverSPI.get_R1, None, SDOverSPI.get_R1, SDOverSPI.get_R1, None, None,
            None, None, SDOverSPI.get_R1b, None, None, None, SDOverSPI.get_R1, None, None,
            None, None, None, None, None, None, None, None, None, None,
            SDOverSPI.get_R1, SDOverSPI.get_R1, None, SDOverSPI.get_R3, SDOverSPI.get_R1, None, None, None,
            None
        ]

        self.ACMD_RESP_TABLE: List[Optional[Callable[[SDOverSPI], bytearray]]] = [
            None, None, None, None, None, None, None, None, None, None, None,
            None, None, SDOverSPI.get_R2, None, None, None, None, None, None, None,
            None, SDOverSPI.get_R1, SDOverSPI.get_R1, None, None, None, None, None, None,
            None, None, None, None, None, None, None, None, None, None, None,
            SDOverSPI.get_R1, SDOverSPI.get_R1, None, None, None, None, None, None, None,
            None, SDOverSPI.get_R1, None, None, None, None, None, None, None, None,
            None, None, None, None
        ]

    def write_bytes(self, data: Union[List[int], bytes, bytearray]) -> None:
        """
        Writes a byte array to the SD card.

        :param data: The byte array to write.
        """

        self.spi.write(data)

    def send_dummy_bytes(self, num_bytes: Optional[int] = None) -> None:
        """
        Sends a number of dummy bytes to the SD card.

        :param num_bytes: The number of dummy bytes to send, overrides the
        default number of dummy bytes.
        """

        if num_bytes is None:
            num_bytes = self.dummy_bytes_count

        self.spi.write(bytearray([0xff]*num_bytes))

    def send_single_cmd(
        self,
        cmd_index: int,
        arguments: Optional[Union[List[int], bytes, bytearray]] = None
    ) -> Optional[bytearray]:
        """
        Sends a single CMD to the SD card, and returns the corresponding
        response.

        :param cmd_index: The command index.
        :param arguments: The command arguments.

        :return: The response received.
        """
        if arguments is None:
            arguments = bytes(4)

        cmd = SDOverSPI.generate_cmd(cmd_index, arguments)
        self.spi.write(cmd)

        response_func = self.CMD_RESP_TABLE[cmd_index]
        if response_func is None:
            return None

        res = response_func(self)

        return res

    def send_single_acmd(
        self,
        cmd_index: int,
        arguments: Optional[Union[List[int], bytes, bytearray]] = None
    ) -> Optional[bytearray]:
        """
        Sends a single ACMD to the SD card, and returns the corresponding
        response.

        :param cmd_index: The command index.
        :param arguments: The command arguments.

        :return: The response received.
        """
        if arguments is None:
            arguments = bytes(4)

        self.send_cmd(
            cmd_index=SDOverSPI.CMDs.CMD55_APP_CMD,
            loop_until_expected_response=[
                SDOverSPI.RESPONSES.R1_IN_IDLE_STATE,
                SDOverSPI.RESPONSES.R1_INITIALIZED,
            ]
        )

        self.send_dummy_bytes()

        cmd = SDOverSPI.generate_cmd(cmd_index, arguments)
        self.spi.write(cmd)

        response_func = self.ACMD_RESP_TABLE[cmd_index]

        if response_func is None:
            return None

        res = response_func(self)

        return res

    def send_cmd(
        self,
        cmd_index: int,
        arguments: Optional[Union[List[int], bytes, bytearray]] = None,
        loop_until_expected_response: Optional[List[int]] = None,
        timeout: Optional[int] = None
    ) -> Optional[bytearray]:
        """
        Sends a CMD to the SD card, and waits for the corresponding response.

        If loop_until_expected_response is provided, it waits for one of the
        expected responses, until the timeout is reached.
        If no loop_until_expected_response is provided, it only sends a single
        CMD and waits for a single response.

        If a timeout is provided, it replaces the default number of retries.

        :param cmd_index: The command index.
        :param arguments: The command arguments.
        :param loop_until_expected_response: The expected responses.
        :param timeout: The number of retries.

        :return: The response received.
        """
        if arguments is None:
            arguments = bytes(4)

        if timeout is None:
            timeout = self.timeout

        if loop_until_expected_response is None:
            timeout = 1
            loop_until_expected_response = []

        res = bytearray([0xff])
        for _ in range(timeout):
            res = self.send_single_cmd(cmd_index, arguments)

            if res is not None and res[0] in loop_until_expected_response:
                break

            self.send_dummy_bytes()

        return res

    def send_acmd(
        self,
        cmd_index: int,
        arguments: Optional[Union[List[int], bytes, bytearray]] = None,
        loop_until_expected_response: Optional[List[int]] = None,
        timeout: Optional[int] = None
    ) -> Optional[bytearray]:
        """
        Sends an ACMD to the SD card, and waits for the corresponding response.

        If loop_until_expected_response is provided, it waits for one of the
        expected responses, until the timeout is reached.
        If no loop_until_expected_response is provided, it only sends a single
        ACMD and waits for a single response.

        If a timeout is provided, it replaces the default number of retries.

        :param cmd_index: The command index.
        :param arguments: The command arguments.
        :param loop_until_expected_response: The expected responses.
        :param timeout: The number of retries.

        :return: The response received.
        """

        if timeout is None:
            timeout = self.timeout

        if loop_until_expected_response is None:
            timeout = 1
            loop_until_expected_response = []

        for _ in range(timeout):
            res = self.send_single_acmd(cmd_index, arguments)

            if res is not None and res[0] in loop_until_expected_response:
                break

            self.send_dummy_bytes()

        return res

    def init(self) -> None:
        """
        Initializes the SD card to the SPI mode.
        """
        while self.spi.try_lock():
            pass

        try:
            self.cs.value = False

            # Send dummy bytes to clear the SPI bus
            self.send_dummy_bytes()

            # Send CMD0 to go to idle state
            self.send_cmd(
                cmd_index=SDOverSPI.CMDs.CMD0_GO_IDLE_STATE,
                loop_until_expected_response=[SDOverSPI.RESPONSES.R1_IN_IDLE_STATE]
            )
            self.send_dummy_bytes()

            # Send ACMD41 to send the operating condition register
            args = 0x40000000
            args = args.to_bytes(4, 'big')
            self.send_acmd(
                cmd_index=SDOverSPI.CMDs.ACMD41_SD_SEND_OP_COND,
                arguments=args,
                loop_until_expected_response=[SDOverSPI.RESPONSES.R1_INITIALIZED]
            )
            self.send_dummy_bytes()

            # Send CMD16 to set block length to 512 bytes
            args = 0x0200
            args = args.to_bytes(4, 'big')
            self.send_cmd(
                cmd_index=SDOverSPI.CMDs.CMD16_SET_BLOCKLEN,
                arguments=args,
                loop_until_expected_response=[SDOverSPI.RESPONSES.R1_INITIALIZED]
            )
            self.send_dummy_bytes()

        finally:
            self.send_dummy_bytes()

            self.cs.value = True
            self.spi.unlock()

    def read_blocks(self, address: int, num_blocks: int) -> bytearray:
        """
        Reads a number of blocks from the SD card.

        :param address: The address to read from.
        :param num_blocks: The number of blocks to read.

        :return: The read bytes.
        """

        address_bytes = address.to_bytes(4, 'big')

        cmd_index = SDOverSPI.CMDs.CMD17_READ_SINGLE_BLOCK if num_blocks == 1 else SDOverSPI.CMDs.CMD18_READ_MULTIPLE_BLOCK

        while self.spi.try_lock():
            pass

        try:
            self.cs.value = False

            self.send_cmd(
                cmd_index=cmd_index,
                arguments=address_bytes,
                loop_until_expected_response=[SDOverSPI.RESPONSES.R1_INITIALIZED]
            )

            data = bytearray()
            for _ in range(num_blocks):
                # Wait for start block token
                self.wait_ready()

                # Read the data
                res = self.read_bytes(512)

                # Check CRC16
                res_crc16 = self.read_bytes(2)
                correct_crc16 = SDOverSPI.CRC16(res)
                if res_crc16 != correct_crc16:
                    raise RuntimeError(
                        f"""
                            CRC16 received: 0x{res_crc16[0]:02x},
                            0x{res_crc16[1]:02x}\n
                            CRC16 calculated: 0x{correct_crc16[0]:02x},
                            0x{correct_crc16[1]:02x}
                        """
                    )
                    data = None
                    break

                data.extend(res)
        finally:
            if num_blocks > 1:
                res = self.send_cmd(cmd_index=SDOverSPI.CMDs.CMD12_STOP_TRANSMISSION)

            self.send_dummy_bytes()

            self.cs.value = True
            self.spi.unlock()
        return data

    def write_blocks(self, address: int, blocks: Union[List[int], bytes, bytearray]) -> int:
        """
        Writes a number of blocks to the SD card.

        :param address: The address to write to.
        :param blocks: The blocks to write.

        :return: The number of blocks written.
        """

        address_bytes = address.to_bytes(4, 'big')

        cmd_index = SDOverSPI.CMDs.CMD24_WRITE_BLOCK
        start_block = SDOverSPI.CONTROL_TOKENS.CMD24_START_BLOCK_TOKEN

        num_blocks = len(blocks) // 512
        if num_blocks > 1:
            cmd_index = SDOverSPI.CMDs.CMD25_WRITE_MULTIPLE_BLOCK
            start_block = SDOverSPI.CONTROL_TOKENS.CMD25_START_BLOCK_TOKEN

        start_block = start_block.to_bytes(1, 'big')

        while self.spi.try_lock():
            pass

        try:
            self.cs.value = False
            count = 0

            self.send_cmd(
                cmd_index=cmd_index,
                arguments=address_bytes,
                loop_until_expected_response=[SDOverSPI.RESPONSES.R1_INITIALIZED]
            )

            for i in range(num_blocks):
                self.send_dummy_bytes()

                self.write_bytes(start_block)

                data = blocks[i*512:(i+1)*512]
                self.write_bytes(data)

                crc16 = SDOverSPI.CRC16(data)
                self.write_bytes(crc16)

                # Data response token
                resp = self.read_bytes(1)
                resp = resp[0]
                resp &= 0b00011111

                if resp == 0b00000101:
                    count += 1
                elif resp == 0b00001011:
                    raise RuntimeError("SD SPI Write error: rejected CRC")
                elif resp == 0b00001101:
                    raise RuntimeError("SD SPI Write error: rejected write")
                else:
                    raise RuntimeError(f"SD SPI Write error: 0x{resp:02x}")

                self.wait_busy()

        finally:
            if num_blocks > 1:
                stop_block = SDOverSPI.CONTROL_TOKENS.CMD25_STOP_BLOCK_TOKEN
                stop_block = stop_block.to_bytes(1, 'big')
                self.write_bytes(stop_block)
                self.wait_busy()

            self.cs.value = True
            self.spi.unlock()

        return count

    def test_rw(self) -> None:
        """
        Tests the read and write operations.

        It reads the first 3 blocks of the SD card, increments the first byte
        of the first block, and writes the incremented data to the first 2
        blocks of the SD card. It then reads the first 2 blocks of the SD card,
        and compares the read data with the written data.
        """

        read_data = self.read_blocks(0, 3)

        new_value = (read_data[0] + 1) & 0xff
        num_blocks = 2
        write_data = bytearray([new_value] * (512 * num_blocks))
        self.write_blocks(0, write_data)

        read_data = self.read_blocks(0, num_blocks)

        assert read_data == write_data, "Read data does not match written data."
