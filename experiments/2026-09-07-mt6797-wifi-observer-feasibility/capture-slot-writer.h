/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * Experimental WFC1 slot writer. No production caller or mapping owner yet.
 * The caller must hold exclusive PMSG ownership and serialize every call,
 * including begin, outside NMI context. State lives in ordinary RAM.
 * The mapped payload must have the reviewed fixed header and no ECC.
 * mb() is the native ARM64 dsb(sy); it does not prove reset retention.
 */
#ifndef WFC_SLOT_WRITER_H
#define WFC_SLOT_WRITER_H

#include <linux/crc32.h>
#include <linux/errno.h>
#include <linux/io.h>
#include <linux/string.h>
#include <asm/unaligned.h>

#define WFC_PAYLOAD_BYTES 65524
#define WFC_SLOT_BYTES 128
#define WFC_LAST_SLOT 510
#define WFC_COMMIT 0x57464331

struct wfc_writer {
	u8 __iomem *payload;
	u8 cycle[16];
	unsigned int next;
	bool attempted;
	bool stopped;
};

/* This primitive never resets state or clears retained bytes. */
static int wfc_slot_write(struct wfc_writer *writer, unsigned int kind,
			  u32 transaction, const u8 *payload, size_t length)
{
	u8 record[WFC_SLOT_BYTES] = { 0 };
	u8 __iomem *slot;
	unsigned int i;
	u8 mismatch = 0;
	bool overflow = false;

	if (!writer->attempted || writer->stopped || !writer->payload)
		return -EPERM;
	if (writer->next > WFC_LAST_SLOT || length > 84 ||
	    (length && !payload) || !((kind >= 1 && kind <= 10) ||
				    kind == 255) ||
	    (!writer->next && (kind != 1 || length != 80 || transaction)) ||
	    (writer->next && kind == 1) ||
	    (kind == 255 && (transaction || length != 4 ||
			    get_unaligned_le32(payload) < 1 ||
			    get_unaligned_le32(payload) > 3))) {
		writer->stopped = true;
		return -EINVAL;
	}

	/* Consume the final slot with an overflow terminal, never an event. */
	if (writer->next == WFC_LAST_SLOT && kind != 255) {
		overflow = true;
		kind = 255;
		transaction = 0;
		length = 4;
		put_unaligned_le32(3, record + 36);
	} else if (length) {
		memcpy(record + 36, payload, length);
	}
	memcpy(record, "WFC1", 4);
	put_unaligned_le16(1, record + 4);
	put_unaligned_le16(kind, record + 6);
	put_unaligned_le32(writer->next, record + 8);
	memcpy(record + 12, writer->cycle, sizeof(writer->cycle));
	put_unaligned_le32(transaction, record + 28);
	put_unaligned_le32(length, record + 32);
	put_unaligned_le32(crc32_le(~0U, record, 120) ^ ~0U, record + 120);
	put_unaligned_le32(WFC_COMMIT, record + 124);

	slot = writer->payload + writer->next * WFC_SLOT_BYTES;
	/* Consume the attempt before touching storage: no retry, even on error. */
	writer->stopped = true;
	/* Order prior activity before inspecting the target slot. */
	mb();
	for (i = 0; i < WFC_SLOT_BYTES; i++)
		mismatch |= readb_relaxed(slot + i);
	/* Finish the zero-slot reads before any body store. */
	mb();
	if (mismatch)
		return -EBUSY;
	for (i = 0; i < 124; i++)
		writeb_relaxed(record[i], slot + i);
	/* Complete body stores before their readback. */
	mb();
	/* Check the entire body and still-zero marker before committing. */
	for (i = 0; i < WFC_SLOT_BYTES; i++)
		mismatch |= readb_relaxed(slot + i) ^ (i < 124 ? record[i] : 0);
	/* Complete verification before publishing any marker byte. */
	mb();
	if (mismatch)
		return -EIO;
	for (i = 124; i < WFC_SLOT_BYTES; i++)
		writeb_relaxed(record[i], slot + i);
	/* Complete marker stores before full-record readback. */
	mb();
	for (i = 0; i < WFC_SLOT_BYTES; i++)
		mismatch |= readb_relaxed(slot + i) ^ record[i];
	/* Complete all readback before advancing volatile state. */
	mb();
	if (mismatch)
		return -EIO;
	writer->next++;
	writer->stopped = kind == 255;
	return overflow ? -ENOSPC : 0;
}

/*
 * One attempt on a zero-initialized state. External admission must first
 * preserve old evidence and verify mapping, header, ECC and backend ownership.
 * A successful begin includes a fully read-back identity in slot zero.
 */
static int wfc_writer_begin(struct wfc_writer *writer, u8 __iomem *payload,
			    size_t length, const u8 cycle[16],
			    const u8 identity[80])
{
	u8 nonzero = 0, cycle_nonzero = 0;
	unsigned int i;

	if (writer->attempted)
		return -EPERM;
	writer->attempted = true;
	writer->stopped = true;
	if (!payload || length != WFC_PAYLOAD_BYTES || !cycle || !identity)
		return -EINVAL;
	for (i = 0; i < 16; i++)
		cycle_nonzero |= cycle[i];
	if (!cycle_nonzero)
		return -EINVAL;
	/* Order prior admission work before the complete zero scan. */
	mb();
	for (i = 0; i < WFC_PAYLOAD_BYTES; i++)
		nonzero |= readb_relaxed(payload + i);
	/* Finish the zero scan before enabling the first append. */
	mb();
	if (nonzero)
		return -EBUSY;
	writer->payload = payload;
	memcpy(writer->cycle, cycle, sizeof(writer->cycle));
	writer->next = 0;
	writer->stopped = false;
	return wfc_slot_write(writer, 1, 0, identity, 80);
}

#endif
