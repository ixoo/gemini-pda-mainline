/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef MT6797_CONN_DOMAIN_H
#define MT6797_CONN_DOMAIN_H

/* The provider supplies BIT() and the private type in the kernel build. */
#ifndef BIT
#define BIT(_n) (1U << (_n))
#endif

#define MTK_SCPD_KEEP_DEFAULT_OFF BIT(2)

struct scp_domain_data;

struct mt6797_conn_domain_descriptor {
	unsigned int id;
	const struct scp_domain_data *data;
};

extern const struct mt6797_conn_domain_descriptor
	mt6797_conn_domain_experiment;

#endif
