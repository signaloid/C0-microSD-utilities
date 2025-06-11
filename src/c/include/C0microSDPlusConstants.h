/*
 *	Copyright (c) 2025, Signaloid.
 *
 *	Permission is hereby granted, free of charge, to any person obtaining a copy
 *	of this software and associated documentation files (the "Software"), to deal
 *	in the Software without restriction, including without limitation the rights
 *	to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 *	copies of the Software, and to permit persons to whom the Software is
 *	furnished to do so, subject to the following conditions:
 *
 *	The above copyright notice and this permission notice shall be included in all
 *	copies or substantial portions of the Software.
 *
 *	THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 *	IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 *	FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 *	AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 *	LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 *	OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 *	SOFTWARE.
 */

#pragma once

/*
 *	The following constants are used by both the host application and the SoC
 *	application to control the SoC
 */
enum SignaloidSoCConstants
{
	/*
	 *	Memory-mapped I/0 (MMIO) register offsets
	 */
	kSignaloidSoCConstantsCommandOffset		= 0x01000000,
	kSignaloidSoCConstantsConfigOffset		= 0x01000004,	
	kSignaloidSoCConstantsBootAddressOffset		= 0x01000008,
	kSignaloidSoCConstantsStatusOffset		= 0x0100000C,
	/*
	 *	Memory-mapped I/0 (MMIO) MISO and MOSI buffer offsets
	 */
	kSignaloidSoCConstantsMMIOBufferOffset		= 0x01004000,

	/*
	 *	MMIO buffer size in number of bytes and words
	 */
	kSignaloidSoCConstantsMMIOBufferSizeBytes	= 8192,
	kSignaloidSoCConstantsMMIOBufferSizeWords	= 2048,
};

/*
 *	The following constants are used to flash new applications and bootloaders
 *	to the C0-microSD+
 */
enum SignaloidC0microSDPlusConstants
{
	/*
	 *	Bootloader offset in SPI flash
	 */
	kSignaloidSoCConstantsBootloaderOffset	= 0x00100000,

	/*
	 *	Application offset in SPI flash
	 */
	kSignaloidSoCConstantsApplicationOffset	= 0x00180000,

	/*
	 *	Main SoC memory offset
	 */
	kSignaloidSoCConstantsMainMemoryOffset	= 0x01080000,
};

/*
 *	Host-Device communication is achieved using the command and status registers.
 *	Following are a series of common status values. Using these is not mandatory,
 *	you can determine your own status values as you see fit.
 */
typedef enum
{
	kSignaloidSoCStatusWaitingForCommand	= 0, /* Waiting for command from host */
	kSignaloidSoCStatusCalculating		= 1, /* Executing command */
	kSignaloidSoCStatusDone			= 2, /* Execution complete */
	kSignaloidSoCStatusInvalidCommand	= 3, /* Invalid command */
} SignaloidSoCStatus;
