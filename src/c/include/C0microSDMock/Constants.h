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
 *	Test-only mock of the SoC constants header.
 *	Points logs_buffer at a host-side static array so the ring-buffer
 *	writes land somewhere we can read back from.
 */

#pragma once

#include <stdint.h>

#define kSignaloidSoCConstantsCommandOffset    command_register
#define kSignaloidSoCConstantsConfigOffset     config_register
#define kSignaloidSoCConstantsStatusOffset     status_register

extern uint32_t command_register;
extern uint32_t config_register;
extern uint32_t status_register;

#define kSignaloidSoCConstantsMMIOBufferSizeBytes 8192
#define kSignaloidSoCConstantsMMIOBufferOffset mock_mmio

extern char mock_mmio[kSignaloidSoCConstantsMMIOBufferSizeBytes];
