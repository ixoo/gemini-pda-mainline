/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef MT6797_COMPILE_KERNEL_ADAPTER_H
#define MT6797_COMPILE_KERNEL_ADAPTER_H

#include <linux/io.h>
#include "hif_ordinary_section.h"

/* Compile-only boundary. The absent caller must own power, mapping lifetime,
 * exclusive driver ownership and setup/data serialization. No resources are
 * acquired here. This type and all referenced buffers must remain distinct.
 */
struct mt6797_compile_mapping {
	void __iomem *base;
	size_t bytes;
};

int mt6797_compile_bind(struct mt6797_compile_mapping *mapping,
			struct mt6797_hif_pio_io *io);
int mt6797_compile_pio(const struct mt6797_hif_pio_io *io, unsigned int port,
		       enum mt6797_hif_direction direction, unsigned char *buffer,
		       size_t bytes, size_t capacity,
		       struct mt6797_hif_pio_result *result);
int mt6797_compile_section_begin(struct mt6797_ordinary_section *section,
				 struct mt6797_init_transaction *transaction,
				 const struct mt6797_hif_pio_io *io, enum mt6797_section_kind kind,
				 const unsigned char *config, size_t config_bytes,
				 unsigned int sequence, const unsigned char *data, size_t length);
int mt6797_compile_section_ack(struct mt6797_ordinary_section *section,
			       const struct mt6797_hif_pio_io *io, unsigned int length,
			       unsigned int *status);
int mt6797_compile_section_next(struct mt6797_ordinary_section *section,
				const struct mt6797_hif_pio_io *io, unsigned char *scratch,
				size_t capacity);
int mt6797_compile_start_begin(struct mt6797_init_transaction *transaction,
			       const unsigned char *command, size_t bytes, unsigned int sequence);
int mt6797_compile_start_submitted(struct mt6797_init_transaction *transaction,
				   int pio_error);
int mt6797_compile_start_ready(struct mt6797_init_transaction *transaction,
			       unsigned int wcir);

#endif
