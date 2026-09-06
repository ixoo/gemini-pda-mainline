/* SPDX-License-Identifier: MIT */
#include <stdio.h>
#include "conn-domain.h"

#define CHECK(_condition) do { \
	if (!(_condition)) { \
		fprintf(stderr, "FAIL:%s:%d: %s\n", __FILE__, __LINE__, \
			#_condition); \
		return 1; \
	} \
} while (0)

int main(void)
{
	const struct scp_domain_data *data =
		mt6797_conn_domain_experiment.data;

	CHECK(mt6797_conn_domain_experiment.id == 12);
	CHECK(data != NULL && data->name != NULL);
	CHECK(data->name[0] == 'c' && data->name[1] == 'o' &&
	      data->name[2] == 'n' && data->name[3] == 'n' &&
	      data->name[4] == '\0');
	CHECK(data->sta_mask == BIT(1));
	CHECK(data->ctl_offs == 0x32c);
	CHECK(data->sram_pdn_bits == 0 && data->sram_pdn_ack_bits == 0);
	CHECK(data->bus_prot_mask == 0x60000);
	for (unsigned int i = 0; i < MAX_CLKS; i++)
		CHECK(data->clk_id[i] == CLK_NONE);
	CHECK(data->caps == MTK_SCPD_KEEP_DEFAULT_OFF);
	puts("conn_domain_typed_descriptor=pass");
	return 0;
}
