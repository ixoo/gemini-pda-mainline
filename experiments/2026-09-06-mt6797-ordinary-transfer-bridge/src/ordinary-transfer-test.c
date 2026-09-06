// SPDX-License-Identifier: MIT
#include <stdio.h>
#include <errno.h>
#include <limits.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "ordinary-transfer.h"

static unsigned int calls;
static unsigned int fail_at;
static u64 expected_deadline;
static int short_success;
static int reject_extended_deadline;
static const struct mt6797_ordinary_transfer_request *expected_requests;
static size_t expected_request_count;
static unsigned int callback_identity_errors;

static u64 test_deadline_after(u64 delay_ns)
{
	struct timespec now;

	if (clock_gettime(CLOCK_MONOTONIC, &now))
		return 0;
	return (u64)now.tv_sec * 1000000000ULL + (u64)now.tv_nsec +
		delay_ns;
}

static u64 test_future_deadline(void)
{
	return test_deadline_after(500000000ULL);
}

int mt6797_hif_download_section(struct mt6797_hif *hif,
	const struct mt6797_hif_section_request *request, u64 deadline_ns,
	struct mt6797_hif_section_result *result)
{
	unsigned int index = calls++;
	const struct mt6797_ordinary_transfer_request *expected;

	(void)hif;
	if (deadline_ns != expected_deadline)
		return -22;
	if (!request || !result)
		return -22;
	if (expected_requests) {
		if (index >= expected_request_count) {
			callback_identity_errors++;
			return -22;
		}
		expected = &expected_requests[index];
		if (request->kind != expected->kind ||
		    request->config != expected->config ||
		    request->config_bytes != expected->config_bytes ||
		    request->sequence != expected->sequence ||
		    request->data != expected->data ||
		    request->length != expected->length) {
			callback_identity_errors++;
			return -22;
		}
	}
	if (reject_extended_deadline)
		return -EINVAL;
	if (index == fail_at) {
		result->submitted = request->length / 2;
		result->firmware_status = 0x40 + index + 1;
		return -5;
	}
	if (short_success) {
		result->submitted = request->length / 2;
		return 0;
	}
	result->submitted = request->length;
	result->firmware_status = 0;
	return 0;
}

#define CHECK(condition) do { \
	if (!(condition)) { \
		fprintf(stderr, "FAIL:%s:%d: %s\n", __FILE__, __LINE__, #condition); \
		return 1; \
	} \
} while (0)

static void make_config(u8 *config, size_t length, unsigned int sequence)
{
	memset(config, 0, 20);
	config[0] = 20;
	config[3] = 0x80;
	config[4] = 1;
	config[5] = 0xa0;
	config[7] = (u8)sequence;
	config[12] = (u8)length;
	config[13] = (u8)(length >> 8);
	config[14] = (u8)(length >> 16);
	config[15] = (u8)(length >> 24);
	config[16] = 0;
	config[17] = 0;
	config[18] = 0;
	config[19] = 0x80;
}

static int test_happy_and_repeat(void)
{
	u8 configs[2][20], data0[3] = {1, 2, 3}, data1[4] = {4, 5, 6, 7};
	struct mt6797_ordinary_transfer_request requests[2];
	struct mt6797_ordinary_transfer_request saved_requests;
	u8 saved_configs[2][20], saved_data0[3], saved_data1[4];
	struct mt6797_ordinary_transfer_batch *batch;
	struct mt6797_ordinary_transfer_result result = {9, 9, 9, 9, 9, 9};
	u64 deadline;

	make_config(configs[0], sizeof(data0), 1);
	make_config(configs[1], sizeof(data1), 2);
	requests[0] = (struct mt6797_ordinary_transfer_request){
		MT6797_SECTION_ORDINARY, configs[0], 20, 1, data0, sizeof(data0)};
	requests[1] = (struct mt6797_ordinary_transfer_request){
		MT6797_SECTION_ORDINARY, configs[1], 20, 2, data1, sizeof(data1)};
	batch = mt6797_ordinary_transfer_prepare(requests, 2);
	CHECK(batch != NULL);
	saved_requests = requests[0];
	memcpy(saved_configs, configs, sizeof(configs));
	memcpy(saved_data0, data0, sizeof(data0));
	memcpy(saved_data1, data1, sizeof(data1));
	deadline = test_future_deadline();
	CHECK(deadline != 0);
	calls = 0; fail_at = 100; expected_deadline = deadline;
	expected_requests = requests; expected_request_count = 2;
	callback_identity_errors = 0;
	CHECK(mt6797_ordinary_transfer_execute(batch, (void *)1, deadline,
		&result) == 0);
	CHECK(calls == 2 && result.completed_sections == 2 &&
	      result.completed_bytes == 7 &&
	      result.failed_index == MT6797_ORDINARY_TRANSFER_NO_FAILURE_INDEX &&
	      result.error == 0 && result.firmware_status == 0 &&
	      result.partial_submitted == 0 && callback_identity_errors == 0);
	CHECK(memcmp(&saved_requests, &requests[0], sizeof(saved_requests)) == 0 &&
	      memcmp(saved_configs, configs, sizeof(configs)) == 0 &&
	      memcmp(saved_data0, data0, sizeof(data0)) == 0 &&
	      memcmp(saved_data1, data1, sizeof(data1)) == 0);
	CHECK(mt6797_ordinary_transfer_execute(batch, (void *)1, deadline,
		&result) == -22 && calls == 2);
	mt6797_ordinary_transfer_free(batch);
	return 0;
}

static int test_prepare_refusals(void)
{
	u8 config[20], config2[20], data[4] = {0}, data2[4] = {0};
	struct mt6797_ordinary_transfer_request request;
	struct mt6797_ordinary_transfer_request duplicate[2];
	struct mt6797_ordinary_transfer_batch *batch;

	make_config(config, sizeof(data), 1);
	request = (struct mt6797_ordinary_transfer_request){
		MT6797_SECTION_ORDINARY, config, 20, 1, data, sizeof(data)};
	CHECK(mt6797_ordinary_transfer_prepare(NULL, 1) == NULL);
	CHECK(mt6797_ordinary_transfer_prepare(&request, 0) == NULL);
	CHECK(mt6797_ordinary_transfer_prepare(&request,
		MTKE_MAX_SECTIONS + 1) == NULL);
	request.kind = MT6797_SECTION_EMI;
	CHECK(mt6797_ordinary_transfer_prepare(&request, 1) == NULL);
	request.kind = MT6797_SECTION_ORDINARY;
	request.sequence = 0;
	CHECK(mt6797_ordinary_transfer_prepare(&request, 1) == NULL);
	request.sequence = 1; config[7] = 2;
	CHECK(mt6797_ordinary_transfer_prepare(&request, 1) == NULL);
	config[7] = 1; config[12] = 3;
	CHECK(mt6797_ordinary_transfer_prepare(&request, 1) == NULL);
	config[12] = 4; request.data = NULL;
	CHECK(mt6797_ordinary_transfer_prepare(&request, 1) == NULL);
	request.data = data;
	request.length = MTKE_MAX_BYTES + 1;
	CHECK(mt6797_ordinary_transfer_prepare(&request, 1) == NULL);
	request.length = sizeof(data);
	request.config = data;
	request.config_bytes = 20;
	CHECK(mt6797_ordinary_transfer_prepare(&request, 1) == NULL);
	request.config = config;
	config[0] = 19;
	CHECK(mt6797_ordinary_transfer_prepare(&request, 1) == NULL);
	make_config(config, sizeof(data), 1); config[4] = 2;
	CHECK(mt6797_ordinary_transfer_prepare(&request, 1) == NULL);
	make_config(config, sizeof(data), 1); config[5] = 1;
	CHECK(mt6797_ordinary_transfer_prepare(&request, 1) == NULL);
	make_config(config, sizeof(data), 1); config[16] = 0x10;
	CHECK(mt6797_ordinary_transfer_prepare(&request, 1) == NULL);
	make_config(config, sizeof(data), 1);
	config[8] = config[9] = config[10] = config[11] = 0xff;
	CHECK(mt6797_ordinary_transfer_prepare(&request, 1) == NULL);
	make_config(config, sizeof(data), 1);
	make_config(config2, sizeof(data2), 1);
	duplicate[0] = request;
	duplicate[1] = (struct mt6797_ordinary_transfer_request){
		MT6797_SECTION_ORDINARY, config2, 20, 1, data2, sizeof(data2)};
	CHECK(mt6797_ordinary_transfer_prepare(duplicate, 2) == NULL);
	request.config = (u8 *)(uintptr_t)-8;
	CHECK(mt6797_ordinary_transfer_prepare(&request, 1) == NULL);
	(void)batch;
	return 0;
}

static int test_aggregate_boundary(void)
{
	u8 config0[20], config1[20];
	u8 *data0 = malloc(MTKE_MAX_BYTES);
	u8 *data1 = malloc(MTKE_MAX_BYTES);
	struct mt6797_ordinary_transfer_request requests[2];
	struct mt6797_ordinary_transfer_batch *batch;
	struct mt6797_ordinary_transfer_result result = {0};
	u64 deadline;

	CHECK(data0 != NULL && data1 != NULL);
	make_config(config0, MTKE_MAX_BYTES, 1);
	make_config(config1, MTKE_MAX_BYTES, 2);
	requests[0] = (struct mt6797_ordinary_transfer_request){
		MT6797_SECTION_ORDINARY, config0, 20, 1, data0,
		MTKE_MAX_BYTES};
	requests[1] = (struct mt6797_ordinary_transfer_request){
		MT6797_SECTION_ORDINARY, config1, 20, 2, data1,
		MTKE_MAX_BYTES};
	batch = mt6797_ordinary_transfer_prepare(requests, 1);
	CHECK(batch != NULL);
	deadline = test_future_deadline();
	CHECK(deadline != 0);
	calls = 0; fail_at = UINT_MAX; expected_deadline = deadline;
	expected_requests = requests; expected_request_count = 1;
	callback_identity_errors = 0;
	CHECK(mt6797_ordinary_transfer_execute(batch, (void *)1, deadline,
		&result) == 0 && result.completed_bytes == MTKE_MAX_BYTES &&
		callback_identity_errors == 0);
	mt6797_ordinary_transfer_free(batch);
	CHECK(mt6797_ordinary_transfer_prepare(requests, 2) == NULL);
	free(data0);
	free(data1);
	return 0;
}

static int test_failure_accounting_and_deadline(void)
{
	u8 configs[3][20], data[3][2] = {{1, 2}, {3, 4}, {5, 6}};
	struct mt6797_ordinary_transfer_request requests[3];
	struct mt6797_ordinary_transfer_batch *batch;
	struct mt6797_ordinary_transfer_result result;
	u64 deadline;
	unsigned int i;

	for (i = 0; i < 3; i++) {
		make_config(configs[i], 2, i + 1);
		requests[i] = (struct mt6797_ordinary_transfer_request){
			MT6797_SECTION_ORDINARY, configs[i], 20, i + 1,
			data[i], 2};
	}
	for (i = 0; i < 3; i++) {
		batch = mt6797_ordinary_transfer_prepare(requests, 3);
		CHECK(batch != NULL);
		deadline = test_future_deadline();
		CHECK(deadline != 0);
		calls = 0; fail_at = i; expected_deadline = deadline;
		expected_requests = requests; expected_request_count = 3;
		callback_identity_errors = 0;
		result = (struct mt6797_ordinary_transfer_result){7, 7, 7, 7, 7, 7};
		CHECK(mt6797_ordinary_transfer_execute(batch, (void *)1, deadline,
			&result) == -5);
		CHECK(calls == i + 1 && result.completed_sections == i &&
		      result.completed_bytes == i * 2 && result.failed_index == i &&
		      result.error == -5 && result.firmware_status == 0x41 + i &&
		      result.partial_submitted == 1 && callback_identity_errors == 0);
		CHECK(mt6797_ordinary_transfer_execute(batch, (void *)1, deadline,
			&result) == -22 && calls == i + 1);
		mt6797_ordinary_transfer_free(batch);
	}
	batch = mt6797_ordinary_transfer_prepare(requests, 3);
	CHECK(batch != NULL); calls = 0;
	expected_requests = requests; expected_request_count = 3;
	result = (struct mt6797_ordinary_transfer_result){7, 7, 7, 7, 7, 7};
	CHECK(mt6797_ordinary_transfer_execute(batch, (void *)1, 1, &result) == -ETIMEDOUT);
	CHECK(calls == 0 && result.completed_sections == 0 &&
	      result.failed_index == MT6797_ORDINARY_TRANSFER_NO_FAILURE_INDEX);
	mt6797_ordinary_transfer_free(batch);
	return 0;
}

static int test_extended_deadline_terminal(void)
{
	u8 config[20], data[4] = {0};
	struct mt6797_ordinary_transfer_request request;
	struct mt6797_ordinary_transfer_batch *batch;
	struct mt6797_ordinary_transfer_result result = {7, 7, 7, 7, 7, 7};
	u64 deadline;

	make_config(config, sizeof(data), 1);
	request = (struct mt6797_ordinary_transfer_request){
		MT6797_SECTION_ORDINARY, config, 20, 1, data, sizeof(data)};
	batch = mt6797_ordinary_transfer_prepare(&request, 1);
	CHECK(batch != NULL);
	/* The real HIF refuses a remaining budget above one second. */
	deadline = test_deadline_after(2000000000ULL);
	CHECK(deadline != 0);
	calls = 0; fail_at = UINT_MAX; expected_deadline = deadline;
	expected_requests = &request; expected_request_count = 1;
	callback_identity_errors = 0; reject_extended_deadline = 1;
	CHECK(mt6797_ordinary_transfer_execute(batch, (void *)1, deadline,
		&result) == -EINVAL);
	CHECK(calls == 1 && callback_identity_errors == 0 &&
	      result.completed_sections == 0 && result.completed_bytes == 0 &&
	      result.failed_index == 0 && result.error == -EINVAL &&
	      result.firmware_status == 0 && result.partial_submitted == 0);
	CHECK(mt6797_ordinary_transfer_execute(batch, (void *)1, deadline,
		&result) == -EINVAL && calls == 1);
	reject_extended_deadline = 0;
	mt6797_ordinary_transfer_free(batch);
	return 0;
}

static int test_maximum_inventory_and_adjacent_ranges(void)
{
	const size_t count = 255;
	u8 *configs = calloc(count, 20), *data = calloc(count, 1);
	struct mt6797_ordinary_transfer_request *requests = calloc(count, sizeof(*requests));
	struct mt6797_ordinary_transfer_batch *batch;
	struct mt6797_ordinary_transfer_result result = {0};
	struct mt6797_ordinary_transfer_request *exact_requests;
	u8 *exact_configs, *exact_data;
	const size_t exact_count = MTKE_MAX_SECTIONS;
	unsigned int i;
	u8 arena[24];
	struct mt6797_ordinary_transfer_request adjacent;
	u64 deadline;

	CHECK(configs != NULL && data != NULL && requests != NULL);
	for (i = 0; i < count; i++) {
		make_config(configs + i * 20, 1, i + 1);
		data[i] = (u8)i;
		requests[i] = (struct mt6797_ordinary_transfer_request){
			MT6797_SECTION_ORDINARY, configs + i * 20, 20, i + 1,
			data + i, 1};
	}
	batch = mt6797_ordinary_transfer_prepare(requests, count);
	CHECK(batch != NULL); calls = 0; fail_at = UINT_MAX;
	deadline = test_future_deadline();
	CHECK(deadline != 0);
	expected_deadline = deadline;
	expected_requests = requests; expected_request_count = count;
	callback_identity_errors = 0;
	CHECK(mt6797_ordinary_transfer_execute(batch, (void *)1, deadline,
		&result) == 0 && calls == count && result.completed_sections == count &&
		callback_identity_errors == 0);
	mt6797_ordinary_transfer_free(batch);
	/* Exactly the parser inventory limit still refuses duplicate sequences. */
	exact_configs = calloc(exact_count, 20);
	exact_data = calloc(exact_count, 1);
	exact_requests = calloc(exact_count, sizeof(*exact_requests));
	CHECK(exact_configs != NULL && exact_data != NULL && exact_requests != NULL);
	for (i = 0; i < exact_count; i++) {
		unsigned int sequence = i < 255 ? i + 1 : 1;

		make_config(exact_configs + i * 20, 1, sequence);
		exact_requests[i] = (struct mt6797_ordinary_transfer_request){
			MT6797_SECTION_ORDINARY, exact_configs + i * 20, 20, sequence,
			exact_data + i, 1};
	}
	CHECK(mt6797_ordinary_transfer_prepare(exact_requests, exact_count) == NULL);
	free(exact_requests); free(exact_configs); free(exact_data);

	make_config(arena, 4, 1);
	memset(arena + 20, 0x5a, 4);
	adjacent = (struct mt6797_ordinary_transfer_request){
		MT6797_SECTION_ORDINARY, arena, 20, 1, arena + 20, 4};
	batch = mt6797_ordinary_transfer_prepare(&adjacent, 1);
	CHECK(batch != NULL);
	mt6797_ordinary_transfer_free(batch);
	free(requests); free(configs); free(data);
	return 0;
}

static int test_pairwise_refusals(void)
{
	u8 configs[2][20], data[8];
	struct mt6797_ordinary_transfer_request requests[2];
	struct mt6797_ordinary_transfer_batch *batch;
	struct mt6797_ordinary_transfer_request saved_requests[2];
	u8 saved_configs[2][20], saved_data[8];

	memset(data, 0x3c, sizeof(data));
	make_config(configs[0], 4, 1); make_config(configs[1], 4, 2);
	requests[0] = (struct mt6797_ordinary_transfer_request){
		MT6797_SECTION_ORDINARY, configs[0], 20, 1, data, 4};
	requests[1] = (struct mt6797_ordinary_transfer_request){
		MT6797_SECTION_ORDINARY, configs[1], 20, 2, data + 4, 4};
	memcpy(saved_requests, requests, sizeof(requests));
	memcpy(saved_configs, configs, sizeof(saved_configs));
	memcpy(saved_data, data, sizeof(data));
	requests[1].data = data + 3;
	CHECK(mt6797_ordinary_transfer_prepare(requests, 2) == NULL);
	requests[1].data = data + 4;
	requests[1].config = data;
	CHECK(mt6797_ordinary_transfer_prepare(requests, 2) == NULL);
	requests[1].config = (u8 *)requests + sizeof(requests) - 1;
	CHECK(mt6797_ordinary_transfer_prepare(requests, 2) == NULL);
	CHECK(memcmp(saved_requests, requests, sizeof(requests)) != 0);
	/* Restore valid descriptors and snapshot them immediately before alias tests. */
	requests[1].config = configs[1];
	memcpy(saved_requests, requests, sizeof(saved_requests));
	memcpy(saved_configs, configs, sizeof(saved_configs));
	memcpy(saved_data, data, sizeof(saved_data));
	batch = mt6797_ordinary_transfer_prepare(requests, 2);
	CHECK(batch != NULL); calls = 0; expected_deadline = UINT64_MAX;
	expected_requests = NULL; expected_request_count = 0;
	CHECK(mt6797_ordinary_transfer_execute(batch, (void *)1, UINT64_MAX,
		(struct mt6797_ordinary_transfer_result *)requests) == -EINVAL);
	CHECK(calls == 0);
	CHECK(mt6797_ordinary_transfer_execute(batch, (void *)1, UINT64_MAX,
		(struct mt6797_ordinary_transfer_result *)((u8 *)requests + 1)) == -EINVAL);
	CHECK(calls == 0);
	CHECK(mt6797_ordinary_transfer_execute(batch, (void *)1, UINT64_MAX,
		(struct mt6797_ordinary_transfer_result *)configs[0]) == -EINVAL);
	CHECK(calls == 0);
	CHECK(mt6797_ordinary_transfer_execute(batch, (void *)1, UINT64_MAX,
		(struct mt6797_ordinary_transfer_result *)data) == -EINVAL);
	CHECK(calls == 0);
	CHECK(mt6797_ordinary_transfer_execute(batch, (void *)1, UINT64_MAX,
		(struct mt6797_ordinary_transfer_result *)((u8 *)batch + 1)) == -EINVAL);
	CHECK(calls == 0);
	CHECK(mt6797_ordinary_transfer_execute(batch, (void *)1, UINT64_MAX,
		(struct mt6797_ordinary_transfer_result *)(UINTPTR_MAX -
			sizeof(struct mt6797_ordinary_transfer_result) + 2)) == -EINVAL);
	CHECK(calls == 0);
	CHECK(memcmp(saved_requests, requests, sizeof(saved_requests)) == 0 &&
	      memcmp(saved_configs, configs, sizeof(saved_configs)) == 0 &&
	      memcmp(saved_data, data, sizeof(data)) == 0);
	mt6797_ordinary_transfer_free(batch);
	return 0;
}

static int test_short_success_is_failure(void)
{
	u8 config[20], data[8];
	struct mt6797_ordinary_transfer_request request;
	struct mt6797_ordinary_transfer_batch *batch;
	struct mt6797_ordinary_transfer_result result;
	u64 deadline;

	make_config(config, sizeof(data), 1); memset(data, 0x11, sizeof(data));
	request = (struct mt6797_ordinary_transfer_request){
		MT6797_SECTION_ORDINARY, config, 20, 1, data, sizeof(data)};
	batch = mt6797_ordinary_transfer_prepare(&request, 1);
	CHECK(batch != NULL); calls = 0; fail_at = UINT_MAX;
	deadline = test_future_deadline();
	CHECK(deadline != 0);
	expected_deadline = deadline; expected_requests = &request;
	expected_request_count = 1; callback_identity_errors = 0;
	short_success = 1; result = (struct mt6797_ordinary_transfer_result){0};
	CHECK(mt6797_ordinary_transfer_execute(batch, (void *)1, deadline,
		&result) == -EPROTO);
	CHECK(calls == 1 && result.completed_sections == 0 &&
	      result.failed_index == 0 && result.error == -EPROTO &&
	      result.partial_submitted == sizeof(data) / 2 &&
	      callback_identity_errors == 0);
	short_success = 0;
	mt6797_ordinary_transfer_free(batch);
	return 0;
}

static int test_output_overlap(void)
{
	u8 config[20], data[32], before[sizeof(data)];
	struct mt6797_ordinary_transfer_request request;
	struct mt6797_ordinary_transfer_batch *batch;

	memset(data, 0xa5, sizeof(data)); memcpy(before, data, sizeof(data));
	make_config(config, sizeof(data), 1);
	request = (struct mt6797_ordinary_transfer_request){
		MT6797_SECTION_ORDINARY, config, 20, 1, data, sizeof(data)};
	batch = mt6797_ordinary_transfer_prepare(&request, 1);
	CHECK(batch != NULL); calls = 0;
	CHECK(mt6797_ordinary_transfer_execute(batch, (void *)1, UINT64_MAX,
		(struct mt6797_ordinary_transfer_result *)data) == -22);
	CHECK(calls == 0 && memcmp(data, before, sizeof(data)) == 0);
	mt6797_ordinary_transfer_free(batch);
	return 0;
}

int main(void)
{
	CHECK(test_happy_and_repeat() == 0);
	CHECK(test_prepare_refusals() == 0);
	CHECK(test_aggregate_boundary() == 0);
	CHECK(test_maximum_inventory_and_adjacent_ranges() == 0);
	CHECK(test_failure_accounting_and_deadline() == 0);
	CHECK(test_extended_deadline_terminal() == 0);
	CHECK(test_output_overlap() == 0);
	CHECK(test_pairwise_refusals() == 0);
	CHECK(test_short_success_is_failure() == 0);
	puts("ordinary-transfer host fixtures: pass");
	return 0;
}
