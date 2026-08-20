/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __DA9213_LEGACY_PROVIDER_CONTRACT_H
#define __DA9213_LEGACY_PROVIDER_CONTRACT_H

#include <linux/mt6797-a72-provider.h>
#include <linux/types.h>

struct i2c_adapter;
struct i2c_msg;

#define DA9213_LEGACY_PROVIDER_ADDRESS		0x68
#define DA9213_LEGACY_PROVIDER_ACTIONS		11
#define DA9213_LEGACY_PROVIDER_SETTLE_US		1000

enum da9213_legacy_provider_state {
	DA9213_LEGACY_PROVIDER_IDLE,
	DA9213_LEGACY_PROVIDER_ACQUIRING,
	DA9213_LEGACY_PROVIDER_HELD,
	DA9213_LEGACY_PROVIDER_RELEASING,
	DA9213_LEGACY_PROVIDER_RELEASED,
	DA9213_LEGACY_PROVIDER_FAILED_NO_MUTATION,
	DA9213_LEGACY_PROVIDER_FAULT_RETAINED,
};

struct da9213_legacy_provider_snapshot {
	u8 control_a;
	u8 status_b;
	u8 buckb_cont;
	u8 vbuckb_a;
	u8 vbuckb_b;
};

struct da9213_legacy_provider_result {
	enum da9213_legacy_provider_state state;
	unsigned int acquire_attempts;
	unsigned int release_attempts;
	unsigned int operation_transfers;
	unsigned int total_transfers;
	unsigned int write_attempts;
	unsigned int inverse_write_attempts;
	int error;
	struct mt6797_a72_provider_handle held_handle;
	struct da9213_legacy_provider_snapshot prestate;
	struct da9213_legacy_provider_snapshot held_state;
	struct da9213_legacy_provider_snapshot release_prestate;
	struct da9213_legacy_provider_snapshot final_state;
};

struct da9213_legacy_provider_transport_ops {
	int (*transfer)(struct i2c_adapter *adapter,
			struct i2c_msg *messages, int count);
	void (*delay)(unsigned long minimum, unsigned long maximum);
};

const char *da9213_legacy_provider_state_name(
	enum da9213_legacy_provider_state state);
int da9213_legacy_provider_transaction_acquire(
	struct i2c_adapter *adapter, u16 address,
	const struct da9213_legacy_provider_transport_ops *ops,
	const struct mt6797_a72_provider_request *request,
	struct da9213_legacy_provider_result *result,
	struct mt6797_a72_provider_response *response);
int da9213_legacy_provider_transaction_release(
	struct i2c_adapter *adapter, u16 address,
	const struct da9213_legacy_provider_transport_ops *ops,
	const struct mt6797_a72_provider_handle *handle,
	struct da9213_legacy_provider_result *result,
	struct mt6797_a72_provider_response *response);

#endif /* __DA9213_LEGACY_PROVIDER_CONTRACT_H */
