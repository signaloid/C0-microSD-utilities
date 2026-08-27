/*
 *	Copyright (c) 2026, Signaloid.
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

#include "../../regmaps/C0microSDPlus/regmap.h"
#include "../../regmaps/C0microSDPlus/regmap_memory_defines.h"


/*
 *	The following constants are used by both the host application and the
 *	SoC application to control the SoC.
 *
 *	Offsets are sourced from the auto-generated C0-microSD+33 register map
 *	(regmaps/C0microSDPlus) so they stay in lock-step with the hardware
 *	definition.
 */
enum SignaloidSoCConstants
{
	/*
	 *	Memory-mapped I/0 (MMIO) register offsets
	 */
	kSignaloidSoCConstantsCommandOffset         = CSR_COMMAND,
	kSignaloidSoCConstantsConfigOffset          = CSR_CONFIG,
	kSignaloidSoCConstantsStatusOffset          = CSR_STATUS,

	/*
	 *	Memory-mapped I/0 (MMIO) MISO and MOSI buffer offsets
	 */
	kSignaloidSoCConstantsMMIOBufferOffset      = TOP_IO_BUFF,

	/*
	 *	MMIO buffer size in number of bytes and words
	 */
	kSignaloidSoCConstantsMMIOBufferSizeBytes   = (TopIoBuffTopEntry - TopIoBuffBottomEntry + 4),
	kSignaloidSoCConstantsMMIOBufferSizeWords   = ((TopIoBuffTopEntry - TopIoBuffBottomEntry + 4) / 4),
};

/*
 *	The following constants are used to flash new applications to the C0-microSD+
 */
enum SignaloidC0microSDPlusConstants
{
	/*
	 *	Application offset in SPI flash
	 */
	kSignaloidSoCConstantsApplicationOffset = SPI_FLASH_USER_DATA,

	/*
	 *	Main SoC memory offset
	 */
	kSignaloidSoCConstantsMainMemoryOffset  = TOP_LRAM,
};
