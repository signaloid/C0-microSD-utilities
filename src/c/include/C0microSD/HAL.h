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

/*
 *	Register/type definitions for the Signaloid C0-microSD.
 *
 *	Included by C0HAL.h, which provides <stdint.h>, <stdbool.h> and
 *	C0SoCStatus.h beforehand. The C0-microSD uses dedicated command,
 *	control and status register addresses and separate MISO/MOSI buffers.
 */

#pragma once

#include "C0microSD/Constants.h"

typedef union
{
	uint32_t value;
	struct
	{
		uint32_t    swLed       : 1;
		uint32_t    debugPin0   : 1;
		uint32_t    reserved    : 30;
	} bits;
} C0HALConfigRegister;

#define kC0HALCommandRegister        (*(volatile uint32_t *)            kSignaloidSoCDeviceConstantsCommandAddress)
#define kC0HALConfigRegister         (*(volatile C0HALConfigRegister *) kSignaloidSoCDeviceConstantsSoCControlAddress)
#define kC0HALStatusRegister         (*(volatile SignaloidSoCStatus *)  kSignaloidSoCDeviceConstantsStatusAddress)

typedef enum
{
	kC0HALOutputBufferOffset       = kSignaloidSoCDeviceConstantsMISOBufferAddress,
	kC0HALInputBufferOffset        = kSignaloidSoCDeviceConstantsMOSIBufferAddress,
	kC0HALOutputBufferSizeBytes    = kSignaloidSoCCommonConstantsMISOBufferSizeBytes,
	kC0HALInputBufferSizeBytes     = kSignaloidSoCCommonConstantsMOSIBufferSizeBytes,
	kC0HALOutputBufferUint8Length  = kC0HALOutputBufferSizeBytes / sizeof(uint8_t),
	kC0HALOutputBufferUint32Length = kC0HALOutputBufferSizeBytes / sizeof(uint32_t),
	kC0HALOutputBufferInt32Length  = kC0HALOutputBufferSizeBytes / sizeof(int32_t),
	kC0HALOutputBufferFloatLength  = kC0HALOutputBufferSizeBytes / sizeof(float),
	kC0HALOutputBufferDoubleLength = kC0HALOutputBufferSizeBytes / sizeof(double),
	kC0HALInputBufferUint8Length   = kC0HALInputBufferSizeBytes / sizeof(uint8_t),
	kC0HALInputBufferUint32Length  = kC0HALInputBufferSizeBytes / sizeof(uint32_t),
	kC0HALInputBufferInt32Length   = kC0HALInputBufferSizeBytes / sizeof(int32_t),
	kC0HALInputBufferFloatLength   = kC0HALInputBufferSizeBytes / sizeof(float),
	kC0HALInputBufferDoubleLength  = kC0HALInputBufferSizeBytes / sizeof(double),
} C0HALConstants;
