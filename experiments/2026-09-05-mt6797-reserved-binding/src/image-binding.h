/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef MT6797_IMAGE_BINDING_H
#define MT6797_IMAGE_BINDING_H

#ifdef MT6797_BINDING_HOST_TEST
#include "binding-test-compat.h"
#else
#include <linux/types.h>
#endif
#include "image-plan.h"

struct mt6797_image_owner;
struct mt6797_image_binding;
struct device;

/* Inclusive boot-resource intervals; descriptive, never an access grant. */
struct mt6797_image_reserved_info {
	u64 generation;
	u64 start;
	u64 end;
	u64 wlan_start;
	u64 wlan_end;
	u64 wmt_start;
	u64 wmt_end;
};

enum mt6797_image_client {
	MT6797_IMAGE_WMT,
	MT6797_IMAGE_WLAN,
	MT6797_IMAGE_BT,
	MT6797_IMAGE_GNSS,
	MT6797_IMAGE_CLIENTS,
};

enum mt6797_image_binding_state {
	MT6797_IMAGE_PASSIVE,
	MT6797_IMAGE_INVALID,
	MT6797_IMAGE_FAULT_HELD,
};

/* Descriptive state only: no byte pointer, hardware grant or release witness.
 */
struct mt6797_image_binding_info {
	u64 generation;
	enum mt6797_image_binding_state state;
	int first_error;
	unsigned int sections;
	unsigned int ordinary_sections;
	unsigned int emi_sections;
	size_t image_bytes;
};

/* This is a private software registry, not a CONSYS hardware provider.
 * One eventual provider retains one owner/generation domain. Join all API users
 * before owner destruction or binding release: generations do not cure UAF.
 */
int mt6797_image_owner_alloc(struct mt6797_image_owner **out);
int mt6797_image_owner_free(struct mt6797_image_owner *owner);
/* Bind one boot memory-region descriptor only while the registry is idle.
 * Hold caller device/OF configuration stable during each operation. Retained
 * references keep objects alive, not drivers bound or OF properties immutable.
 * No region callback, exclusive resource claim, mapping or hardware act occurs.
 */
int mt6797_image_owner_bind_reserved(struct mt6797_image_owner *owner,
				     struct device *dev, unsigned int index,
				     u64 *generation);
int mt6797_image_owner_reserved_info(struct mt6797_image_owner *owner,
				     u64 generation,
				     struct mt6797_image_reserved_info *info);
int mt6797_image_owner_unbind_reserved(struct mt6797_image_owner *owner,
				       u64 generation);
/* Passive client registration excludes a whole-image binding. It does not
 * acquire power, firmware exclusion, remap, MPU, IRQ or DMA resources.
 */
int mt6797_image_owner_claim(struct mt6797_image_owner *owner,
			     enum mt6797_image_client client, u64 *generation);
int mt6797_image_owner_unclaim(struct mt6797_image_owner *owner,
			       enum mt6797_image_client client, u64 generation);

/* Caller keeps data stable during this call; the owned copy is parsed only
 * after copying. Outputs must be distinct from data and all live objects.
 * A failure publishes neither a binding nor a generation. No hardware acts.
 */
int mt6797_image_binding_create(struct mt6797_image_owner *owner,
				const u8 *data, size_t bytes,
				struct mt6797_image_binding **out,
				u64 *generation);
int mt6797_image_binding_info(struct mt6797_image_binding *binding,
			      u64 generation,
			      struct mt6797_image_binding_info *info);
int mt6797_image_binding_describe(struct mt6797_image_binding *binding,
				  u64 generation, unsigned int index,
				  struct mt6797_plan_section *section);
/* Prevalidation is descriptive only, including for ordinary-only images. */
int mt6797_image_binding_prevalidate(struct mt6797_image_binding *binding,
				     u64 generation);
/* Always refuses active entry: no real provider is connected. */
int mt6797_image_binding_begin(struct mt6797_image_binding *binding,
			       u64 generation);
int mt6797_image_binding_invalidate(struct mt6797_image_binding *binding,
				    u64 generation);
/* Conservative failure notification; NEVER a way to enter an active state.
 * Retains the first negative error, snapshot and owner claim. No recovery or
 * hardware quiescence witness exists here, so held objects cannot be released.
 */
int mt6797_image_binding_hold_fault(struct mt6797_image_binding *binding,
				    u64 generation, int error);
int mt6797_image_binding_release(struct mt6797_image_binding *binding,
				 u64 generation);

#endif
