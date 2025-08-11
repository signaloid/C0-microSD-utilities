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

import struct
import time
from typing import Tuple

SIGNALOID_SOC_STATUS_WAIT_FOR_COMMAND = 0
SIGNALOID_SOC_STATUS_CALCULATING = 1
SIGNALOID_SOC_STATUS_DONE = 2
SIGNALOID_SOC_STATUS_INVALID_COMMAND = 3

K_CALCULATE_NO_COMMAND = 0


class C0microSDPlusInterface:
    """Communication interface for C0-microSD+.

    This class provides basic functionality for interfacing with the
    Signaloid C0-microSD+ and the built-in Signaloid SoC.
    """
    BITSTREAM_OFFSET = 0x00000000
    BOOTLOADER_OFFSET = 0x00100000
    APPLICATION_BINARY_OFFSET = 0x00180000

    COMMAND_REGISTER_OFFSET = 0x01000000
    CONFIG_REGISTER_OFFSET = 0x01000004
    BOOT_ADDRESS_REGISTER_OFFSET = 0x01000008
    STATUS_REGISTER_OFFSET = 0x0100000C

    MMIO_BUFFER_SIZE_BYTES = 8192
    MMIO_BUFFER_OFFSET = 0x01004000

    def __init__(
            self, target_device: str,
            force_transactions: bool = False
            ) -> None:

        self.target_device = target_device
        self.force_transactions = force_transactions

    def _read(self, offset, bytes) -> bytes:
        """
        Reads data from the C0-microSD+.

        :return: The read buffer
        """
        try:
            with open(self.target_device, "rb") as device:
                device.seek(offset)
                return device.read(bytes)
        except PermissionError:
            raise PermissionError(
                "Permission denied: You do not have the "
                f"necessary permissions to access {self.target_device}. "
                "Try running this application with root privileges."
            )
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Device not found: The device {self.target_device} "
                "does not exist."
            )

    def _write(self, offset, data) -> int:
        """
        Write data to the C0-microSD+.

        :param buffer: The data buffer to write.
        :return: Number of bytes written.
        """
        try:
            with open(self.target_device, "wb") as device:
                device.seek(offset)
                return device.write(data)

        except PermissionError:
            raise PermissionError(
                "Permission denied: You do not have the "
                f"necessary permissions to access {self.target_device}. "
                "Try running this application with root privileges."
            )
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Device not found: The device {self.target_device} "
                "does not exist."
            )

    def __str__(self) -> str:
        value = "Signaloid C0-microSD+"
        return value

    def write_MMIO_buffer(self, buffer: bytes) -> None:
        """
        Writes data to the C0-microSD+ MMIO buffer.

        :param buffer: The data buffer to write.
        """
        if len(buffer) > self.MMIO_BUFFER_SIZE_BYTES:
            raise ValueError(
                "Buffer size exceeds maximum allowed "
                f"size of {self.MMIO_BUFFER_SIZE_BYTES} bytes."
            )

        self._write(self.MMIO_BUFFER_OFFSET, buffer)

    def read_MMIO_buffer(
        self,
        size: int = MMIO_BUFFER_SIZE_BYTES
    ) -> bytes:
        """
        Reads data from the C0-microSD+ MMIO buffer.

        :param size: Size in bytes of data to read.

        :return: The read buffer
        """

        if size > self.MMIO_BUFFER_SIZE_BYTES:
            raise ValueError(
                "Read MMIO size exceeds"
                f" {self.MMIO_BUFFER_SIZE_BYTES} bytes."
            )
        return self._read(self.MMIO_BUFFER_OFFSET, size)

    def set_config_register(self, value: int) -> None:
        """
        Set the config register of the the C0-microSD+.

        :param value: The uint32_t value to write
        """
        # Pack the uint32_t value into a 4-byte buffer and send it
        self._write(self.CONFIG_REGISTER_OFFSET, struct.pack("I", value))

    def get_config_register(self) -> int:
        """
        Get the config register of the the C0-microSD+ Signaloid SoC.

        :return: The read uint32_t value
        """
        buffer = self._read(self.CONFIG_REGISTER_OFFSET, 4)
        # Unpack the buffer to get the uint32_t value
        return struct.unpack("I", buffer)[0]

    def get_config_register_unpacked(
            self) -> Tuple[bool, bool, bool, bool]:
        """
            Fetches the configuration register value from the device
            and unpacks it into individual boolean fields.

            :return: A tuple containing:
                    (rstn, unlock_bitstream_section, sw_led_enable, sw_led)
                    where each element is a boolean.
        """
        reg_val = self.get_config_register()

        # Unpack individual bits from the register value
        rstn = bool((reg_val >> 0) & 0x1)
        unlock_bitstream_section = bool((reg_val >> 1) & 0x1)
        sw_led_enable = bool((reg_val >> 2) & 0x1)
        sw_led = bool((reg_val >> 3) & 0x1)

        return rstn, unlock_bitstream_section, sw_led_enable, sw_led

    def set_config_register_unpacked(
        self,
        rstn: bool,
        unlock_bitstream_section: bool,
        sw_led_enable: bool,
        sw_led: bool
    ):
        """
            Packs individual boolean values into a configuration register and
            writes the register back to the device.

            :param device: Identifier of the device.
            :param rstn: State of the reset signal.
            :param unlock_bitstream_section: Unlock bitstream section.
            :param sw_led_enable: State of the software LED enable.
            :param sw_led: State of the software LED.
        """
        # Initialize the register value
        reg_val = 0

        reg_val |= (int(rstn) & 0x1) << 0
        reg_val |= (int(unlock_bitstream_section) & 0x1) << 1
        reg_val |= (int(sw_led_enable) & 0x1) << 2
        reg_val |= (int(sw_led) & 0x1) << 3

        # Write the register value back to the device
        self.set_config_register(reg_val)

    def set_boot_address(self, value: int) -> None:
        """
        Set the boot address of the the C0-microSD+ Signaloid SoC.

        :param value: The uint32_t value to write
        """
        # Pack the uint32_t value into a 4-byte buffer and send it
        self._write(self.BOOT_ADDRESS_REGISTER_OFFSET, struct.pack("I", value))

    def get_boot_address(self) -> int:
        """
        Get the boot address of the the C0-microSD+ Signaloid SoC.

        :return: The read uint32_t value
        """
        buffer = self._read(self.BOOT_ADDRESS_REGISTER_OFFSET, 4)
        # Unpack the buffer to get the uint32_t value
        return struct.unpack("I", buffer)[0]

    def set_command(self, value: int) -> None:
        """
        Sends a command to the C0-microSD+ device.

        :param value: The uint32_t value to write
        """
        # Pack the uint32_t value into a 4-byte buffer and send it
        self._write(self.COMMAND_REGISTER_OFFSET, struct.pack("I", value))

    def get_status(self) -> int:
        """
        Reads the C0-microSD+ status register.

        :return: The read uint32_t value
        """
        buffer = self._read(self.STATUS_REGISTER_OFFSET, 4)
        # Unpack the buffer to get the uint32_t value
        return struct.unpack("I", buffer)[0]

    def calculate_command(
            self,
            command: int,
            idle_command: int = K_CALCULATE_NO_COMMAND,
            poll_sleep_time: float = 0.5,
            skip_MMIO_buffer_read: bool = False,
            verbose: bool = True
    ) -> bytes:
        """
        Basic command calculation routine. This function sends a command to
        the C0-microSD+, polls the device until it reports that the calculation
        has finished, and finally returns the MMIO buffer data.

        :param command:         The C0-microSD+ command.
        :param idle_command:    This is the command that will be sent after the
                                calculation is complete. The default is
                                K_CALCULATE_NO_COMMAND

        :return: The MMIO buffer contents after the command has finished.
        """
        data_buffer = None

        self.set_command(command)
        if verbose:
            print("Waiting for calculation to finish.", end="")

        while True:
            # Get status of Signaloid C0-microSD+ compute module
            soc_status = self.get_status()

            if soc_status == SIGNALOID_SOC_STATUS_CALCULATING:
                # Signaloid C0-microSD+ compute module is still calculating
                if verbose:
                    print(".", end="")
                time.sleep(poll_sleep_time)
            elif soc_status == SIGNALOID_SOC_STATUS_DONE:
                # Signaloid C0-microSD+ completed calculation
                if verbose:
                    print("\n")
                if not skip_MMIO_buffer_read:
                    if verbose:
                        print("Read data content...")
                    data_buffer = self.read_MMIO_buffer()
                break
            elif soc_status == SIGNALOID_SOC_STATUS_INVALID_COMMAND:
                if verbose:
                    print("\nERROR: Device returned 'Unknown CMD'\n")
                break
            elif soc_status != SIGNALOID_SOC_STATUS_WAIT_FOR_COMMAND:
                if verbose:
                    print("\nERROR: Device returned 'Unknown CMD'\n")
                break

        while (self.get_status()
               != SIGNALOID_SOC_STATUS_WAIT_FOR_COMMAND):
            self.set_command(idle_command)

        return data_buffer
