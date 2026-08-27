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
 *	Signaloid SoC debug logger.
 *
 *	Implements the write_buffer hook and API for enabling prints on the
 *	C0 compute modules.
 *
 *	Output is copied into a 512-byte device's MMIO window, where the host
 *	can read it back. When full, buffer wraps at the next newline boundary.
 *
 *	Note: When using plain debug_printf we let it manage its temp buffer,
 *	up to 1KB. Mind that printf itself takes ~10KB.
 *
 *	For minimal memory usage avoid debug_printf and use the provided API
 *	  print_lstr("string")    - zero-overhead literal-string print
 *	  print_int(int)          - raw signed decimal integer
 *	  print_uint(unsigned)    - raw unsigned decimal integer
 *	  print_hex(unsigned)     - raw lowercase hexadecimal
 *	  print_hexdump(p, len)   - hex+ASCII dump of a memory region
 *	  tiny_printf(fmt, ...)   - supports %d, %u, %x, %X, %b, %p, %c,
 *	                            %s, %% with optional zero-pad/width
 *	                            (e.g. %08x)
 *
 *	Note: If ENABLE_DEBUG_LOGGING != 1, these API functions become a no-op.
 */

#pragma once


/*
 *	Set ENABLE_DEBUG_LOGGING to 1 to enable the debug logger, or 0 to
 *	disable it. When disabled, the API functions become no-op stubs, so no
 *	logs are emitted or copied to the MMIO window.
 *
 *	Enabling the debug logger will increase code size and may have a minor
 *	performance impact, so it should be disabled in production builds.
 *
 *	To set the ENABLE_DEBUG_LOGGING flag, define it before including this
 *	header, or pass it as a compiler flag (e.g. -DENABLE_DEBUG_LOGGING=0).
 */
#ifndef ENABLE_DEBUG_LOGGING
 #define ENABLE_DEBUG_LOGGING 1
#endif


#if ENABLE_DEBUG_LOGGING == 1
/*
 * 	Set ENABLE_FULL_PRINTF to 1 to enable the debug_printf function, which
 *	supports full printf formatting capabilities but with the overhead of a
 *	temp buffer and vsnprintf (~30kB).
 *
 *	When ENABLE_FULL_PRINTF is 0, debug_printf is a simple alias for
 *	tiny_printf, which has minimal overhead but only supports %d, %s, and
 *	%% format specifiers.
 *
 *	The print_lstr and print_int functions remain available regardless of
 *	the ENABLE_FULL_PRINTF setting.
 *
 * 	To set the ENABLE_FULL_PRINTF flag, define it before including this
 *	header,	or pass it as a compiler flag (e.g. -DENABLE_FULL_PRINTF=1).
 */
#ifndef ENABLE_FULL_PRINTF
 #define ENABLE_FULL_PRINTF 0
#endif


/*
 *	ENABLE_FLOAT_PRINTF controls the %f conversion (and the optional .N
 *	precision, default 6) in tiny_printf. It is enabled by default.
 *
 *	Enabling %f adds roughly ~6.7kB of code size, because it pulls in the
 *	toolchain's soft-float routines: a variadic float argument is promoted
 *	to double, which is emulated in software on these modules. On the
 *	integer-only base C0-microSD (RV32I) the cost is larger still. If you
 *	do not log floating-point values, set ENABLE_FLOAT_PRINTF to 0 to
 *	reclaim that space.
 *
 *	%f truncates the integer part to a 32-bit unsigned value, so it is
 *	intended for human-readable debug magnitudes (roughly |x| < 4.29e9),
 *	not exact wide-range formatting. Inf/NaN are not specially handled.
 *
 *	To override the ENABLE_FLOAT_PRINTF flag, define it before including
 *	this header, or pass it as a compiler flag (e.g. -DENABLE_FLOAT_PRINTF=0).
 */
#ifndef ENABLE_FLOAT_PRINTF
 #define ENABLE_FLOAT_PRINTF 1
#endif


/*
 *	Defines the size of the logs packet buffer.
 *	Should be a power of 2 for efficient modulo operations, and small
 *	enough to fit in the device's MMIO window along with other data.
 *	512 bytes is a reasonable default, but it can be adjusted as needed.
 *
 *	To change the logs packet size, define the macro
 *	kSignaloidSoCLoggerConstants_logsPacketSize before including this
 *	header, or pass it as a compiler flag
 *	(e.g. -DkSignaloidSoCLoggerConstants_logsPacketSize=1024).
 */
#ifndef kSignaloidSoCLoggerConstants_logsPacketSize
#define kSignaloidSoCLoggerConstants_logsPacketSize 512
#endif


#include <stdarg.h>
#include <stdint.h>


/*
 *	logs_buffer points at the final logsPacketSize bytes of the device's MMIO window
 *	the pointer itself never changes after init, only its target.
 */
extern volatile const char * logs_buffer;


void
clear_logs_buffer(void);

/*
 * Emit a string literal. sizeof is compile-time so no strlen overhead
 */
void
print_lstr_impl(char * s, unsigned int len);

#define print_lstr(s) print_lstr_impl(s, sizeof(s) - 1)

/*
 * Emit a signed decimal
 */
void
print_int(int v);

/*
 * Emit an unsigned decimal
 */
void
print_uint(unsigned int v);

/*
 * Emit a lowercase hexadecimal
 */
void
print_hex(unsigned int v);

/*
 *	Emit a classic hex dump of `len` bytes starting at `addr`: a relative
 *	offset, 16 hex byte columns, and a printable-ASCII gutter per line.
 *	Useful for inspecting MMIO buffers and raw memory.
 */
void
print_hexdump(const void *addr, unsigned int len);

void
tiny_printf_impl(const char *fmt, ...);

/*
 *	Minimal printf supporting %d, %u, %x, %X, %b, %p, %c, %s and %%,
 *	with an optional zero-pad flag and decimal field width (e.g. %08x).
 *	When ENABLE_FLOAT_PRINTF is 1, also supports %f with an optional
 *	.N precision (default 6, e.g. %.2f).
 *	Requires literal fmt, dispatching to a plain print_lstr when no args
 */
#define tiny_printf(fmt, ...)                                                 \
	do {                                                                  \
		(void) sizeof("" fmt);                                        \
		if (sizeof(#__VA_ARGS__) == 1)                                \
		{                                                             \
			print_lstr(fmt);                                      \
		}                                                             \
		else                                                          \
		{                                                             \
			tiny_printf_impl(fmt, ## __VA_ARGS__);                \
		}                                                             \
	} while (0)

#if ENABLE_FULL_PRINTF == 1
/*
 * 	Debug printf that supports full formatting capabilities, but with the
 *	overhead of a temp buffer and vsnprintf. Use tiny_printf for minimal
 *	overhead when only basic formatting is needed.
 */
void
debug_printf(const char *format, ...);
#else
#define debug_printf tiny_printf
#endif

#define trace() tiny_printf("%s[%s:%d]\n", __FUNCTION__, __FILE__, __LINE__)

#else

/* No-op stubs. Keep the literal-fmt enforcement */
 #define tiny_printf(fmt, ...)  ((void) sizeof("" fmt))
 #define print_lstr(s)          ((void) sizeof("" s))
 #define print_int(v)           ((void) (v))
 #define print_uint(v)          ((void) (v))
 #define print_hex(v)           ((void) (v))
 #define print_hexdump(a, l)    ((void) (a), (void) (l))

 #define clear_logs_buffer()    ((void) 0)
 #define debug_printf(fmt, ...) ((void) sizeof("" fmt))

 #define trace()                ((void) 0)

#endif
