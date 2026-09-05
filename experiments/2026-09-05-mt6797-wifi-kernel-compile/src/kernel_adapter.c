// SPDX-License-Identifier: GPL-2.0-only
#include <linux/align.h>
#include "kernel_adapter.h"

static bool mt6797_mapping_valid(const struct mt6797_compile_mapping *mapping)
{
	return mapping && mapping->base && mapping->bytes >= 0x1004 &&
		IS_ALIGNED((unsigned long)mapping->base, sizeof(u32));
}

/* Ordered scalar MMIO, with no relaxed/raw accessor or status emulation.
 * A successful return means the accessor returned, not bus/firmware success.
 * readl/writel cannot report a recoverable device/bus fault through this API.
 */
static int mt6797_compile_write(void *context, unsigned int offset,
				unsigned int value)
{
	struct mt6797_compile_mapping *mapping = context;

	if (!mt6797_mapping_valid(mapping) || (offset != 0 && offset != 0x1000))
		return -EINVAL;
	writel(value, (u8 __iomem *)mapping->base + offset);
	return 0;
}

static int mt6797_compile_read(void *context, unsigned int offset,
			       unsigned int *value)
{
	struct mt6797_compile_mapping *mapping = context;

	if (!value || !mt6797_mapping_valid(mapping) || offset != 0x1000)
		return -EINVAL;
	*value = readl((u8 __iomem *)mapping->base + offset);
	return 0;
}

int mt6797_compile_bind(struct mt6797_compile_mapping *mapping,
			struct mt6797_hif_pio_io *io)
{
	if (!io)
		return -EINVAL;
	*io = (struct mt6797_hif_pio_io) { 0 };
	if (!mt6797_mapping_valid(mapping))
		return -EINVAL;
	io->context = mapping;
	io->write = mt6797_compile_write;
	io->read = mt6797_compile_read;
	return 0;
}

/* Non-static typed entry points force kernel compilation of the connected
 * inline protocol code. No initcall, registration, export or runtime caller.
 */
int mt6797_compile_pio(const struct mt6797_hif_pio_io *io, unsigned int port,
		       enum mt6797_hif_direction direction, unsigned char *buffer,
		       size_t bytes, size_t capacity,
		       struct mt6797_hif_pio_result *result)
{
	return mt6797_hif_pio_transfer(io, port, direction, buffer, bytes,
				      capacity, result);
}

int mt6797_compile_section_begin(struct mt6797_ordinary_section *section,
				 struct mt6797_init_transaction *transaction,
				 const struct mt6797_hif_pio_io *io, enum mt6797_section_kind kind,
				 const unsigned char *config, size_t config_bytes,
				 unsigned int sequence, const unsigned char *data, size_t length)
{
	return mt6797_section_begin(section, transaction, io, kind, config,
				    config_bytes, sequence, data, length);
}

int mt6797_compile_section_ack(struct mt6797_ordinary_section *section,
			       const struct mt6797_hif_pio_io *io, unsigned int length,
			       unsigned int *status)
{
	return mt6797_section_ack(section, io, length, status);
}

int mt6797_compile_section_next(struct mt6797_ordinary_section *section,
				const struct mt6797_hif_pio_io *io, unsigned char *scratch,
				size_t capacity)
{
	return mt6797_section_next(section, io, scratch, capacity);
}

int mt6797_compile_start_begin(struct mt6797_init_transaction *transaction,
			       const unsigned char *command, size_t bytes, unsigned int sequence)
{
	return mt6797_start_begin(transaction, command, bytes, sequence);
}

int mt6797_compile_start_submitted(struct mt6797_init_transaction *transaction,
				   int pio_error)
{
	return mt6797_start_submitted(transaction, pio_error);
}

int mt6797_compile_start_ready(struct mt6797_init_transaction *transaction,
			       unsigned int wcir)
{
	return mt6797_start_observe_ready(transaction, wcir);
}
