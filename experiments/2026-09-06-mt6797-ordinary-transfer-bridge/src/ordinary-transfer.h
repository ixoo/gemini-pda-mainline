/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef MT6797_ORDINARY_TRANSFER_H
#define MT6797_ORDINARY_TRANSFER_H

#ifdef ORDINARY_TRANSFER_HOST_TEST
#include <stddef.h>
#include <stdint.h>
typedef uint8_t u8;
typedef uint32_t u32;
typedef uint64_t u64;
#define MTKE_MAX_BYTES (1024U * 1024U)
#define MTKE_MAX_SECTIONS 256U
struct mt6797_hif;
enum mt6797_section_kind { MT6797_SECTION_ORDINARY, MT6797_SECTION_EMI };
struct mt6797_hif_section_request {
	enum mt6797_section_kind kind;
	const u8 *config;
	size_t config_bytes;
	unsigned int sequence;
	const u8 *data;
	size_t length;
};
struct mt6797_hif_section_result {
	size_t submitted;
	unsigned int firmware_status;
};
#else
#include "hif.h"
#include "mtke.h"
#endif

#define MT6797_ORDINARY_TRANSFER_NO_FAILURE_INDEX ((size_t)-1)

struct mt6797_ordinary_transfer_request {
	enum mt6797_section_kind kind;
	const u8 *config;
	size_t config_bytes;
	unsigned int sequence;
	const u8 *data;
	size_t length;
};

struct mt6797_ordinary_transfer_result {
	size_t completed_sections;
	size_t completed_bytes;
	size_t failed_index;
	int error;
	unsigned int firmware_status;
	size_t partial_submitted;
};

struct mt6797_ordinary_transfer_batch;

/* The caller retains powered ownership, exclusion, generation and all source
 * buffers across preparation and execution. This object makes none of those
 * claims and has no production caller or owner-token escape hatch. */
struct mt6797_ordinary_transfer_batch *
mt6797_ordinary_transfer_prepare(
	const struct mt6797_ordinary_transfer_request *requests, size_t count);

/* Free only after every caller has joined; this releases no HIF/hardware state. */
void mt6797_ordinary_transfer_free(struct mt6797_ordinary_transfer_batch *batch);

/* One absolute monotonic deadline covers the whole batch. The HIF context and
 * result storage must remain disjoint from every retained input span. */
int mt6797_ordinary_transfer_execute(
	struct mt6797_ordinary_transfer_batch *batch, struct mt6797_hif *hif,
	u64 deadline_ns, struct mt6797_ordinary_transfer_result *result);

#ifdef ORDINARY_TRANSFER_HOST_TEST
int mt6797_hif_download_section(struct mt6797_hif *hif,
	const struct mt6797_hif_section_request *request, u64 deadline_ns,
	struct mt6797_hif_section_result *result);
#endif

#endif
