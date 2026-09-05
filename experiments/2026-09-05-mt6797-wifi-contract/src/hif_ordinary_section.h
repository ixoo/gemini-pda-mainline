/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef GEMINI_HIF_ORDINARY_SECTION_H
#define GEMINI_HIF_ORDINARY_SECTION_H
#include "hif_config_phase.h"

enum mt6797_section_kind { MT6797_SECTION_ORDINARY, MT6797_SECTION_EMI };
enum mt6797_section_phase { MT6797_SECTION_NEW, MT6797_SECTION_CONFIG,
	MT6797_SECTION_PAYLOAD, MT6797_SECTION_SUBMITTED, MT6797_SECTION_FAILED };
struct mt6797_ordinary_section {
	enum mt6797_section_phase phase;
	struct mt6797_init_transaction *transaction;
	const unsigned char *data;
	size_t length, submitted;
};
static inline int mt6797_section_fail(struct mt6797_ordinary_section *s)
{
	if (!s) return -EINVAL;
	s->phase=MT6797_SECTION_FAILED;
	if (s->transaction) mt6797_init_abort(s->transaction);
	return -EIO;
}

/* Caller has validated ordinary-section metadata/bytes and retains immutable
 * data, transaction, powered ownership and serialization for the entire phase.
 * EMI is explicitly refused, not silently omitted. No destination permission.
 */
static inline int
mt6797_section_begin(struct mt6797_ordinary_section *s,
	struct mt6797_init_transaction *t, const struct mt6797_hif_pio_io *io,
	enum mt6797_section_kind kind, const unsigned char *config, size_t config_bytes,
	unsigned int sequence, const unsigned char *data, size_t length)
{
	int error;
	if (!s || !t || !data || kind!=MT6797_SECTION_ORDINARY) return -EINVAL;
	if (s->phase!=MT6797_SECTION_NEW) return mt6797_section_fail(s);
	error=mt6797_init_validate_config(config,config_bytes,sequence);
	if (error) return error;
	if (!length || length!=mt6797_init_le32(config+12)) return -EMSGSIZE;
	s->transaction=t; s->data=data; s->length=length; s->submitted=0;
	error=mt6797_config_send(t,io,config,config_bytes,sequence);
	if (error) { mt6797_section_fail(s); return error; }
	s->phase=MT6797_SECTION_CONFIG;
	return 0;
}
static inline int
mt6797_section_ack(struct mt6797_ordinary_section *s,
	const struct mt6797_hif_pio_io *io, unsigned int length, unsigned int *status)
{
	int error;
	if (status) *status=0;
	if (!s) return -EINVAL;
	if (s->phase!=MT6797_SECTION_CONFIG) return mt6797_section_fail(s);
	error=mt6797_config_receive(s->transaction,io,length,status);
	if (error==-EAGAIN) return error;
	if (error) { mt6797_section_fail(s); return error; }
	s->phase=MT6797_SECTION_PAYLOAD;
	s->transaction->phase=MT6797_INIT_PAYLOAD;
	return 0;
}

/* Exactly one <=2048-byte PDA chunk per call; no ACK wait or local credit debit.
 * Scratch must be distinct from immutable section data and all state/I/O objects.
 * At most 2560 bytes needed. Caller checks deadline/ownership between calls.
 */
static inline int
mt6797_section_next(struct mt6797_ordinary_section *s,
	const struct mt6797_hif_pio_io *io, unsigned char *scratch, size_t capacity)
{
	size_t chunk, bytes, i;
	struct mt6797_hif_command command;
	struct mt6797_hif_pio_result result;
	int error;
	if (!s) return -EINVAL;
	if (s->phase!=MT6797_SECTION_PAYLOAD || !s->transaction ||
	    s->transaction->phase!=MT6797_INIT_PAYLOAD || !s->data ||
	    s->submitted>=s->length || !scratch || !io || !io->write)
		return mt6797_section_fail(s);
	chunk=s->length-s->submitted;
	if (chunk>2048) chunk=2048;
	bytes=8+chunk;
	error=mt6797_hif_encode_command(0x34,MT6797_HIF_WRITE,MT6797_HIF_PIO_ONLY,
		bytes,capacity,&command);
	if (error) { mt6797_section_fail(s); return error; }
	for (i=0;i<8;i++) scratch[i]=0;
	scratch[0]=(unsigned char)bytes; scratch[1]=(unsigned char)(bytes>>8);
	scratch[3]=0xc0; scratch[5]=0xa0;
	for (i=0;i<chunk;i++) scratch[8+i]=s->data[s->submitted+i];
	error=mt6797_hif_pio_transfer(io,0x34,MT6797_HIF_WRITE,scratch,bytes,capacity,&result);
	if (error) { mt6797_section_fail(s); return error; }
	s->submitted+=chunk;
	if (s->submitted==s->length) {
		s->phase=MT6797_SECTION_SUBMITTED;
		s->transaction->phase=MT6797_INIT_IDLE;
	}
	return 0;
}
#endif
