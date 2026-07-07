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
 *	Register/type definitions for the Signaloid C0-SD.
 *
 *	Included by C0HAL.h, which provides <stdint.h>, <stdbool.h> and
 *	C0SoCStatus.h beforehand.
 */

#pragma once

#include "C0SD/Constants.h"

typedef union
{
	uint32_t value;
	struct
	{
		uint32_t    rstn                    : 1;
		uint32_t    unlockBitstreamSection  : 1;
		uint32_t    swLedEnable             : 1;
		uint32_t    swLed                   : 1;
		uint32_t    greenLed                : 1;
		uint32_t    debugPin0               : 1;
		uint32_t    reserved                : 26;
	} bits;
} C0HALConfigRegister;

#include "C0mmioCommonHAL.h"
