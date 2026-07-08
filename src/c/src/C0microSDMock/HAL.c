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

#include "C0HAL.h"

#if BUILD_FOR == SIGNALOID_C0_TESTING

uint32_t
C0HALGetCommandRegister(void)
{
	return kC0HALCommandRegister;
}

C0HALConfigRegister
C0HALGetConfigRegister(void)
{
	return (C0HALConfigRegister) kC0HALConfigRegister;
}

SignaloidSoCStatus
C0HALGetStatusRegister(void)
{
	return kC0HALStatusRegister;
}

void
C0HALSetStatusRegister(SignaloidSoCStatus status)
{
	kC0HALStatusRegister = status;

	return;
}

void
C0HALSetLed(bool state)
{
	/*
	 *	The host-side test build has no onboard LED, so do nothing.
	 *	The function is defined for API consistency across SoC variants.
	 */
	(void)state;

	return;
}

#else
#error "C0microSDMock/HAL.c must be built with BUILD_FOR == SIGNALOID_C0_TESTING."
#endif
