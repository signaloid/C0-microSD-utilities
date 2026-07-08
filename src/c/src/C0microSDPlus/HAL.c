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

#if BUILD_FOR == SIGNALOID_C0_MICROSD_PLUS

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
C0HALSetConfigRegisterUnlockBitstreamSection(bool state)
{
	kC0HALConfigRegister.bits.unlockBitstreamSection = state;

	return;
}

void
C0HALSetConfigRegisterSwLedEnable(bool state)
{
	kC0HALConfigRegister.bits.swLedEnable = state;

	return;
}

void
C0HALSetConfigRegisterSwLed(bool state)
{
	kC0HALConfigRegister.bits.swLed = state;

	return;
}

void
C0HALSetConfigRegisterRedLed(bool state)
{
	kC0HALConfigRegister.bits.redLed = state;

	return;
}

void
C0HALSetConfigRegisterGreenLed(bool state)
{
	kC0HALConfigRegister.bits.greenLed = state;

	return;
}

void
C0HALSetConfigRegisterBlueLed(bool state)
{
	kC0HALConfigRegister.bits.blueLed = state;

	return;
}

void
C0HALSetConfigRegisterDebugPin0(bool state)
{
	kC0HALConfigRegister.bits.debugPin0 = state;

	return;
}

void
C0HALSetConfigRegisterDebugPin1(bool state)
{
	kC0HALConfigRegister.bits.debugPin1 = state;

	return;
}

void
C0HALSetConfigRegisterDebugPin2(bool state)
{
	kC0HALConfigRegister.bits.debugPin2 = state;

	return;
}

void
C0HALSetConfigRegisterRstn(bool state)
{
	kC0HALConfigRegister.bits.rstn = state;

	return;
}

void
C0HALStopCore(void)
{
	C0HALSetConfigRegisterRstn(false);

	return;
}

void
C0HALSetLed(bool state)
{
	C0HALSetConfigRegisterGreenLed(state);

	return;
}

#else
#error "C0microSDPlus/HAL.c must be built with BUILD_FOR == SIGNALOID_C0_MICROSD_PLUS."
#endif
