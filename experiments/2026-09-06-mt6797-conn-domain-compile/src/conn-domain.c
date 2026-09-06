/* SPDX-License-Identifier: GPL-2.0-only */
#include "conn-domain.h"

/* This descriptor is deliberately not part of any provider or binding table. */
static const struct scp_domain_data mt6797_conn_domain_experiment_data = {
	.name = "conn",
	.sta_mask = BIT(1),
	.ctl_offs = 0x32c,
	.sram_pdn_bits = 0,
	.sram_pdn_ack_bits = 0,
	.bus_prot_mask = 0x60000,
	.clk_id = {CLK_NONE},
	.caps = MTK_SCPD_KEEP_DEFAULT_OFF,
};

const struct mt6797_conn_domain_descriptor mt6797_conn_domain_experiment = {
	.id = 12,
	.data = &mt6797_conn_domain_experiment_data,
};
