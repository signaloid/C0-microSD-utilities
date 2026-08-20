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


import struct
import time
from typing import Any, Callable, Dict, Iterable, Optional, Tuple

from ..common.raw_block_device import UnifiedBlockDevice
from ..common.bitstream_prefix import (
    COMMENT_WINDOW_BYTES,
    NEXUS,
    crc32,
    locate_prefix,
    read_prefix_json,
)
from ..regmap_loader import load_regmap_namespace


SIGNALOID_SOC_STATUS_WAIT_FOR_COMMAND = 0
SIGNALOID_SOC_STATUS_CALCULATING = 1
SIGNALOID_SOC_STATUS_DONE = 2
SIGNALOID_SOC_STATUS_INVALID_COMMAND = 3

K_CALCULATE_NO_COMMAND = 0


class UnsupportedConfigureAction(Exception):
    """Raised when a `configure` action is not in the variant's supported set."""

    def __init__(
        self,
        action: str,
        variant_name: str,
        available: Iterable[str],
    ) -> None:
        self.action = action
        self.variant_name = variant_name
        self.available = available
        super().__init__(
            f"action '{action}' is not supported on {variant_name}.\n"
            f"Available actions: {', '.join(sorted(available))}"
        )


class C0SDBaseInterface:
    """Communication interface for the C0-SD device family.

    The base class owns all behaviour shared across variants — low-level
    register I/O, MMIO buffer access, command dispatch, and the generic
    `apply_configure_action` driver. Each variant subclass supplies its
    own offsets (via class attributes) and its own SUPPORTED_ACTIONS
    table; the dispatch reads from `self.SUPPORTED_ACTIONS`, so swapping
    the table is enough to retarget a variant.
    """

    DISPLAY_NAME: str = "C0-SD device"

    # Variant-specific layout. Subclasses MUST override these.
    BITSTREAM_OFFSET: int = 0
    APPLICATION_BINARY_OFFSET: int = 0

    COMMAND_REGISTER_OFFSET: int = 0
    CONFIG_REGISTER_OFFSET: int = 0
    STATUS_REGISTER_OFFSET: int = 0

    MMIO_BUFFER_SIZE_BYTES: int = 8192
    MMIO_BUFFER_OFFSET: int = 0

    DEBUG_LOG_BUFFER_SIZE_BYTES = 512

    # Map action name -> (value, mask, register, confirm). apply_configure_action does:
    #   if confirm: prompt the user via confirm_callback; abort if declined.
    #   new = (current & ~mask) | (value & mask)
    # on the raw config register. Bitstream lock/unlock are ordinary
    # entries — unlock-bitstream additionally has confirm=True.
    # Subclasses override this with the per-variant table.
    SUPPORTED_ACTIONS: Dict[str, Tuple[int, int, int, bool]] = {}

    def __init__(
        self, target_device: str,
        force_transactions: bool = False
    ) -> None:
        self.target_device = target_device
        self.force_transactions = force_transactions

        self.INPUT_BUFFER_SIZE_BYTES: int = self.MMIO_BUFFER_SIZE_BYTES // 2
        self.INPUT_BUFFER_OFFSET: int = self.MMIO_BUFFER_OFFSET + self.MMIO_BUFFER_SIZE_BYTES // 2

        self.OUTPUT_BUFFER_SIZE_BYTES: int = self.MMIO_BUFFER_SIZE_BYTES // 2
        self.OUTPUT_BUFFER_OFFSET: int = self.MMIO_BUFFER_OFFSET

        self.device = UnifiedBlockDevice(path=target_device)

    def _read(self, offset: int, size: int) -> bytes:
        return self.device.read(offset=offset, length=size)

    def _write(self, offset: int, data: bytes) -> int:
        return self.device.write(offset=offset, data=data)

    def __str__(self) -> str:
        return f"Signaloid {self.DISPLAY_NAME}"

    def write_MMIO_buffer(self, buffer: bytes) -> None:
        if len(buffer) > self.MMIO_BUFFER_SIZE_BYTES:
            raise ValueError(
                "Buffer size exceeds maximum allowed "
                f"size of {self.MMIO_BUFFER_SIZE_BYTES} bytes."
            )
        self._write(self.MMIO_BUFFER_OFFSET, buffer)

    def read_MMIO_buffer(self, size: int | None = None) -> bytes:
        if size is None:
            size = self.MMIO_BUFFER_SIZE_BYTES
        if size > self.MMIO_BUFFER_SIZE_BYTES:
            raise ValueError(
                "Read MMIO size exceeds"
                f" {self.MMIO_BUFFER_SIZE_BYTES} bytes."
            )
        return self._read(self.MMIO_BUFFER_OFFSET, size)

    def write_input_buffer(self, buffer: bytes) -> None:
        if len(buffer) > self.INPUT_BUFFER_SIZE_BYTES:
            raise ValueError(
                "Buffer size exceeds maximum allowed "
                f"size of {self.INPUT_BUFFER_SIZE_BYTES} bytes."
            )
        self._write(self.INPUT_BUFFER_OFFSET, buffer)

    def read_output_buffer(self, size: int | None = None) -> bytes:
        if size is None:
            size = self.OUTPUT_BUFFER_SIZE_BYTES
        if size > self.OUTPUT_BUFFER_SIZE_BYTES:
            raise ValueError(
                "Read output buffer size exceeds"
                f" {self.OUTPUT_BUFFER_SIZE_BYTES} bytes."
            )
        return self._read(self.OUTPUT_BUFFER_OFFSET, size)

    def read_debug_log_buffer(
        self,
        size: int = DEBUG_LOG_BUFFER_SIZE_BYTES
    ) -> bytes:
        if size > self.MMIO_BUFFER_SIZE_BYTES:
            raise ValueError(
                "Read UART size exceeds"
                f" {self.MMIO_BUFFER_SIZE_BYTES} bytes."
            )

        DEBUG_LOG_BUFFER_OFFSET = (
            self.OUTPUT_BUFFER_OFFSET + self.OUTPUT_BUFFER_SIZE_BYTES - size
        )
        return self._read(DEBUG_LOG_BUFFER_OFFSET, size)

    def read_bitstream_prefix(
        self, offset: int | None = None, size: int = COMMENT_WINDOW_BYTES
    ) -> bytes:
        """Return the raw ASCII metadata-prefix payload of the bitstream.

        Reads ``size`` bytes at ``offset`` (default ``BITSTREAM_OFFSET``)
        and returns the bytes between the Nexus (``LSCC``) framing markers.

        Args:
            offset: Flash byte offset of the bitstream; defaults to
                ``self.BITSTREAM_OFFSET``.
            size: Number of bytes to read for the prefix scan (the comment
                fits comfortably in the default 4096).

        Returns:
            The metadata payload bytes (framing markers excluded).

        Raises:
            ValueError: if the LSCC framing is not present.
        """
        if offset is None:
            offset = self.BITSTREAM_OFFSET
        chunk = self._read(offset, size)
        prefix_start, prefix_end, _ = locate_prefix(chunk, NEXUS)
        return chunk[prefix_start:prefix_end]

    def read_bitstream_metadata(
        self, offset: int | None = None
    ) -> Dict[str, Any]:
        """Decode the Signaloid JSON metadata embedded in the bitstream.

        Args:
            offset: Flash byte offset of the bitstream; defaults to
                ``self.BITSTREAM_OFFSET``.

        Returns:
            The decoded metadata object.

        Raises:
            ValueError: if no valid JSON metadata object is present.
        """
        if offset is None:
            offset = self.BITSTREAM_OFFSET
        chunk = self._read(offset, COMMENT_WINDOW_BYTES)
        return read_prefix_json(chunk, NEXUS)

    def verify_bitstream_crc(
        self,
        offset: int | None = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool | None:
        """Recompute the CRC-32 of the CRC-covered region and compare.

        Reads ``metadata['bitstream_size']`` bytes from just after the
        comment section and compares their CRC-32 to
        ``metadata['bitstream_crc']`` (accepting the ``crc``/``size``
        aliases).

        Args:
            offset: Flash byte offset of the bitstream; defaults to
                ``self.BITSTREAM_OFFSET``.
            metadata: Previously decoded metadata; read from the device if
                omitted.

        Returns:
            ``True``/``False`` for the comparison, or ``None`` if the
            metadata carries no CRC/size fields.
        """
        if offset is None:
            offset = self.BITSTREAM_OFFSET
        if metadata is None:
            metadata = self.read_bitstream_metadata(offset)

        expected_crc = metadata.get("bitstream_crc", metadata.get("crc"))
        expected_size = metadata.get("bitstream_size", metadata.get("size"))
        if expected_crc is None or expected_size is None:
            return None

        chunk = self._read(offset, COMMENT_WINDOW_BYTES)
        _, _, crc_start = locate_prefix(chunk, NEXUS)
        payload = self._read(offset + crc_start, int(expected_size))
        return crc32(payload) == int(expected_crc)

    def set_command(self, value: int) -> None:
        self._write(self.COMMAND_REGISTER_OFFSET, struct.pack("<I", value))

    def get_command(self) -> int:
        buffer = self._read(self.COMMAND_REGISTER_OFFSET, 4)
        return struct.unpack("<I", buffer)[0]

    def get_status(self) -> int:
        buffer = self._read(self.STATUS_REGISTER_OFFSET, 4)
        return struct.unpack("<I", buffer)[0]

    def calculate_command(
            self,
            command: int,
            idle_command: int = K_CALCULATE_NO_COMMAND,
            poll_sleep_time: float = 0.5,
            skip_MMIO_buffer_read: bool = False,
            verbose: bool = True,
            timeout_waiting_to_start: float = 0.5,
    ) -> bytes:
        data_buffer = None

        self.set_command(command)
        if verbose:
            print("Waiting for calculation to finish.", end="")

        start_time = time.time()
        while True:
            soc_status = self.get_status()

            if soc_status == SIGNALOID_SOC_STATUS_CALCULATING:
                if verbose:
                    print(".", end="")
                time.sleep(poll_sleep_time)
            elif soc_status == SIGNALOID_SOC_STATUS_DONE:
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
            elif soc_status == SIGNALOID_SOC_STATUS_WAIT_FOR_COMMAND:
                if time.time() - start_time < timeout_waiting_to_start:
                    continue

                if verbose:
                    print(f"\nERROR: Timeout waiting for command to start.\n")
                break
            elif soc_status != SIGNALOID_SOC_STATUS_WAIT_FOR_COMMAND:
                if verbose:
                    print(f"\nERROR: Unknown status: {soc_status}\n")
                break

        while (self.get_status() != SIGNALOID_SOC_STATUS_WAIT_FOR_COMMAND):
            self.set_command(idle_command)

        return data_buffer

    def get_config_register(self) -> int:
        buffer = self._read(self.CONFIG_REGISTER_OFFSET, 4)
        return struct.unpack("<I", buffer)[0]

    def set_config_register(self, value: int) -> None:
        self._write(self.CONFIG_REGISTER_OFFSET, struct.pack("<I", value))

    def apply_configure_action(
        self,
        action: str,
        confirm_callback: Callable[[], bool] | None = None,
        verbose: bool = False,
    ) -> None:
        if action not in self.SUPPORTED_ACTIONS:
            raise UnsupportedConfigureAction(
                action, self.DISPLAY_NAME, self.SUPPORTED_ACTIONS
            )

        value, mask, register_offset, confirm = self.SUPPORTED_ACTIONS[action]
        if confirm and (confirm_callback is None or not confirm_callback()):
            if verbose:
                print(f"Applying configure action {action} aborted.")
            return
        current = struct.unpack("<I", self._read(register_offset, 4))[0]
        updated = (current & ~mask) | (value & mask)
        self._write(register_offset, struct.pack("<I", updated))
        if verbose:
            print(f"Applied configure action: {action}")

    def reset_core(self, timeout: float = 1.0, verbose: bool = False) -> None:
        self.apply_configure_action("core-stop", verbose=verbose)
        time.sleep(timeout)
        self.apply_configure_action("core-start", verbose=verbose)
        time.sleep(timeout)

    def verbose_status(self) -> None:
        """Print the contents of the COMMAND, CONFIG, and STATUS registers."""
        print(f"{'COMMAND':>9}: {self.get_command():#010x}")
        print(f"{'CONFIG':>9}: {self.get_config_register():#010x}")
        print(f"{'STATUS':>9}: {self.get_status():#010x}")


class SDConfigRegisterMixin:
    """Accessors for the SD config register, shared by variants that have one.

    Subclasses must provide ``SD_CONFIG_REGISTER_OFFSET`` and inherit
    from ``C0SDBaseInterface`` (for ``_read``/``_write`` and the base
    ``verbose_status``). The mixin should come first in the MRO so its
    ``verbose_status`` extends the base report.
    """

    SD_CONFIG_REGISTER_OFFSET: int = 0

    @staticmethod
    def sd_config_actions(
        offset: int,
    ) -> Dict[str, Tuple[int, int, int, bool]]:
        """Return the SD-config-register entries for ``SUPPORTED_ACTIONS``.

        Subclasses spread this into their own ``SUPPORTED_ACTIONS`` so
        the write-crc-* actions stay in lock-step across variants while
        each variant supplies its own register offset.
        """
        return {
            "write-crc-force-ok-enable":     (0x00000001, 0x00000001, offset, False),
            "write-crc-force-ok-disable":    (0x00000000, 0x00000001, offset, False),
            "write-crc-force-write-enable":  (0x00000100, 0x00000100, offset, False),
            "write-crc-force-write-disable": (0x00000000, 0x00000100, offset, False),
            "write-crc-irq-connect":         (0x00010000, 0x00010000, offset, False),
            "write-crc-irq-disconnect":      (0x00000000, 0x00010000, offset, False),
            "write-crc-irq-clear":           (0x00000000, 0x01000000, offset, False),
        }

    def get_sd_config_register(self) -> int:
        buffer: bytes = self._read(self.SD_CONFIG_REGISTER_OFFSET, 4)
        return struct.unpack("<I", buffer)[0]

    def set_sd_config_register(self, value: int) -> None:
        self._write(self.SD_CONFIG_REGISTER_OFFSET, struct.pack("<I", value))

    def get_sd_config_unpacked(self) -> Tuple[bool, ...]:
        """Read the SD config register and unpack its boolean fields.

        Returns:
            Tuple in declaration order: (force_write_crc_ok,
            ignore_write_crc_error, connect_crc_error_to_interrupt,
            crc_error).
        """
        value = self.get_sd_config_register()
        return (
            bool(value & (1 << 0)),
            bool(value & (1 << 8)),
            bool(value & (1 << 16)),
            bool(value & (1 << 24)),
        )

    def set_sd_config_unpacked(
        self,
        force_write_crc_ok: bool = True,
        ignore_write_crc_error: bool = False,
        connect_crc_error_to_interrupt: bool = False,
        crc_error: bool = False,
    ) -> None:
        """Write the SD config register from its boolean fields.

        Each call writes a complete register value. Defaults match the
        RDL reset values (``force_write_crc_ok=True``, rest ``False``),
        so omitted fields take their reset value.

        Args:
            force_write_crc_ok: Force CRC OK response for SD Block Write.
            ignore_write_crc_error: Commit Block Write data even on CRC mismatch.
            connect_crc_error_to_interrupt: Route crc_error to the core IRQ.
            crc_error: CRC error status; write 0 to clear.
        """
        value = (
            (force_write_crc_ok << 0)
            | (ignore_write_crc_error << 8)
            | (connect_crc_error_to_interrupt << 16)
            | (crc_error << 24)
        )
        self.set_sd_config_register(value)

    def modify_sd_config(
        self,
        force_write_crc_ok: Optional[bool] = None,
        ignore_write_crc_error: Optional[bool] = None,
        connect_crc_error_to_interrupt: Optional[bool] = None,
        crc_error: Optional[bool] = None,
    ) -> None:
        """Read-modify-write the SD config register, updating only the fields passed.

        Any argument left as None keeps its current on-device value;
        arguments passed as True/False force the corresponding bit to
        1/0. The whole transaction is one read followed by one write.

        Args:
            force_write_crc_ok: Force CRC OK response for SD Block Write.
            ignore_write_crc_error: Commit Block Write data even on CRC mismatch.
            connect_crc_error_to_interrupt: Route crc_error to the core IRQ.
            crc_error: CRC error status; write 0 to clear.
        """
        fields = (
            (force_write_crc_ok, 0),
            (ignore_write_crc_error, 8),
            (connect_crc_error_to_interrupt, 16),
            (crc_error, 24),
        )
        value = self.get_sd_config_register()
        for field, bit in fields:
            if field is None:
                continue
            mask = 1 << bit
            value = (value & ~mask) | ((1 if field else 0) << bit)
        self.set_sd_config_register(value)

    def verbose_status(self) -> None:
        """Extend the base report with the SD_CONFIG register."""
        super().verbose_status()
        print(f"{'SD_CONFIG':>9}: {self.get_sd_config_register():#010x}")


# ---------------------------------------------------------------------------
# Variant subclasses
#
# Each variant supplies its DISPLAY_NAME, the per-device register and
# flash offsets, and its SUPPORTED_ACTIONS table. Behaviour (register I/O
# and configure-action dispatch) is inherited from C0SDBaseInterface.
# ---------------------------------------------------------------------------


class C0microSDPlusInterface(SDConfigRegisterMixin, C0SDBaseInterface):
    """Interface for the C0-microSD+ variant. CLI default."""

    DISPLAY_NAME = "C0-microSD+"

    def __init__(
            self,
            target_device: str,
            force_transactions: bool = False,
            regmap_path: Optional[str] = None,
            ) -> None:
        top = load_regmap_namespace(
            ".regmaps.c0microsdplus", __package__, "Top", regmap_path
        )
        csr = top.Csr

        self.BITSTREAM_OFFSET = top.SpiFlash.Bitstream.BOTTOM_ENTRY
        self.APPLICATION_BINARY_OFFSET = top.SpiFlash.UserData.BOTTOM_ENTRY

        self.COMMAND_REGISTER_OFFSET = csr.Command.ADDR
        self.CONFIG_REGISTER_OFFSET = csr.Config.ADDR
        self.STATUS_REGISTER_OFFSET = csr.Status.ADDR
        self.SD_CONFIG_REGISTER_OFFSET = csr.SdConfig.ADDR

        self.TRAP_MCAUSE_REGISTER_OFFSET = csr.TrapMcause.ADDR
        self.TRAP_MEPC_REGISTER_OFFSET = csr.TrapMepc.ADDR
        self.TRAP_MTVAL_REGISTER_OFFSET = csr.TrapMtval.ADDR

        self.MMIO_BUFFER_OFFSET = top.IoBuff.BOTTOM_ENTRY
        self.MMIO_BUFFER_SIZE_BYTES = top.IoBuff.SIZE_BYTES

        config = self.CONFIG_REGISTER_OFFSET
        self.SUPPORTED_ACTIONS: Dict[str, Tuple[int, int, int, bool]] = {
            "core-start":       (0x00000001, 0x00000001, config, False),
            "core-stop":        (0x00000000, 0x00000001, config, False),
            "unlock-bitstream": (0x00000002, 0x00000002, config, True),
            "lock-bitstream":   (0x00000000, 0x00000002, config, False),
            "sw-led-on":        (0x0000000C, 0x0000000C, config, False),
            "sw-led-off":       (0x00000000, 0x0000000C, config, False),
            "red-led-on":       (0x00000010, 0x00000010, config, False),
            "red-led-off":      (0x00000000, 0x00000010, config, False),
            "green-led-on":     (0x00000020, 0x00000020, config, False),
            "green-led-off":    (0x00000000, 0x00000020, config, False),
            "blue-led-on":      (0x00000040, 0x00000040, config, False),
            "blue-led-off":     (0x00000000, 0x00000040, config, False),
            "debug-pin-0-on":   (0x00000080, 0x00000080, config, False),
            "debug-pin-0-off":  (0x00000000, 0x00000080, config, False),
            "debug-pin-1-on":   (0x00000100, 0x00000100, config, False),
            "debug-pin-1-off":  (0x00000000, 0x00000100, config, False),
            "debug-pin-2-on":   (0x00000200, 0x00000200, config, False),
            "debug-pin-2-off":  (0x00000000, 0x00000200, config, False),
            **self.sd_config_actions(self.SD_CONFIG_REGISTER_OFFSET),
        }

        super().__init__(target_device, force_transactions)

    def get_config_register_unpacked(self) -> Tuple[bool, ...]:
        """Read the config register and unpack its boolean fields.

        Returns:
            Tuple in declaration order: (rstn, unlock_bitstream_section,
            sw_led_enable, sw_led, red_led, green_led, blue_led,
            debug_pin_0, debug_pin_1, debug_pin_2).
        """
        value = self.get_config_register()
        return (
            bool(value & 0x001),
            bool(value & 0x002),
            bool(value & 0x004),
            bool(value & 0x008),
            bool(value & 0x010),
            bool(value & 0x020),
            bool(value & 0x040),
            bool(value & 0x080),
            bool(value & 0x100),
            bool(value & 0x200),
        )

    def set_config_register_unpacked(
        self,
        rstn: bool = False,
        unlock_bitstream_section: bool = False,
        sw_led_enable: bool = False,
        sw_led: bool = False,
        red_led: bool = False,
        green_led: bool = False,
        blue_led: bool = False,
        debug_pin_0: bool = False,
        debug_pin_1: bool = False,
        debug_pin_2: bool = False,
    ) -> None:
        """Write the config register from its boolean fields.

        Each call writes a complete register value. Unspecified fields
        take their RDL reset default (0), so pass only the fields you
        want set to 1.

        Args:
            rstn: Reset CPU (active low).
            unlock_bitstream_section: Unlock bitstream section for flashing.
            sw_led_enable: Enable software management of the onboard red LED.
            sw_led: Onboard red LED (requires sw_led_enable=True).
            red_led: Red LED control.
            green_led: Green LED control.
            blue_led: Blue LED control.
            debug_pin_0: Debug pin 0.
            debug_pin_1: Debug pin 1.
            debug_pin_2: Debug pin 2.
        """
        value = (
            (rstn << 0)
            | (unlock_bitstream_section << 1)
            | (sw_led_enable << 2)
            | (sw_led << 3)
            | (red_led << 4)
            | (green_led << 5)
            | (blue_led << 6)
            | (debug_pin_0 << 7)
            | (debug_pin_1 << 8)
            | (debug_pin_2 << 9)
        )
        self.set_config_register(value)

    def modify_config_register(
        self,
        rstn: Optional[bool] = None,
        unlock_bitstream_section: Optional[bool] = None,
        sw_led_enable: Optional[bool] = None,
        sw_led: Optional[bool] = None,
        red_led: Optional[bool] = None,
        green_led: Optional[bool] = None,
        blue_led: Optional[bool] = None,
        debug_pin_0: Optional[bool] = None,
        debug_pin_1: Optional[bool] = None,
        debug_pin_2: Optional[bool] = None,
    ) -> None:
        """Read-modify-write the config register, updating only the fields passed.

        Any argument left as None keeps its current on-device value;
        arguments passed as True/False force the corresponding bit to
        1/0. The whole transaction is one read followed by one write.

        Args:
            rstn: Reset CPU (active low).
            unlock_bitstream_section: Unlock bitstream section for flashing.
            sw_led_enable: Enable software management of the onboard red LED.
            sw_led: Onboard red LED (requires sw_led_enable=True).
            red_led: Red LED control.
            green_led: Green LED control.
            blue_led: Blue LED control.
            debug_pin_0: Debug pin 0.
            debug_pin_1: Debug pin 1.
            debug_pin_2: Debug pin 2.
        """
        fields = (
            (rstn, 0),
            (unlock_bitstream_section, 1),
            (sw_led_enable, 2),
            (sw_led, 3),
            (red_led, 4),
            (green_led, 5),
            (blue_led, 6),
            (debug_pin_0, 7),
            (debug_pin_1, 8),
            (debug_pin_2, 9),
        )
        value = self.get_config_register()
        for field, bit in fields:
            if field is None:
                continue
            mask = 1 << bit
            value = (value & ~mask) | ((1 if field else 0) << bit)
        self.set_config_register(value)

    def get_trap_status(self) -> Tuple[int, int, int]:
        """Read the trap registers (mcause, mepc, mtval) in one transaction.

        The three registers are contiguous in the memory map, so they are read
        together as a single packed 12-byte block. Returns (mcause, mepc,
        mtval); mcause is 0xFFFFFFFF when no trap has been recorded.
        """
        buffer = self._read(self.TRAP_MCAUSE_REGISTER_OFFSET, 12)
        return struct.unpack("<III", buffer)


class C0SDInterface(SDConfigRegisterMixin, C0SDBaseInterface):
    """Interface for the C0-SD variant.

    Offsets are derived from the auto-generated ``regmaps.c0sd`` register
    map, so they stay in lock-step with the hardware definition.
    """

    DISPLAY_NAME = "C0-SD"

    def __init__(
            self,
            target_device: str,
            force_transactions: bool = False,
            regmap_path: Optional[str] = None,
            ) -> None:
        top = load_regmap_namespace(
            ".regmaps.c0sd", __package__, "Top", regmap_path
        )
        csr = top.Csr

        self.BITSTREAM_OFFSET = top.SpiFlash.Bitstream.BOTTOM_ENTRY
        self.APPLICATION_BINARY_OFFSET = top.SpiFlash.UserData.BOTTOM_ENTRY

        self.COMMAND_REGISTER_OFFSET = csr.Command.ADDR
        self.CONFIG_REGISTER_OFFSET = csr.Config.ADDR
        self.STATUS_REGISTER_OFFSET = csr.Status.ADDR
        self.SD_CONFIG_REGISTER_OFFSET = csr.SdConfig.ADDR

        self.TRAP_MCAUSE_REGISTER_OFFSET = csr.TrapMcause.ADDR
        self.TRAP_MEPC_REGISTER_OFFSET = csr.TrapMepc.ADDR
        self.TRAP_MTVAL_REGISTER_OFFSET = csr.TrapMtval.ADDR

        self.MMIO_BUFFER_OFFSET = top.IoBuff.BOTTOM_ENTRY
        self.MMIO_BUFFER_SIZE_BYTES = top.IoBuff.SIZE_BYTES

        config = self.CONFIG_REGISTER_OFFSET
        self.SUPPORTED_ACTIONS: Dict[str, Tuple[int, int, int, bool]] = {
            "core-start":       (0x00000001, 0x00000001, config, False),
            "core-stop":        (0x00000000, 0x00000001, config, False),
            "unlock-bitstream": (0x00000002, 0x00000002, config, True),
            "lock-bitstream":   (0x00000000, 0x00000002, config, False),
            "sw-led-on":        (0x0000000C, 0x0000000C, config, False),
            "sw-led-off":       (0x00000000, 0x0000000C, config, False),
            "green-led-on":     (0x00000010, 0x00000010, config, False),
            "green-led-off":    (0x00000000, 0x00000010, config, False),
            "debug-pin-on":     (0x00000020, 0x00000020, config, False),
            "debug-pin-off":    (0x00000000, 0x00000020, config, False),
            **self.sd_config_actions(self.SD_CONFIG_REGISTER_OFFSET),
        }

        super().__init__(target_device, force_transactions)

    def get_config_register_unpacked(self) -> Tuple[bool, ...]:
        """Read the config register and unpack its boolean fields.

        Returns:
            Tuple in declaration order: (rstn, unlock_bitstream_section,
            sw_led_enable, sw_led, green_led, debug_pin_0).
        """
        value = self.get_config_register()
        return (
            bool(value & 0x01),
            bool(value & 0x02),
            bool(value & 0x04),
            bool(value & 0x08),
            bool(value & 0x10),
            bool(value & 0x20),
        )

    def set_config_register_unpacked(
        self,
        rstn: bool = False,
        unlock_bitstream_section: bool = False,
        sw_led_enable: bool = False,
        sw_led: bool = False,
        green_led: bool = False,
        debug_pin_0: bool = False,
    ) -> None:
        """Write the config register from its boolean fields.

        Each call writes a complete register value. Unspecified fields
        take their RDL reset default (0), so pass only the fields you
        want set to 1.

        Args:
            rstn: Reset CPU (active low).
            unlock_bitstream_section: Unlock bitstream section for flashing.
            sw_led_enable: Enable software management of the onboard red LED.
            sw_led: Onboard red LED (requires sw_led_enable=True).
            green_led: Green LED control.
            debug_pin_0: Debug pin 0.
        """
        value = (
            (rstn << 0)
            | (unlock_bitstream_section << 1)
            | (sw_led_enable << 2)
            | (sw_led << 3)
            | (green_led << 4)
            | (debug_pin_0 << 5)
        )
        self.set_config_register(value)

    def modify_config_register(
        self,
        rstn: Optional[bool] = None,
        unlock_bitstream_section: Optional[bool] = None,
        sw_led_enable: Optional[bool] = None,
        sw_led: Optional[bool] = None,
        green_led: Optional[bool] = None,
        debug_pin_0: Optional[bool] = None,
    ) -> None:
        """Read-modify-write the config register, updating only the fields passed.

        Any argument left as None keeps its current on-device value;
        arguments passed as True/False force the corresponding bit to
        1/0. The whole transaction is one read followed by one write.

        Args:
            rstn: Reset CPU (active low).
            unlock_bitstream_section: Unlock bitstream section for flashing.
            sw_led_enable: Enable software management of the onboard red LED.
            sw_led: Onboard red LED (requires sw_led_enable=True).
            green_led: Green LED control.
            debug_pin_0: Debug pin 0.
        """
        fields = (
            (rstn, 0),
            (unlock_bitstream_section, 1),
            (sw_led_enable, 2),
            (sw_led, 3),
            (green_led, 4),
            (debug_pin_0, 5),
        )
        value = self.get_config_register()
        for field, bit in fields:
            if field is None:
                continue
            mask = 1 << bit
            value = (value & ~mask) | ((1 if field else 0) << bit)
        self.set_config_register(value)

    def get_trap_status(self) -> Tuple[int, int, int]:
        """Read the trap registers (mcause, mepc, mtval) in one transaction.

        The three registers are contiguous in the memory map, so they are
        read together as a single packed 12-byte block rather than with
        three separate transactions.

        Returns:
            Tuple in order (mcause, mepc, mtval). ``mcause`` is
            ``0xFFFFFFFF`` when no trap has been recorded.
        """
        buffer = self._read(self.TRAP_MCAUSE_REGISTER_OFFSET, 12)
        return struct.unpack("<III", buffer)

    def verbose_status(self) -> None:
        """Extend the report with the trap registers (mcause/mepc/mtval).

        After the base + SD report (COMMAND, CONFIG, STATUS, SD_CONFIG),
        the trap registers are read in one transaction. ``mcause`` reads
        ``0xFFFFFFFF`` when no trap has occurred; any other value
        indicates a trap, in which case an extra section is printed with
        ``mcause`` as an unsigned integer and ``mepc``/``mtval`` as hex.
        """
        super().verbose_status()

        mcause, mepc, mtval = self.get_trap_status()
        if mcause != 0xFFFFFFFF:
            print("\nA trap has occurred:")
            print(f"{'MCAUSE':>9}: {mcause}")
            print(f"{'MEPC':>9}: {mepc:#010x}")
            print(f"{'MTVAL':>9}: {mtval:#010x}")
