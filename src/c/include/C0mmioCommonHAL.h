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

/*
 *	Shared MMIO memory model for compute-module variants that expose a
 *	single memory-mapped I/O buffer split in the middle into an output
 *	(MISO, first half) and an input (MOSI, second half) window, with the
 *	command/config/status registers at fixed regmap offsets.
 *
 *	Contract for including headers:
 *		- the variant's <variant>Constants.h must already be included
 *		  (the C0HALConstants enum below is evaluated at this point), and
 *		- the C0HALConfigRegister union must be defined (used lazily by the
 *		  kC0HALConfigRegister macro; only needs to exist at macro-use site).
 *
 *	The register/buffer accessors stay as macros because they expand to
 *	volatile pointer lvalues, which are not integer constants; the integer
 *	buffer offsets/sizes/lengths are grouped in the C0HALConstants enum so
 *	they remain debugger-visible.
 */
#define kC0HALCommandRegister        (*(volatile uint32_t *) kSignaloidSoCConstantsCommandOffset)
#define kC0HALConfigRegister         (*(volatile C0HALConfigRegister *) kSignaloidSoCConstantsConfigOffset)
#define kC0HALStatusRegister         (*(volatile SignaloidSoCStatus *)  kSignaloidSoCConstantsStatusOffset)

#define kC0HALMMIOBufferUint8       ((volatile uint8_t *)  kSignaloidSoCConstantsMMIOBufferOffset)
#define kC0HALMMIOBufferUint32      ((volatile uint32_t *) kSignaloidSoCConstantsMMIOBufferOffset)
#define kC0HALMMIOBufferInt32       ((volatile int32_t *)  kSignaloidSoCConstantsMMIOBufferOffset)
#define kC0HALMMIOBufferFloat       ((volatile float *)    kSignaloidSoCConstantsMMIOBufferOffset)
#define kC0HALMMIOBufferDouble      ((volatile double *)   kSignaloidSoCConstantsMMIOBufferOffset)

typedef enum
{
	kC0HALMMIOBufferUint8Length    = kSignaloidSoCConstantsMMIOBufferSizeBytes / sizeof(uint8_t),
	kC0HALMMIOBufferUint32Length   = kSignaloidSoCConstantsMMIOBufferSizeBytes / sizeof(uint32_t),
	kC0HALMMIOBufferInt32Length    = kSignaloidSoCConstantsMMIOBufferSizeBytes / sizeof(int32_t),
	kC0HALMMIOBufferFloatLength    = kSignaloidSoCConstantsMMIOBufferSizeBytes / sizeof(float),
	kC0HALMMIOBufferDoubleLength   = kSignaloidSoCConstantsMMIOBufferSizeBytes / sizeof(double),
	kC0HALOutputBufferOffset       = kSignaloidSoCConstantsMMIOBufferOffset,
	kC0HALInputBufferOffset        = kSignaloidSoCConstantsMMIOBufferOffset +
						(kSignaloidSoCConstantsMMIOBufferSizeBytes / 2),
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
