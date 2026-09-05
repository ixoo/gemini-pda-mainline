/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef GEMINI_HIF_PIO_H
#define GEMINI_HIF_PIO_H
#include "hif_command.h"

/* Offset-relative, ordered scalar I/O. Return zero on success, else error.
 * A kernel adapter uses writel/readl on its held mapping. No status emulation.
 */
struct mt6797_hif_pio_io {
	void *context;
	int (*write)(void *context, unsigned int offset, unsigned int value);
	int (*read)(void *context, unsigned int offset, unsigned int *value);
};

struct mt6797_hif_pio_result {
	size_t data_bytes;
	bool setup_submitted;
	bool transfer_complete;
};

/* Caller holds powered mapping, driver ownership and setup/data serialization.
 * Credits/RX length, session validity and response completion belong to caller.
 * TX reads only payload bytes and supplies zero padding; RX stores padded bytes.
 * Zero return means finite submission/read completed, not firmware success.
 * An I/O error may have side effects: no retry, rollback or credit refund.
 */
static inline int mt6797_hif_pio_transfer(const struct mt6797_hif_pio_io *io,
					  unsigned int port,
					  enum mt6797_hif_direction direction,
					  unsigned char *buffer,
					  size_t payload_bytes, size_t capacity,
					  struct mt6797_hif_pio_result *result)
{
	struct mt6797_hif_command command;
	size_t offset;
	unsigned int byte, word;
	int error;

	if (!result)
		return -EINVAL;
	*result = (struct mt6797_hif_pio_result){0};
	if (!io || !io->write || !buffer ||
	    (direction == MT6797_HIF_READ && !io->read))
		return -EINVAL;
	error = mt6797_hif_encode_command(port, direction, MT6797_HIF_PIO_ONLY,
					  payload_bytes, capacity, &command);
	if (error)
		return error;
	if (io->write(io->context, 0, command.word))
		return -EIO;
	result->setup_submitted = true;
	for (offset = 0; offset < command.transfer_bytes; offset += 4) {
		word = 0;
		if (direction == MT6797_HIF_WRITE) {
			for (byte = 0; byte < 4; byte++)
				if (offset + byte < payload_bytes)
					word |= (unsigned int)
							buffer[offset + byte]
						<< (byte * 8);
			error = io->write(io->context, 0x1000, word);
		} else {
			error = io->read(io->context, 0x1000, &word);
			if (!error)
				for (byte = 0; byte < 4; byte++)
					buffer[offset + byte] =
						(unsigned char)(word >>
								(byte * 8));
		}
		if (error)
			return -EIO;
		result->data_bytes += 4;
	}
	result->transfer_complete = true;
	return 0;
}

#endif
