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
 *	Register/type definitions for the host-side unit-test build.
 *
 *	Follows the C0-microSD+/C0-SD memory model: a single MMIO buffer split
 *	in the middle into the output (MISO, first half) and input (MOSI, second
 *	half) windows. The buffer base and registers resolve to static arrays /
 *	variables supplied by the test harness (see C0microSDMock/Constants.h).
 *
 *	Included by C0HAL.h, which provides <stdint.h>, <stdbool.h> and
 *	C0SoCStatus.h beforehand.
 */

#pragma once

#include "C0microSDMock/Constants.h"

typedef union
{
	uint32_t value;
	struct
	{
		uint32_t    reserved    : 32;
	} bits;
} C0HALConfigRegister;

#define kC0HALCommandRegister        kSignaloidSoCConstantsCommandOffset
#define kC0HALConfigRegister         kSignaloidSoCConstantsConfigOffset
#define kC0HALStatusRegister         kSignaloidSoCConstantsStatusOffset

#define kC0HALMMIOBufferUint8        kSignaloidSoCConstantsMMIOBufferOffset
#define kC0HALMMIOBufferUint32       kSignaloidSoCConstantsMMIOBufferOffset
#define kC0HALMMIOBufferInt32        kSignaloidSoCConstantsMMIOBufferOffset
#define kC0HALMMIOBufferFloat        kSignaloidSoCConstantsMMIOBufferOffset
#define kC0HALMMIOBufferDouble       kSignaloidSoCConstantsMMIOBufferOffset

#define kC0HALOutputBufferOffset     kSignaloidSoCConstantsMMIOBufferOffset
#define kC0HALInputBufferOffset      (kSignaloidSoCConstantsMMIOBufferOffset + \
					(kSignaloidSoCConstantsMMIOBufferSizeBytes / 2))

typedef enum
{
	kC0HALMMIOBufferUint8Length    = kSignaloidSoCConstantsMMIOBufferSizeBytes / sizeof(uint8_t),
	kC0HALMMIOBufferUint32Length   = kSignaloidSoCConstantsMMIOBufferSizeBytes / sizeof(uint32_t),
	kC0HALMMIOBufferInt32Length    = kSignaloidSoCConstantsMMIOBufferSizeBytes / sizeof(int32_t),
	kC0HALMMIOBufferFloatLength    = kSignaloidSoCConstantsMMIOBufferSizeBytes / sizeof(float),
	kC0HALMMIOBufferDoubleLength   = kSignaloidSoCConstantsMMIOBufferSizeBytes / sizeof(double),
	kC0HALOutputBufferSizeBytes    = kSignaloidSoCConstantsMMIOBufferSizeBytes / 2,
	kC0HALInputBufferSizeBytes     = kSignaloidSoCConstantsMMIOBufferSizeBytes / 2,
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
