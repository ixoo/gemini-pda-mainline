// SPDX-License-Identifier: GPL-2.0-only
#include "emi-service-gate.h"

static int mt6797_emi_selector_valid(enum mt6797_emi_selector selector)
{
	return selector == MT6797_EMI_SELECTOR_BIT13_CLEAR ||
		selector == MT6797_EMI_SELECTOR_BIT13_SET;
}

static int mt6797_emi_interval_outside(u64 start, u64 end,
				       u64 outer_start, u64 outer_end)
{
	return start > end || start < outer_start || end > outer_end;
}

int mt6797_emi_service_gate_init(struct mt6797_emi_service_gate *gate,
				 const struct mt6797_resource_layout *layout,
				 const struct mt6797_emi_service_backend *backend)
{
	unsigned int expected_common;
	int error;

	if ((const void *)gate == (const void *)layout ||
	    (const void *)gate == (const void *)backend ||
	    (const void *)layout == (const void *)backend)
		return -EINVAL;
	if (!gate)
		return -EINVAL;
	*gate = (struct mt6797_emi_service_gate){0};
	if (!layout || !backend)
		return -EINVAL;
	if (!backend->call)
		return -EOPNOTSUPP;

	if (layout->generation == 0 || layout->start > layout->end ||
	    layout->start > 0xffffffffffffffffULL - 0xfffffULL ||
	    layout->end - layout->start < 0xfffffULL)
		return -ERANGE;
	if (layout->wlan_start != layout->start ||
	    layout->wlan_end != layout->start + 0x7ffffULL ||
	    layout->wmt_start != layout->start + 0x80000ULL ||
	    layout->wmt_end != layout->start + 0xfffffULL ||
	    mt6797_emi_interval_outside(layout->wlan_start, layout->wlan_end,
					layout->start, layout->end) ||
	    mt6797_emi_interval_outside(layout->wmt_start, layout->wmt_end,
					layout->start, layout->end) ||
	    mt6797_emi_interval_outside(layout->region18.start,
					layout->region18.end,
					layout->start, layout->end) ||
	    mt6797_emi_interval_outside(layout->region19.start,
					layout->region19.end,
					layout->start, layout->end))
		return -ERANGE;
	if (!mt6797_emi_selector_valid(layout->region18.selector) ||
	    !mt6797_emi_selector_valid(layout->region19.selector) ||
	    layout->region18.region != 18 || layout->region19.region != 19 ||
	    layout->region18.selector != layout->region19.selector ||
	    layout->region18.start != layout->wlan_start ||
	    layout->region18.end != layout->wlan_end ||
	    layout->region19.start != layout->wmt_start ||
	    layout->region19.end != layout->wmt_end)
		return -EINVAL;
	if (layout->region18.selector == MT6797_EMI_SELECTOR_BIT13_CLEAR &&
	    layout->start < 0x40000000ULL)
		return -ERANGE;
	error = mt6797_remap_encode_common(layout->start, 1, &expected_common);
	if (error)
		return error;
	if (layout->common_field != expected_common)
		return -EINVAL;

	gate->layout = *layout;
	gate->backend = *backend;
	gate->expected_generation = layout->generation;
	gate->state = MT6797_EMI_SERVICE_GATE_READY;
	return 0;
}

int mt6797_emi_service_gate_apply(struct mt6797_emi_service_gate *gate,
				  u64 expected_generation,
				  unsigned int permissions,
				  struct mt6797_emi_service_result *result)
{
	struct mt6797_emi_arguments arguments;
	struct mt6797_emi_result decoded;
	u64 raw;
	int error;

	if (!result || (const void *)gate == (const void *)result)
		return -EINVAL;
	*result = (struct mt6797_emi_service_result){0};
	if (!gate)
		return -EINVAL;
	if (gate->state == MT6797_EMI_SERVICE_GATE_ATTEMPTED ||
	    gate->state == MT6797_EMI_SERVICE_GATE_COMPLETED ||
	    gate->state == MT6797_EMI_SERVICE_GATE_FAULT_HELD)
		return -EALREADY;
	if (gate->state != MT6797_EMI_SERVICE_GATE_READY)
		return -EINVAL;
	if (expected_generation == 0)
		return -EINVAL;
	if (expected_generation != gate->expected_generation)
		return -ESTALE;

	error = mt6797_emi_prepare(&gate->layout.region18,
				   gate->layout.wlan_start, gate->layout.wlan_end,
				   permissions, &arguments);
	if (error)
		return error;
	gate->state = MT6797_EMI_SERVICE_GATE_ATTEMPTED;
	raw = gate->backend.call(gate->backend.context, arguments.function_id,
				 arguments.start, arguments.end,
				 arguments.region_permission);
	decoded = mt6797_emi_decode_result(raw);
	result->generation = gate->expected_generation;
	result->arguments = arguments;
	result->raw = decoded.raw;
	result->status = decoded.status;
	gate->state = decoded.status == 0 ?
		MT6797_EMI_SERVICE_GATE_COMPLETED :
		MT6797_EMI_SERVICE_GATE_FAULT_HELD;
	return decoded.status;
}
