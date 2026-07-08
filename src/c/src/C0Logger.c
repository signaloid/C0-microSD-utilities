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


#include "C0Logger.h"


#if ENABLE_DEBUG_LOGGING == 1


#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#include "C0HAL.h"


volatile const char * logs_buffer = (char *) (
	kC0HALOutputBufferUint8
	+ kC0HALOutputBufferUint8Length
	- kSignaloidSoCLoggerConstants_logsPacketSize
);

char        temp_logs_buffer[kSignaloidSoCLoggerConstants_logsPacketSize];
uint16_t    logs_buffer_start   = 0;
uint16_t    logs_buffer_end     = 0;


void
clear_logs_buffer(void)
{
	memset((void *) logs_buffer, 0x00, kSignaloidSoCLoggerConstants_logsPacketSize);
	memset(temp_logs_buffer, 0x00, kSignaloidSoCLoggerConstants_logsPacketSize);
	logs_buffer_start   = 0;
	logs_buffer_end     = 0;
}

static inline uint16_t
clear_logs_buffer_until_newline(char * buffer, uint16_t start, uint16_t end)
{
	uint16_t new_start = 0;

	for (uint16_t i = start; i < end; i++)
	{
		new_start = i + 1;

		if (buffer[i] == '\n')
		{
			buffer[i] = 0x00;
			break;
		}
		buffer[i] = 0x00;
	}

	return new_start;
}

unsigned int
write_buffer(int _fd, const char * buf, unsigned int len)
{
	(void) _fd;
	uint16_t logs_buffer_end_old = logs_buffer_end;

	for (unsigned int i = 0; i < len; i++)
	{
		temp_logs_buffer[logs_buffer_end] = buf[i];
		logs_buffer_end = (logs_buffer_end + 1) % kSignaloidSoCLoggerConstants_logsPacketSize;
	}

	if (logs_buffer_start < logs_buffer_end && logs_buffer_end < logs_buffer_end_old)
	{
		logs_buffer_start = clear_logs_buffer_until_newline(
			temp_logs_buffer,
			logs_buffer_end,
			logs_buffer_end_old
		);
	}
	else if (logs_buffer_end_old <= logs_buffer_start && logs_buffer_start < logs_buffer_end)
	{
		logs_buffer_start = clear_logs_buffer_until_newline(
			temp_logs_buffer,
			logs_buffer_end,
			kSignaloidSoCLoggerConstants_logsPacketSize
		);

		if (logs_buffer_start == kSignaloidSoCLoggerConstants_logsPacketSize)
		{
			logs_buffer_start = clear_logs_buffer_until_newline(
				temp_logs_buffer,
				0,
				logs_buffer_end_old
			);
		}
	}
	else if (logs_buffer_end < logs_buffer_end_old && logs_buffer_end_old <= logs_buffer_start)
	{
		logs_buffer_start = clear_logs_buffer_until_newline(
			temp_logs_buffer,
			logs_buffer_end,
			logs_buffer_end_old
		);
	}

	memset(
		(void *) logs_buffer,
		0x00,
		kSignaloidSoCLoggerConstants_logsPacketSize
	);

	if (logs_buffer_start < logs_buffer_end)
	{
		memcpy(
			(void *) logs_buffer,
			temp_logs_buffer + logs_buffer_start,
			logs_buffer_end - logs_buffer_start
		);
	}
	else
	{
		memcpy(
			(void *) logs_buffer,
			temp_logs_buffer + logs_buffer_start,
			kSignaloidSoCLoggerConstants_logsPacketSize - logs_buffer_start
		);
		memcpy(
			(void *) logs_buffer + (kSignaloidSoCLoggerConstants_logsPacketSize - logs_buffer_start),
			temp_logs_buffer,
			logs_buffer_end
		);
	}

	return len;
}

void
print_lstr_impl(char * s, unsigned int len)
{
	write_buffer(1, s, len);
}

/*
 *	Shared unsigned integer formatter. Converts `u` to ASCII in the given
 *	`base` (2..16), optionally with uppercase hex digits, left-padding the
 *	result to `width` characters using `pad` (' ' or '0'). A leading '-' is
 *	emitted when `neg` is set; with zero padding the sign precedes the
 *	zeros (e.g. "%04d" of -7 -> "-007").
 *
 *	A 33-byte scratch buffer covers the worst case (base-2 of a 32-bit
 *	value). All decimal/hex/binary printing routes through here so the
 *	digit-conversion loop exists only once.
 */
static void
emit_uint(unsigned int u, unsigned int base, int upper, int width, char pad, int neg)
{
	char                buf[33];
	char *              p       = buf + sizeof(buf);
	const char *        digits  = upper ? "0123456789ABCDEF" : "0123456789abcdef";

	do
	{
		*--p    = digits[u % base];
		u       /= base;
	} while (u);

	int len = (int) ((buf + sizeof(buf)) - p) + (neg ? 1 : 0);

	if (pad == '0')
	{
		if (neg)
		{
			write_buffer(1, "-", 1);
		}
		for (; len < width; len++)
		{
			write_buffer(1, "0", 1);
		}
	}
	else
	{
		for (; len < width; len++)
		{
			write_buffer(1, " ", 1);
		}
		if (neg)
		{
			write_buffer(1, "-", 1);
		}
	}

	write_buffer(1, p, (unsigned int) ((buf + sizeof(buf)) - p));
}

void
print_int(int v)
{
	unsigned int u = (v < 0) ? -(unsigned int) v : (unsigned int) v;

	emit_uint(u, 10, 0, 0, ' ', v < 0);
}

void
print_uint(unsigned int v)
{
	emit_uint(v, 10, 0, 0, ' ', 0);
}

void
print_hex(unsigned int v)
{
	emit_uint(v, 16, 0, 0, ' ', 0);
}

void
print_hexdump(const void * addr, unsigned int len)
{
	const unsigned char * data = (const unsigned char *) addr;

	for (unsigned int off = 0; off < len; off += 16)
	{
		/* relative offset column */
		emit_uint(off, 16, 0, 4, '0', 0);
		write_buffer(1, "  ", 2);

		/* hex byte columns, blank-padded to a fixed width */
		for (unsigned int i = 0; i < 16; i++)
		{
			if (off + i < len)
			{
				emit_uint(data[off + i], 16, 0, 2, '0', 0);
				write_buffer(1, " ", 1);
			}
			else
			{
				write_buffer(1, "   ", 3);
			}
		}

		/* printable-ASCII gutter */
		write_buffer(1, "|", 1);
		for (unsigned int i = 0; i < 16 && (off + i) < len; i++)
		{
			unsigned char b = data[off + i];
			char          c = (b < 0x20 || b > 0x7e) ? '.' : (char) b;
			write_buffer(1, &c, 1);
		}
		write_buffer(1, "|\n", 2);
	}
}

#if ENABLE_FLOAT_PRINTF == 1
/*
 *	Minimal fixed-notation float formatter. Splits `val` into an integer
 *	part and a fractional part scaled to an integer, rounds the fractional
 *	part half-up at integer scale (which avoids the digit-by-digit
 *	truncation error a naive loop would accumulate), and streams
 *	"<int>.<frac>".
 *
 *	Precision is clamped to 9 so the 10^prec scale fits in 32 bits. The
 *	integer part is truncated to 32 bits, so this is for readable debug
 *	magnitudes (roughly |x| < 4.29e9), not exact wide-range output. The
 *	last printed digit may differ by one from a full printf because the
 *	value is held in binary floating point. Inf/NaN are not handled
 *	specially.
 */
static void
emit_float(double val, int prec)
{
	if (prec < 0)
	{
		prec = 6;
	}
	if (prec > 9)
	{
		prec = 9;
	}

	int neg = (val < 0.0);
	if (neg)
	{
		val = -val;
	}

	unsigned int scale = 1;
	for (int i = 0; i < prec; i++)
	{
		scale *= 10;
	}

	unsigned int    ipart   = (unsigned int) val;
	double          frac    = val - (double) ipart;
	unsigned int    fpart   = (unsigned int) ((frac * (double) scale) + 0.5);

	/*
	 *	The fractional part can round up into the integer part
	 *	(e.g. 9.99 at one digit -> 10.0).
	 */
	if (fpart >= scale)
	{
		ipart++;
		fpart -= scale;
	}

	emit_uint(ipart, 10, 0, 0, ' ', neg);

	if (prec > 0)
	{
		write_buffer(1, ".", 1);
		emit_uint(fpart, 10, 0, prec, '0', 0);
	}
}
#endif

void
tiny_printf_impl(const char * fmt, ...)
{
	va_list ap;

	va_start(ap, fmt);
	const char * run = fmt;

	while (*fmt)
	{
		if (*fmt != '%')
		{
			fmt++;
			continue;
		}

		if (fmt > run)
		{
			write_buffer(1, run, (unsigned int) (fmt - run));
		}
		fmt++;

		/*
		 *	Parse an optional zero-pad flag followed by a decimal
		 *	field width, e.g. "%08x" -> pad='0', width=8.
		 */
		char    pad     = ' ';
		int     width   = 0;

		if (*fmt == '0')
		{
			pad = '0';
			fmt++;
		}
		while (*fmt >= '0' && *fmt <= '9')
		{
			width = (width * 10) + (*fmt - '0');
			fmt++;
		}

#if ENABLE_FLOAT_PRINTF == 1
		/*
		 *	optional .N precision, used by %f
		 *	(default applied in emit_float)
		 */
		int precision = -1;

		if (*fmt == '.')
		{
			precision = 0;
			fmt++;
			while (*fmt >= '0' && *fmt <= '9')
			{
				precision = (precision * 10) + (*fmt - '0');
				fmt++;
			}
		}
#endif

		switch (*fmt) {
			case 'd': {
				int v = va_arg(ap, int);
				unsigned int u = (v < 0) ? -(unsigned int) v : (unsigned int) v;
				emit_uint(u, 10, 0, width, pad, v < 0);
				break;
			}

			case 'u':
				emit_uint(va_arg(ap, unsigned int), 10, 0, width, pad, 0);
				break;

			case 'x':
				emit_uint(va_arg(ap, unsigned int), 16, 0, width, pad, 0);
				break;

			case 'X':
				emit_uint(va_arg(ap, unsigned int), 16, 1, width, pad, 0);
				break;

			case 'b':
				emit_uint(va_arg(ap, unsigned int), 2, 0, width, pad, 0);
				break;

			case 'p': {
				void * ptr = va_arg(ap, void *);
				write_buffer(1, "0x", 2);
				emit_uint((unsigned int) (uintptr_t) ptr, 16, 0, width, pad, 0);
				break;
			}

			case 'c': {
				char ch = (char) va_arg(ap, int);
				write_buffer(1, &ch, 1);
				break;
			}

#if ENABLE_FLOAT_PRINTF == 1
			case 'f':
				emit_float(va_arg(ap, double), precision);
				break;
#endif

			case 's': {
				const char * s = va_arg(ap, const char *);
				write_buffer(1, s, strlen(s));
				break;
			}

			case '%':
				write_buffer(1, "%", 1);
				break;

			default:
				write_buffer(1, "%", 1);

				if (*fmt)
				{
					write_buffer(1, fmt, 1);
				}
				break;
		}

		if (*fmt)
		{
			fmt++;
		}
		run = fmt;
	}

	if (fmt > run)
	{
		write_buffer(1, run, (unsigned int) (fmt - run));
	}
	va_end(ap);
}


#if ENABLE_FULL_PRINTF == 1
void
debug_printf(const char * format, ...)
{
	va_list args;

	char temp_buffer[kSignaloidSoCLoggerConstants_logsPacketSize];

	va_start(args, format);
	int ret = vsnprintf(
		(char *) temp_buffer,
		kSignaloidSoCLoggerConstants_logsPacketSize,
		format,
		args
	);
	va_end(args);

	if (ret < 0)
	{
		return;
	}

	if (ret > kSignaloidSoCLoggerConstants_logsPacketSize)
	{
		ret = kSignaloidSoCLoggerConstants_logsPacketSize;
	}

	write_buffer(1, temp_buffer, (unsigned int) ret);
}
#endif

#endif
