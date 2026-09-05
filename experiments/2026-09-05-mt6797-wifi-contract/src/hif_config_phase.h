/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef GEMINI_HIF_CONFIG_PHASE_H
#define GEMINI_HIF_CONFIG_PHASE_H
#include "hif_init_transaction.h"
#include "hif_pio.h"

/* One CONFIG phase, deliberately split at the caller's timed WRPLR wait.
 * Caller holds the existing owner/session/serialization contract throughout.
 * No callback is added beyond the accepted scalar PIO seam.
 */
static inline int
mt6797_config_send(struct mt6797_init_transaction *t,
		   const struct mt6797_hif_pio_io *io,
		   const unsigned char *command, size_t bytes, unsigned int sequence)
{
	unsigned char staging[20];
	struct mt6797_hif_pio_result result;
	size_t i;
	int error;
	if (!t)
		return -EINVAL;
	if (t->phase != MT6797_INIT_IDLE)
		return mt6797_init_abort(t);
	/* Validate the whole exchange's I/O capability before consuming credit. */
	if (!io || !io->write || !io->read)
		return -EINVAL;
	error = mt6797_init_validate_config(command, bytes, sequence);
	if (error)
		return error;
	for (i = 0; i < sizeof(staging); i++)
		staging[i] = command[i];
	error = mt6797_init_begin(t, staging, sizeof(staging), sequence);
	if (error)
		return error;
	error = mt6797_hif_pio_transfer(io, 0x34, MT6797_HIF_WRITE, staging,
				      sizeof(staging), sizeof(staging), &result);
	return mt6797_init_submitted(t, error);
}

/* Caller supplies this session's port-0 logical WRPLR length after a timed wait.
 * Zero returns EAGAIN without I/O. Exact length triggers one 32-byte PIO read
 * and validation of its first 28 bytes. No raw reply escapes this function.
 */
static inline int
mt6797_config_receive(struct mt6797_init_transaction *t,
		      const struct mt6797_hif_pio_io *io, unsigned int length,
		      unsigned int *firmware_status)
{
	unsigned char staging[32];
	struct mt6797_hif_command span;
	struct mt6797_hif_pio_result result;
	int error;
	if (firmware_status)
		*firmware_status = 0;
	if (!io || !io->read || !io->write || !firmware_status) {
		if (t)
			mt6797_init_abort(t);
		return -EINVAL;
	}
	error = mt6797_init_prepare_reply(t, length, sizeof(staging), &span);
	if (error)
		return error;
	error = mt6797_hif_pio_transfer(io, 0x50, MT6797_HIF_READ, staging,
				      span.transfer_bytes, sizeof(staging), &result);
	if (error)
		return mt6797_init_abort(t);
	return mt6797_init_accept_reply(t, staging, 28, firmware_status);
}
#endif
