// SPDX-License-Identifier: GPL-2.0-only
#ifdef ORDINARY_TRANSFER_HOST_TEST
#include <errno.h>
#include <limits.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#else
#include <linux/errno.h>
#include <linux/kernel.h>
#include <linux/ktime.h>
#include <linux/slab.h>
#include <linux/string.h>
#endif
#include "ordinary-transfer.h"

#define MT6797_ORDINARY_TRANSFER_CONFIG_BYTES 20U

#ifdef ORDINARY_TRANSFER_HOST_TEST
static unsigned int mt6797_init_le16(const u8 *p)
{
	return (unsigned int)p[0] | (unsigned int)p[1] << 8;
}

static unsigned int mt6797_init_le32(const u8 *p)
{
	return mt6797_init_le16(p) | mt6797_init_le16(p + 2) << 16;
}

static int mt6797_init_validate_config(const u8 *p, size_t bytes,
				       unsigned int sequence)
{
	unsigned int address, length, mode;

	if (!p || sequence > 255U)
		return -EINVAL;
	if (bytes != 20 || mt6797_init_le16(p) != 20 ||
	    mt6797_init_le16(p + 2) != 0x8000 || p[4] != 1 || p[5] != 0xa0 ||
	    p[6] || p[7] != sequence)
		return -EPROTO;
	address = mt6797_init_le32(p + 8);
	length = mt6797_init_le32(p + 12);
	mode = mt6797_init_le32(p + 16);
	if (!length || length - 1U > 0xffffffffU - address ||
	    (mode & ~0x8000000fU) || !(mode & 0x80000000U) ||
	    ((mode & 6U) && !(mode & 1U)))
		return -EPROTO;
	return 0;
}
#endif

struct mt6797_ordinary_transfer_batch {
	const struct mt6797_ordinary_transfer_request *request_start;
	size_t request_bytes;
	size_t count;
	size_t aggregate_bytes;
	int attempted;
	int first_error;
	struct mt6797_ordinary_transfer_request requests[MTKE_MAX_SECTIONS];
};

#ifdef ORDINARY_TRANSFER_HOST_TEST
static void *ordinary_zalloc(size_t size)
{
	return calloc(1, size);
}

static void ordinary_free(void *pointer)
{
	free(pointer);
}

static u64 ordinary_now_ns(void)
{
	struct timespec now;

	if (clock_gettime(CLOCK_MONOTONIC, &now))
		return UINT64_MAX;
	return (u64)now.tv_sec * 1000000000ULL + (u64)now.tv_nsec;
}
#else
static void *ordinary_zalloc(size_t size)
{
	return kzalloc(size, GFP_KERNEL);
}

static void ordinary_free(void *pointer)
{
	kfree(pointer);
}

static u64 ordinary_now_ns(void)
{
	return ktime_get_ns();
}
#endif

static int ordinary_span(const void *pointer, size_t bytes,
			 unsigned long *start, unsigned long *end)
{
	unsigned long address = (unsigned long)pointer;

	if (!pointer || !bytes || bytes > ULONG_MAX - address)
		return -EOVERFLOW;
	*start = address;
	*end = address + bytes;
	return 0;
}

static int ordinary_disjoint(const void *left, size_t left_bytes,
			     const void *right, size_t right_bytes)
{
	unsigned long left_start, left_end, right_start, right_end;

	if (ordinary_span(left, left_bytes, &left_start, &left_end) ||
	    ordinary_span(right, right_bytes, &right_start, &right_end))
		return 0;
	return left_end <= right_start || right_end <= left_start;
}

static int
ordinary_request_spans_valid(const struct mt6797_ordinary_transfer_request *requests,
			     size_t count,
			     const struct mt6797_ordinary_transfer_batch *batch)
{
	size_t i, j;

	if (!ordinary_disjoint(requests, count * sizeof(*requests), batch,
			       sizeof(*batch)))
		return -EOVERFLOW;
	for (i = 0; i < count; i++) {
		const struct mt6797_ordinary_transfer_request *request = &requests[i];

		if (!ordinary_disjoint(requests, count * sizeof(*requests),
				       request->config, request->config_bytes) ||
		    !ordinary_disjoint(requests, count * sizeof(*requests),
				       request->data, request->length) ||
		    !ordinary_disjoint(batch, sizeof(*batch), request->config,
				       request->config_bytes) ||
		    !ordinary_disjoint(batch, sizeof(*batch), request->data,
				       request->length) ||
		    !ordinary_disjoint(request->config, request->config_bytes,
				       request->data, request->length))
			return -EINVAL;
		for (j = 0; j < i; j++) {
			if (!ordinary_disjoint(request->config, request->config_bytes,
					       requests[j].config,
					       requests[j].config_bytes) ||
			    !ordinary_disjoint(request->config, request->config_bytes,
					       requests[j].data, requests[j].length) ||
			    !ordinary_disjoint(request->data, request->length,
					       requests[j].config,
					       requests[j].config_bytes) ||
			    !ordinary_disjoint(request->data, request->length,
					       requests[j].data, requests[j].length))
				return -EINVAL;
		}
	}
	return 0;
}

struct mt6797_ordinary_transfer_batch *
mt6797_ordinary_transfer_prepare(const struct mt6797_ordinary_transfer_request *requests,
				 size_t count)
{
	struct mt6797_ordinary_transfer_batch *batch;
	size_t i, aggregate = 0;

	if (!requests || !count || count > MTKE_MAX_SECTIONS ||
	    count > (size_t)-1 / sizeof(*requests))
		return NULL;
	batch = ordinary_zalloc(sizeof(*batch));
	if (!batch)
		return NULL;
	if (ordinary_request_spans_valid(requests, count, batch))
		goto fail;
	for (i = 0; i < count; i++) {
		const struct mt6797_ordinary_transfer_request *request = &requests[i];
		size_t j;

		if (request->kind != MT6797_SECTION_ORDINARY || !request->config ||
		    request->config_bytes != MT6797_ORDINARY_TRANSFER_CONFIG_BYTES ||
		    !request->data || !request->length ||
		    request->length > MTKE_MAX_BYTES ||
		    request->sequence == 0 || request->sequence > 255U ||
		    mt6797_init_validate_config(request->config, request->config_bytes,
						request->sequence) ||
		    mt6797_init_le32(request->config + 12) != request->length ||
		    aggregate > MTKE_MAX_BYTES - request->length)
			goto fail;
		for (j = 0; j < i; j++)
			if (request->sequence == batch->requests[j].sequence)
				goto fail;
		aggregate += request->length;
		batch->requests[i] = *request;
	}
	batch->request_start = requests;
	batch->request_bytes = count * sizeof(*requests);
	batch->count = count;
	batch->aggregate_bytes = aggregate;
	return batch;
fail:
	ordinary_free(batch);
	return NULL;
}

void mt6797_ordinary_transfer_free(struct mt6797_ordinary_transfer_batch *batch)
{
	if (batch)
		ordinary_free(batch);
}

static int
ordinary_result_spans_valid(const struct mt6797_ordinary_transfer_batch *batch,
			    const struct mt6797_ordinary_transfer_result *result)
{
	size_t i;

	if (!ordinary_disjoint(result, sizeof(*result), batch, sizeof(*batch)) ||
	    !ordinary_disjoint(result, sizeof(*result), batch->request_start,
			       batch->request_bytes))
		return 0;
	for (i = 0; i < batch->count; i++) {
		const struct mt6797_ordinary_transfer_request *request =
			&batch->requests[i];

		if (!ordinary_disjoint(result, sizeof(*result), request->config,
				       request->config_bytes) ||
		    !ordinary_disjoint(result, sizeof(*result), request->data,
				       request->length))
			return 0;
	}
	return 1;
}

int
mt6797_ordinary_transfer_execute(struct mt6797_ordinary_transfer_batch *batch,
				 struct mt6797_hif *hif, u64 deadline_ns,
				 struct mt6797_ordinary_transfer_result *result)
{
	size_t i;

	if (!batch || !hif || !result || batch->attempted || batch->first_error)
		return -EINVAL;
	if (!ordinary_result_spans_valid(batch, result))
		return -EINVAL;
	*result = (struct mt6797_ordinary_transfer_result){
		.failed_index = MT6797_ORDINARY_TRANSFER_NO_FAILURE_INDEX};
	batch->attempted = 1;
	if (!deadline_ns || ordinary_now_ns() >= deadline_ns) {
		batch->first_error = -ETIMEDOUT;
		result->error = batch->first_error;
		return batch->first_error;
	}
	for (i = 0; i < batch->count; i++) {
		struct mt6797_hif_section_request request = {
			.kind = batch->requests[i].kind,
			.config = batch->requests[i].config,
			.config_bytes = batch->requests[i].config_bytes,
			.sequence = batch->requests[i].sequence,
			.data = batch->requests[i].data,
			.length = batch->requests[i].length,
		};
		struct mt6797_hif_section_result section = {0};
		int error;

		error = mt6797_hif_download_section(hif, &request, deadline_ns,
						    &section);
		if (error || section.submitted != request.length) {
			if (!error)
				error = -EPROTO;
			batch->first_error = error;
			result->failed_index = i;
			result->error = error;
			result->firmware_status = section.firmware_status;
			result->partial_submitted = section.submitted;
			return error;
		}
		result->completed_sections++;
		result->completed_bytes += request.length;
	}
	return 0;
}
