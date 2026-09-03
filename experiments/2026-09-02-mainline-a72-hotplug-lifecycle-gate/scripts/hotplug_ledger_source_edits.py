#!/usr/bin/env python3
"""Add the disconnected record-4 A72 hotplug ledger and its KUnit tests."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"{path}: expected one anchor: {old.splitlines()[0]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


PUBLIC_HEADER = dedent(r"""\
    /* SPDX-License-Identifier: GPL-2.0-only */
    #ifndef _LINUX_GEMINI_A72_HOTPLUG_LEDGER_H
    #define _LINUX_GEMINI_A72_HOTPLUG_LEDGER_H

    #include <linux/errno.h>
    #include <linux/types.h>

    #define GEMINI_A72_HOTPLUG_LEDGER_ONLINE_MASK GENMASK(9, 0)
    #define GEMINI_A72_HOTPLUG_LEDGER_MEMBERS_MASK GENMASK(1, 0)

    enum gemini_a72_hotplug_ledger_stage {
            GEMINI_A72_HOTPLUG_BINDING_PARENT = 1,
            GEMINI_A72_HOTPLUG_DOWN_PREPARED,
            GEMINI_A72_HOTPLUG_WATCHDOG_VALID,
            GEMINI_A72_HOTPLUG_BASELINE_VALID,
            GEMINI_A72_HOTPLUG_DOWN_VALID,
            GEMINI_A72_HOTPLUG_TARGET_DISABLE_VALID,
            GEMINI_A72_HOTPLUG_CPU_OFF_COMMITTED,
            GEMINI_A72_HOTPLUG_CPU_OFF_RETURNED,
            GEMINI_A72_HOTPLUG_AFFINITY_OFF,
            GEMINI_A72_HOTPLUG_POST_STATE_VALID,
            GEMINI_A72_HOTPLUG_CPU8_RESPONSIVE,
            GEMINI_A72_HOTPLUG_OFF_PROOF_ACCEPTED,
            GEMINI_A72_HOTPLUG_DOWN_COMPLETE,
            GEMINI_A72_HOTPLUG_RESTORE_PREPARED,
            GEMINI_A72_HOTPLUG_CPU_ON_COMMITTED,
            GEMINI_A72_HOTPLUG_SECONDARY_COMPLETE,
            GEMINI_A72_HOTPLUG_RESTORE_COMPLETE,
    };

    enum gemini_a72_hotplug_ledger_terminal {
            GEMINI_A72_HOTPLUG_REJECTED_PRECOMMIT = 1,
            GEMINI_A72_HOTPLUG_CPU_OFF_RETURN_FAULT,
            GEMINI_A72_HOTPLUG_POSTCOMMIT_DOWN_FAULT,
            GEMINI_A72_HOTPLUG_RESTORE_FAULT,
            GEMINI_A72_HOTPLUG_RESTORED_SUCCESS,
    };

    struct gemini_a72_hotplug_ledger_record {
            u64 session_id;
            u32 parent_generation;
            u64 parent_cookie;
            u64 watchdog_identity;
            u32 down_generation;
            u64 down_cookie;
            u32 restore_generation;
            u64 restore_cookie;
            u32 result_flags;
            u32 cpu_off_calls;
            u32 affinity_calls;
            u32 cpu8_ipi_calls;
            u32 cpu_on_calls;
            u32 online_mask;
            u32 members;
            u32 readback_mismatch;
            u32 generation;
            u32 stage;
            u32 terminal;
            s32 error;
    };

    #ifdef CONFIG_PSTORE_GEMINI_A72_HOTPLUG_LEDGER
    int gemini_a72_hotplug_ledger_begin(u64 session_id);
    int gemini_a72_hotplug_ledger_checkpoint(
            u64 session_id,
            const struct gemini_a72_hotplug_ledger_record *record);
    #else
    static inline int gemini_a72_hotplug_ledger_begin(u64 session_id)
    {
            return -EOPNOTSUPP;
    }

    static inline int gemini_a72_hotplug_ledger_checkpoint(
            u64 session_id,
            const struct gemini_a72_hotplug_ledger_record *record)
    {
            return -EOPNOTSUPP;
    }
    #endif

    #endif /* _LINUX_GEMINI_A72_HOTPLUG_LEDGER_H */
    """)


INTERNAL_HEADER = dedent(r"""\
    /* SPDX-License-Identifier: GPL-2.0-only */
    #ifndef __GEMINI_A72_HOTPLUG_LEDGER_INTERNAL_H
    #define __GEMINI_A72_HOTPLUG_LEDGER_INTERNAL_H

    #include <linux/gemini_a72_hotplug_ledger.h>
    #include <linux/types.h>

    #define GEMINI_A72_HOTPLUG_LEDGER_PSTORE_SIGNATURE 0x43474244U
    #define GEMINI_A72_HOTPLUG_LEDGER_MAGIC 0x4c483947U
    #define GEMINI_A72_HOTPLUG_LEDGER_VERSION_WORD 0x00010001U
    #define GEMINI_A72_HOTPLUG_LEDGER_HEADER_WORDS 3U
    #define GEMINI_A72_HOTPLUG_LEDGER_COPY_WORDS 27U
    #define GEMINI_A72_HOTPLUG_LEDGER_COPIES 2U
    #define GEMINI_A72_HOTPLUG_LEDGER_INTEGRITY_WORD 26U
    #define GEMINI_A72_HOTPLUG_LEDGER_PAYLOAD_BYTES \
            (GEMINI_A72_HOTPLUG_LEDGER_COPY_WORDS * \
             GEMINI_A72_HOTPLUG_LEDGER_COPIES * sizeof(u32))
    #define GEMINI_A72_HOTPLUG_LEDGER_SLOT_SIZE 0x1000U
    #define GEMINI_A72_HOTPLUG_LEDGER_MAX_RECORDS 16U
    #define GEMINI_A72_HOTPLUG_LEDGER_WRITES_PER_RECORD 28U

    struct gemini_a72_hotplug_ledger_ops {
            u32 (*read)(void *context, unsigned int word);
            void (*write)(void *context, unsigned int word, u32 value);
            void (*sync)(void *context);
    };

    struct gemini_a72_hotplug_ledger_owner {
            u64 session_id;
            u32 next_generation;
            u32 newest_copy;
            u32 next_stage;
            u32 records;
            bool active;
            bool sealed;
            bool failed;
            bool have_valid;
            bool header_committed;
            bool needs_signature;
    };

    int gemini_a72_hotplug_ledger_owner_begin(
            struct gemini_a72_hotplug_ledger_owner *owner,
            const struct gemini_a72_hotplug_ledger_ops *ops, void *context,
            u64 session_id);
    int gemini_a72_hotplug_ledger_owner_checkpoint(
            struct gemini_a72_hotplug_ledger_owner *owner,
            const struct gemini_a72_hotplug_ledger_ops *ops, void *context,
            u64 session_id,
            const struct gemini_a72_hotplug_ledger_record *record);
    bool gemini_a72_hotplug_ledger_read_latest(
            const struct gemini_a72_hotplug_ledger_ops *ops, void *context,
            struct gemini_a72_hotplug_ledger_record *record, u32 *copy_index);

    #endif /* __GEMINI_A72_HOTPLUG_LEDGER_INTERNAL_H */
    """)


SOURCE = dedent(r"""\
    // SPDX-License-Identifier: GPL-2.0-only
    /* One-shot retained record-4 ledger for Gemini A72 physical hotplug. */

    #include <linux/crc32.h>
    #include <linux/errno.h>
    #include <linux/export.h>
    #include <linux/gemini_a72_hotplug_ledger.h>
    #include <linux/io.h>
    #include <linux/mutex.h>
    #include <linux/of.h>
    #include <linux/of_address.h>
    #include <linux/string.h>

    #include "gemini_a72_hotplug_ledger_internal.h"

    #define GEMINI_A72_HOTPLUG_LEDGER_RESERVE_BASE 0x44410000ULL
    #define GEMINI_A72_HOTPLUG_LEDGER_BASE 0x44414000ULL
    #define GEMINI_A72_HOTPLUG_LEDGER_RESERVE_SIZE 0x000e0000ULL

    static unsigned int hotplug_copy_word(unsigned int copy, unsigned int word)
    {
            return GEMINI_A72_HOTPLUG_LEDGER_HEADER_WORDS +
                    copy * GEMINI_A72_HOTPLUG_LEDGER_COPY_WORDS + word;
    }

    static u32 hotplug_integrity(const __le32 *wire)
    {
            return crc32_le(~0U, (const u8 *)wire,
                            GEMINI_A72_HOTPLUG_LEDGER_INTEGRITY_WORD *
                            sizeof(*wire)) ^ ~0U;
    }

    static void hotplug_read_wire(const struct gemini_a72_hotplug_ledger_ops *ops,
                                     void *context, unsigned int copy, __le32 *wire)
    {
            unsigned int word;

            for (word = 0; word < GEMINI_A72_HOTPLUG_LEDGER_COPY_WORDS; word++)
                    wire[word] = cpu_to_le32(ops->read(context,
                                                           hotplug_copy_word(copy, word)));
    }

    static bool hotplug_record_shape_valid(
            const struct gemini_a72_hotplug_ledger_record *record)
    {
            if (!record->session_id || !record->generation ||
                record->generation > GEMINI_A72_HOTPLUG_LEDGER_MAX_RECORDS ||
                !record->parent_generation || !record->parent_cookie ||
                !record->stage ||
                record->stage > GEMINI_A72_HOTPLUG_RESTORE_COMPLETE ||
                record->terminal > GEMINI_A72_HOTPLUG_RESTORED_SUCCESS ||
                record->cpu_off_calls > 1 || record->affinity_calls > 1 ||
                record->cpu8_ipi_calls > 1 || record->cpu_on_calls > 1 ||
                record->online_mask & ~GEMINI_A72_HOTPLUG_LEDGER_ONLINE_MASK ||
                record->members & ~GEMINI_A72_HOTPLUG_LEDGER_MEMBERS_MASK)
                    return false;
            if (record->stage >= GEMINI_A72_HOTPLUG_DOWN_PREPARED &&
                (!record->down_generation || !record->down_cookie))
                    return false;
            if (record->stage >= GEMINI_A72_HOTPLUG_WATCHDOG_VALID &&
                !record->watchdog_identity)
                    return false;
            if (record->stage >= GEMINI_A72_HOTPLUG_RESTORE_PREPARED &&
                (!record->restore_generation || !record->restore_cookie))
                    return false;
            if (!record->terminal)
                    return !record->error &&
                           record->stage != GEMINI_A72_HOTPLUG_CPU_OFF_RETURNED &&
                           record->stage != GEMINI_A72_HOTPLUG_RESTORE_COMPLETE;
            if (record->terminal == GEMINI_A72_HOTPLUG_RESTORED_SUCCESS)
                    return record->stage == GEMINI_A72_HOTPLUG_RESTORE_COMPLETE &&
                           !record->error;
            return record->error != 0;
    }

    static bool hotplug_wire_valid(
            const __le32 *wire, struct gemini_a72_hotplug_ledger_record *record)
    {
            u32 online_members;

            if (le32_to_cpu(wire[0]) != GEMINI_A72_HOTPLUG_LEDGER_MAGIC ||
                le32_to_cpu(wire[1]) != GEMINI_A72_HOTPLUG_LEDGER_VERSION_WORD ||
                le32_to_cpu(wire[GEMINI_A72_HOTPLUG_LEDGER_INTEGRITY_WORD]) !=
                        hotplug_integrity(wire))
                    return false;
            record->generation = le32_to_cpu(wire[2]);
            record->stage = le32_to_cpu(wire[3]);
            record->terminal = le32_to_cpu(wire[4]);
            record->error = (s32)le32_to_cpu(wire[5]);
            record->session_id = le32_to_cpu(wire[6]);
            record->session_id |= (u64)le32_to_cpu(wire[7]) << 32;
            record->parent_generation = le32_to_cpu(wire[8]);
            record->parent_cookie = le32_to_cpu(wire[9]);
            record->parent_cookie |= (u64)le32_to_cpu(wire[10]) << 32;
            record->watchdog_identity = le32_to_cpu(wire[11]);
            record->watchdog_identity |= (u64)le32_to_cpu(wire[12]) << 32;
            record->down_generation = le32_to_cpu(wire[13]);
            record->down_cookie = le32_to_cpu(wire[14]);
            record->down_cookie |= (u64)le32_to_cpu(wire[15]) << 32;
            record->restore_generation = le32_to_cpu(wire[16]);
            record->restore_cookie = le32_to_cpu(wire[17]);
            record->restore_cookie |= (u64)le32_to_cpu(wire[18]) << 32;
            record->result_flags = le32_to_cpu(wire[19]);
            record->cpu_off_calls = le32_to_cpu(wire[20]);
            record->affinity_calls = le32_to_cpu(wire[21]);
            record->cpu8_ipi_calls = le32_to_cpu(wire[22]);
            record->cpu_on_calls = le32_to_cpu(wire[23]);
            online_members = le32_to_cpu(wire[24]);
            record->online_mask = online_members & 0xffffU;
            record->members = online_members >> 16;
            record->readback_mismatch = le32_to_cpu(wire[25]);
            return hotplug_record_shape_valid(record);
    }

    bool gemini_a72_hotplug_ledger_read_latest(
            const struct gemini_a72_hotplug_ledger_ops *ops, void *context,
            struct gemini_a72_hotplug_ledger_record *record, u32 *copy_index)
    {
            struct gemini_a72_hotplug_ledger_record candidate;
            __le32 wire[GEMINI_A72_HOTPLUG_LEDGER_COPY_WORDS];
            bool found = false;
            unsigned int copy;

            if (!ops || !ops->read || !record || !copy_index)
                    return false;
            for (copy = 0; copy < GEMINI_A72_HOTPLUG_LEDGER_COPIES; copy++) {
                    hotplug_read_wire(ops, context, copy, wire);
                    if (!hotplug_wire_valid(wire, &candidate))
                            continue;
                    if (found && candidate.generation == record->generation)
                            return false;
                    if (!found || candidate.generation > record->generation) {
                            *record = candidate;
                            *copy_index = copy;
                            found = true;
                    }
            }
            return found;
    }

    static bool hotplug_ops_valid(const struct gemini_a72_hotplug_ledger_ops *ops)
    {
            return ops && ops->read && ops->write && ops->sync;
    }

    int gemini_a72_hotplug_ledger_owner_begin(
            struct gemini_a72_hotplug_ledger_owner *owner,
            const struct gemini_a72_hotplug_ledger_ops *ops, void *context,
            u64 session_id)
    {
            u32 signature;
            u32 size;
            u32 start;
            bool empty;
            bool raw;

            if (!owner || !hotplug_ops_valid(ops) || !session_id)
                    return -EINVAL;
            if (owner->active || owner->sealed)
                    return -EALREADY;
            signature = ops->read(context, 0);
            start = ops->read(context, 1);
            size = ops->read(context, 2);
            raw = signature == ~0U && start == ~0U && size == ~0U;
            empty = signature == GEMINI_A72_HOTPLUG_LEDGER_PSTORE_SIGNATURE &&
                    !start && !size;
            if (!raw && !empty)
                    return signature == GEMINI_A72_HOTPLUG_LEDGER_PSTORE_SIGNATURE &&
                           start == GEMINI_A72_HOTPLUG_LEDGER_PAYLOAD_BYTES &&
                           size == start ? -EALREADY : -EBADMSG;
            owner->session_id = session_id;
            owner->next_generation = 1;
            owner->next_stage = GEMINI_A72_HOTPLUG_BINDING_PARENT;
            owner->active = true;
            owner->needs_signature = raw;
            return 0;
    }

    static bool hotplug_sequence_valid(
            const struct gemini_a72_hotplug_ledger_owner *owner,
            const struct gemini_a72_hotplug_ledger_record *record)
    {
            if (record->terminal == GEMINI_A72_HOTPLUG_CPU_OFF_RETURN_FAULT)
                    return owner->next_stage == GEMINI_A72_HOTPLUG_AFFINITY_OFF &&
                           record->stage == GEMINI_A72_HOTPLUG_CPU_OFF_RETURNED;
            if (record->stage != owner->next_stage)
                    return false;
            if (record->terminal == GEMINI_A72_HOTPLUG_REJECTED_PRECOMMIT)
                    return record->stage <= GEMINI_A72_HOTPLUG_TARGET_DISABLE_VALID;
            if (record->terminal == GEMINI_A72_HOTPLUG_POSTCOMMIT_DOWN_FAULT)
                    return record->stage >= GEMINI_A72_HOTPLUG_AFFINITY_OFF &&
                           record->stage <= GEMINI_A72_HOTPLUG_DOWN_COMPLETE;
            if (record->terminal == GEMINI_A72_HOTPLUG_RESTORE_FAULT)
                    return record->stage >= GEMINI_A72_HOTPLUG_RESTORE_PREPARED;
            if (record->terminal == GEMINI_A72_HOTPLUG_RESTORED_SUCCESS)
                    return record->stage == GEMINI_A72_HOTPLUG_RESTORE_COMPLETE;
            return !record->terminal;
    }

    static int hotplug_fault(struct gemini_a72_hotplug_ledger_owner *owner)
    {
            owner->active = false;
            owner->failed = true;
            owner->sealed = true;
            return -EIO;
    }

    int gemini_a72_hotplug_ledger_owner_checkpoint(
            struct gemini_a72_hotplug_ledger_owner *owner,
            const struct gemini_a72_hotplug_ledger_ops *ops, void *context,
            u64 session_id,
            const struct gemini_a72_hotplug_ledger_record *record)
    {
            struct gemini_a72_hotplug_ledger_record committed;
            __le32 readback[GEMINI_A72_HOTPLUG_LEDGER_COPY_WORDS];
            __le32 wire[GEMINI_A72_HOTPLUG_LEDGER_COPY_WORDS] = {};
            unsigned int target;
            unsigned int word;

            if (!owner || !hotplug_ops_valid(ops) || !record)
                    return -EINVAL;
            if (!owner->active)
                    return owner->sealed ? -EALREADY : -EPERM;
            if (session_id != owner->session_id || record->session_id != session_id)
                    return -EACCES;
            committed = *record;
            committed.generation = owner->next_generation;
            if (!hotplug_record_shape_valid(&committed) ||
                !hotplug_sequence_valid(owner, &committed) ||
                owner->records >= GEMINI_A72_HOTPLUG_LEDGER_MAX_RECORDS)
                    return -EINVAL;

            wire[0] = cpu_to_le32(GEMINI_A72_HOTPLUG_LEDGER_MAGIC);
            wire[1] = cpu_to_le32(GEMINI_A72_HOTPLUG_LEDGER_VERSION_WORD);
            wire[2] = cpu_to_le32(committed.generation);
            wire[3] = cpu_to_le32(committed.stage);
            wire[4] = cpu_to_le32(committed.terminal);
            wire[5] = cpu_to_le32((u32)committed.error);
            wire[6] = cpu_to_le32(lower_32_bits(committed.session_id));
            wire[7] = cpu_to_le32(upper_32_bits(committed.session_id));
            wire[8] = cpu_to_le32(committed.parent_generation);
            wire[9] = cpu_to_le32(lower_32_bits(committed.parent_cookie));
            wire[10] = cpu_to_le32(upper_32_bits(committed.parent_cookie));
            wire[11] = cpu_to_le32(lower_32_bits(committed.watchdog_identity));
            wire[12] = cpu_to_le32(upper_32_bits(committed.watchdog_identity));
            wire[13] = cpu_to_le32(committed.down_generation);
            wire[14] = cpu_to_le32(lower_32_bits(committed.down_cookie));
            wire[15] = cpu_to_le32(upper_32_bits(committed.down_cookie));
            wire[16] = cpu_to_le32(committed.restore_generation);
            wire[17] = cpu_to_le32(lower_32_bits(committed.restore_cookie));
            wire[18] = cpu_to_le32(upper_32_bits(committed.restore_cookie));
            wire[19] = cpu_to_le32(committed.result_flags);
            wire[20] = cpu_to_le32(committed.cpu_off_calls);
            wire[21] = cpu_to_le32(committed.affinity_calls);
            wire[22] = cpu_to_le32(committed.cpu8_ipi_calls);
            wire[23] = cpu_to_le32(committed.cpu_on_calls);
            wire[24] = cpu_to_le32(committed.online_mask |
                                          committed.members << 16);
            wire[25] = cpu_to_le32(committed.readback_mismatch);
            wire[26] = cpu_to_le32(hotplug_integrity(wire));
            target = owner->have_valid ? owner->newest_copy ^ 1U : 0;

            ops->write(context, hotplug_copy_word(target,
                            GEMINI_A72_HOTPLUG_LEDGER_INTEGRITY_WORD), 0);
            ops->sync(context);
            for (word = 0; word < GEMINI_A72_HOTPLUG_LEDGER_INTEGRITY_WORD;
                 word++)
                    ops->write(context, hotplug_copy_word(target, word),
                               le32_to_cpu(wire[word]));
            ops->sync(context);
            ops->write(context, hotplug_copy_word(target,
                            GEMINI_A72_HOTPLUG_LEDGER_INTEGRITY_WORD),
                       le32_to_cpu(wire[GEMINI_A72_HOTPLUG_LEDGER_INTEGRITY_WORD]));
            ops->sync(context);
            hotplug_read_wire(ops, context, target, readback);
            if (memcmp(wire, readback, sizeof(wire)))
                    return hotplug_fault(owner);

            if (!owner->header_committed) {
                    ops->write(context, 1, GEMINI_A72_HOTPLUG_LEDGER_PAYLOAD_BYTES);
                    ops->sync(context);
                    ops->write(context, 2, GEMINI_A72_HOTPLUG_LEDGER_PAYLOAD_BYTES);
                    ops->sync(context);
                    if (owner->needs_signature) {
                            ops->write(context, 0,
                                       GEMINI_A72_HOTPLUG_LEDGER_PSTORE_SIGNATURE);
                            ops->sync(context);
                    }
                    if (ops->read(context, 0) !=
                                GEMINI_A72_HOTPLUG_LEDGER_PSTORE_SIGNATURE ||
                        ops->read(context, 1) !=
                                GEMINI_A72_HOTPLUG_LEDGER_PAYLOAD_BYTES ||
                        ops->read(context, 2) !=
                                GEMINI_A72_HOTPLUG_LEDGER_PAYLOAD_BYTES)
                            return hotplug_fault(owner);
                    owner->header_committed = true;
            }

            owner->newest_copy = target;
            owner->have_valid = true;
            owner->records++;
            owner->next_generation++;
            owner->next_stage = committed.stage + 1;
            if (committed.stage == GEMINI_A72_HOTPLUG_CPU_OFF_COMMITTED)
                    owner->next_stage = GEMINI_A72_HOTPLUG_AFFINITY_OFF;
            if (committed.terminal) {
                    owner->active = false;
                    owner->sealed = true;
            }
            return 0;
    }

    static bool gemini_a72_hotplug_ledger_exact_dt(void)
    {
            struct device_node *node;
            struct resource resource;
            const char *model;
            u32 value;
            bool exact = false;

            if (!of_machine_is_compatible("planet,gemini-pda") ||
                of_property_read_string(of_root, "model", &model) ||
                strcmp(model, "MT6797X"))
                    return false;
            node = of_find_node_by_path("/reserved-memory/ramoops@44410000");
            if (!node)
                    return false;
            if (!of_device_is_compatible(node, "ramoops") ||
                of_address_to_resource(node, 0, &resource) ||
                resource.start != GEMINI_A72_HOTPLUG_LEDGER_RESERVE_BASE ||
                resource_size(&resource) != GEMINI_A72_HOTPLUG_LEDGER_RESERVE_SIZE ||
                !of_property_read_bool(node, "no-map"))
                    goto out;
            if (of_property_read_u32(node, "record-size", &value) ||
                value != GEMINI_A72_HOTPLUG_LEDGER_SLOT_SIZE)
                    goto out;
            if (of_property_read_u32(node, "console-size", &value) ||
                value != 0x10000 ||
                of_property_read_u32(node, "ftrace-size", &value) ||
                value != 0x1000 ||
                of_property_read_u32(node, "pmsg-size", &value) ||
                value != 0x20000 ||
                of_property_read_u32(node, "mem-type", &value) || value)
                    goto out;
            exact = true;
    out:
            of_node_put(node);
            return exact;
    }

    static u32 hotplug_mmio_read(void *context, unsigned int word)
    {
            void __iomem *slot = context;

            return readl((u8 __iomem *)slot + word * sizeof(u32));
    }

    static void hotplug_mmio_write(void *context, unsigned int word, u32 value)
    {
            void __iomem *slot = context;

            writel(value, (u8 __iomem *)slot + word * sizeof(u32));
    }

    static void hotplug_mmio_sync(void *context)
    {
            (void)context;
            wmb();
    }

    static const struct gemini_a72_hotplug_ledger_ops hotplug_mmio_ops = {
            .read = hotplug_mmio_read,
            .write = hotplug_mmio_write,
            .sync = hotplug_mmio_sync,
    };

    static DEFINE_MUTEX(gemini_a72_hotplug_ledger_lock);
    static struct gemini_a72_hotplug_ledger_owner hotplug_owner;
    static void __iomem *hotplug_slot;
    static bool hotplug_attempted;

    int gemini_a72_hotplug_ledger_begin(u64 session_id)
    {
            int ret;

            mutex_lock(&gemini_a72_hotplug_ledger_lock);
            if (hotplug_attempted) {
                    ret = -EALREADY;
                    goto out_unlock;
            }
            hotplug_attempted = true;
            if (!gemini_a72_hotplug_ledger_exact_dt()) {
                    ret = -ENODEV;
                    goto out_unlock;
            }
            hotplug_slot = ioremap_wc(GEMINI_A72_HOTPLUG_LEDGER_BASE,
                                     GEMINI_A72_HOTPLUG_LEDGER_SLOT_SIZE);
            if (!hotplug_slot) {
                    ret = -ENOMEM;
                    goto out_unlock;
            }
            ret = gemini_a72_hotplug_ledger_owner_begin(
                    &hotplug_owner, &hotplug_mmio_ops, hotplug_slot, session_id);
            if (ret) {
                    iounmap(hotplug_slot);
                    hotplug_slot = NULL;
            }
    out_unlock:
            mutex_unlock(&gemini_a72_hotplug_ledger_lock);
            return ret;
    }
    EXPORT_SYMBOL_GPL(gemini_a72_hotplug_ledger_begin);

    int gemini_a72_hotplug_ledger_checkpoint(
            u64 session_id,
            const struct gemini_a72_hotplug_ledger_record *record)
    {
            int ret;

            mutex_lock(&gemini_a72_hotplug_ledger_lock);
            if (!hotplug_slot) {
                    ret = -EPERM;
                    goto out_unlock;
            }
            ret = gemini_a72_hotplug_ledger_owner_checkpoint(
                    &hotplug_owner, &hotplug_mmio_ops, hotplug_slot,
                    session_id, record);
            if (ret || (record && record->terminal)) {
                    iounmap(hotplug_slot);
                    hotplug_slot = NULL;
            }
    out_unlock:
            mutex_unlock(&gemini_a72_hotplug_ledger_lock);
            return ret;
    }
    EXPORT_SYMBOL_GPL(gemini_a72_hotplug_ledger_checkpoint);
    """)


TEST_SOURCE = dedent(r"""\
    // SPDX-License-Identifier: GPL-2.0-only
    /* In-memory KUnit tests for the Gemini A72 record-4 hotplug ledger. */

    #include <kunit/test.h>
    #include <linux/errno.h>
    #include <linux/gemini_a72_hotplug_ledger.h>
    #include <linux/module.h>
    #include <linux/string.h>

    #include "gemini_a72_hotplug_ledger_internal.h"

    #define HOTPLUG_TEST_WORDS \
            (GEMINI_A72_HOTPLUG_LEDGER_HEADER_WORDS + \
             GEMINI_A72_HOTPLUG_LEDGER_COPIES * \
             GEMINI_A72_HOTPLUG_LEDGER_COPY_WORDS)

    struct hotplug_test_state {
            u32 words[HOTPLUG_TEST_WORDS];
            u32 writes;
            u32 syncs;
            int corrupt_word;
    };

    static u32 hotplug_test_read(void *context, unsigned int word)
    {
            struct hotplug_test_state *state = context;

            if (word >= ARRAY_SIZE(state->words))
                    return 0;
            if (state->corrupt_word == word)
                    return state->words[word] ^ 1U;
            return state->words[word];
    }

    static void hotplug_test_write(void *context, unsigned int word, u32 value)
    {
            struct hotplug_test_state *state = context;

            if (word < ARRAY_SIZE(state->words))
                    state->words[word] = value;
            state->writes++;
    }

    static void hotplug_test_sync(void *context)
    {
            struct hotplug_test_state *state = context;

            state->syncs++;
    }

    static const struct gemini_a72_hotplug_ledger_ops hotplug_test_ops = {
            .read = hotplug_test_read,
            .write = hotplug_test_write,
            .sync = hotplug_test_sync,
    };

    static void hotplug_test_raw(struct hotplug_test_state *state)
    {
            memset(state, 0, sizeof(*state));
            memset(state->words, 0xff, sizeof(state->words));
            state->corrupt_word = -1;
    }

    static void hotplug_test_empty(struct hotplug_test_state *state)
    {
            memset(state, 0, sizeof(*state));
            state->words[0] = GEMINI_A72_HOTPLUG_LEDGER_PSTORE_SIGNATURE;
            state->corrupt_word = -1;
    }

    static void hotplug_test_fill(struct gemini_a72_hotplug_ledger_record *record,
                                  u32 stage, u32 terminal, s32 error)
    {
            *record = (struct gemini_a72_hotplug_ledger_record) {
                    .session_id = 0x1234567887654321ULL,
                    .parent_generation = 7,
                    .parent_cookie = 0x1111222233334444ULL,
                    .stage = stage,
                    .terminal = terminal,
                    .error = error,
                    .online_mask = GENMASK(9, 0),
                    .members = GENMASK(1, 0),
            };
            if (stage >= GEMINI_A72_HOTPLUG_DOWN_PREPARED) {
                    record->down_generation = 8;
                    record->down_cookie = 0x2222333344445555ULL;
            }
            if (stage >= GEMINI_A72_HOTPLUG_WATCHDOG_VALID)
                    record->watchdog_identity = 0x3333444455556666ULL;
            if (stage >= GEMINI_A72_HOTPLUG_CPU_OFF_RETURNED)
                    record->cpu_off_calls = 1;
            if (stage >= GEMINI_A72_HOTPLUG_AFFINITY_OFF)
                    record->affinity_calls = 1;
            if (stage >= GEMINI_A72_HOTPLUG_CPU8_RESPONSIVE)
                    record->cpu8_ipi_calls = 1;
            if (stage >= GEMINI_A72_HOTPLUG_RESTORE_PREPARED) {
                    record->restore_generation = 9;
                    record->restore_cookie = 0x4444555566667777ULL;
            }
            if (stage >= GEMINI_A72_HOTPLUG_SECONDARY_COMPLETE)
                    record->cpu_on_calls = 1;
            if (stage >= GEMINI_A72_HOTPLUG_AFFINITY_OFF &&
                stage < GEMINI_A72_HOTPLUG_SECONDARY_COMPLETE)
                    record->online_mask = GENMASK(8, 0);
            if (stage >= GEMINI_A72_HOTPLUG_DOWN_COMPLETE &&
                stage < GEMINI_A72_HOTPLUG_RESTORE_COMPLETE)
                    record->members = BIT(0);
    }

    static void hotplug_layout_test(struct kunit *test)
    {
            KUNIT_EXPECT_EQ(test, GEMINI_A72_HOTPLUG_LEDGER_COPY_WORDS, 27U);
            KUNIT_EXPECT_EQ(test, GEMINI_A72_HOTPLUG_LEDGER_INTEGRITY_WORD, 26U);
            KUNIT_EXPECT_EQ(test, GEMINI_A72_HOTPLUG_LEDGER_WRITES_PER_RECORD, 28U);
            KUNIT_EXPECT_EQ(test, GEMINI_A72_HOTPLUG_LEDGER_MAX_RECORDS, 16U);
            KUNIT_EXPECT_EQ(test, GEMINI_A72_HOTPLUG_LEDGER_MAGIC, 0x4c483947U);
            KUNIT_EXPECT_EQ(test, GEMINI_A72_HOTPLUG_LEDGER_VERSION_WORD,
                            0x00010001U);
    }

    static void hotplug_success_sequence_test(struct kunit *test)
    {
            static const u32 stages[] = { 1, 2, 3, 4, 5, 6, 7, 9, 10, 11,
                                          12, 13, 14, 15, 16, 17 };
            struct gemini_a72_hotplug_ledger_record latest;
            struct gemini_a72_hotplug_ledger_record record;
            struct gemini_a72_hotplug_ledger_owner owner = {};
            struct hotplug_test_state state;
            u32 copy = 0;
            unsigned int index;

            hotplug_test_raw(&state);
            KUNIT_ASSERT_EQ(test, gemini_a72_hotplug_ledger_owner_begin(
                    &owner, &hotplug_test_ops, &state,
                    0x1234567887654321ULL), 0);
            for (index = 0; index < ARRAY_SIZE(stages); index++) {
                    u32 terminal = stages[index] == 17 ?
                            GEMINI_A72_HOTPLUG_RESTORED_SUCCESS : 0;

                    hotplug_test_fill(&record, stages[index], terminal, 0);
                    KUNIT_ASSERT_EQ(test,
                            gemini_a72_hotplug_ledger_owner_checkpoint(
                                    &owner, &hotplug_test_ops, &state,
                                    0x1234567887654321ULL, &record), 0);
            }
            KUNIT_EXPECT_EQ(test, state.writes, 451U);
            KUNIT_EXPECT_TRUE(test, owner.sealed);
            KUNIT_ASSERT_TRUE(test, gemini_a72_hotplug_ledger_read_latest(
                    &hotplug_test_ops, &state, &latest, &copy));
            KUNIT_EXPECT_EQ(test, latest.generation, 16U);
            KUNIT_EXPECT_EQ(test, latest.stage, 17U);
            KUNIT_EXPECT_EQ(test, latest.terminal,
                            (u32)GEMINI_A72_HOTPLUG_RESTORED_SUCCESS);
            KUNIT_EXPECT_EQ(test, latest.online_mask, GENMASK(9, 0));
            KUNIT_EXPECT_EQ(test, latest.members, GENMASK(1, 0));
    }

    static void hotplug_pstore_empty_test(struct kunit *test)
    {
            struct gemini_a72_hotplug_ledger_record record;
            struct gemini_a72_hotplug_ledger_owner owner = {};
            struct hotplug_test_state state;

            hotplug_test_empty(&state);
            KUNIT_ASSERT_EQ(test, gemini_a72_hotplug_ledger_owner_begin(
                    &owner, &hotplug_test_ops, &state,
                    0x1234567887654321ULL), 0);
            hotplug_test_fill(&record, 1, 0, 0);
            KUNIT_ASSERT_EQ(test, gemini_a72_hotplug_ledger_owner_checkpoint(
                    &owner, &hotplug_test_ops, &state,
                    0x1234567887654321ULL, &record), 0);
            KUNIT_EXPECT_EQ(test, state.writes, 30U);
    }

    static void hotplug_nonempty_refusal_test(struct kunit *test)
    {
            struct gemini_a72_hotplug_ledger_owner owner = {};
            struct hotplug_test_state state;

            hotplug_test_empty(&state);
            state.words[1] = GEMINI_A72_HOTPLUG_LEDGER_PAYLOAD_BYTES;
            state.words[2] = GEMINI_A72_HOTPLUG_LEDGER_PAYLOAD_BYTES;
            KUNIT_EXPECT_EQ(test, gemini_a72_hotplug_ledger_owner_begin(
                    &owner, &hotplug_test_ops, &state, 1), -EALREADY);
            state.words[2] = 1;
            KUNIT_EXPECT_EQ(test, gemini_a72_hotplug_ledger_owner_begin(
                    &owner, &hotplug_test_ops, &state, 1), -EBADMSG);
    }

    static void hotplug_sequence_refusal_test(struct kunit *test)
    {
            struct gemini_a72_hotplug_ledger_record record;
            struct gemini_a72_hotplug_ledger_owner owner = {};
            struct hotplug_test_state state;

            hotplug_test_raw(&state);
            KUNIT_ASSERT_EQ(test, gemini_a72_hotplug_ledger_owner_begin(
                    &owner, &hotplug_test_ops, &state,
                    0x1234567887654321ULL), 0);
            hotplug_test_fill(&record, 2, 0, 0);
            KUNIT_EXPECT_EQ(test, gemini_a72_hotplug_ledger_owner_checkpoint(
                    &owner, &hotplug_test_ops, &state,
                    0x1234567887654321ULL, &record), -EINVAL);
            hotplug_test_fill(&record, 1, 0, 0);
            KUNIT_EXPECT_EQ(test, gemini_a72_hotplug_ledger_owner_checkpoint(
                    &owner, &hotplug_test_ops, &state, 2, &record), -EACCES);
            KUNIT_EXPECT_EQ(test, state.writes, 0U);
    }

    static void hotplug_precommit_terminal_test(struct kunit *test)
    {
            struct gemini_a72_hotplug_ledger_record record;
            struct gemini_a72_hotplug_ledger_owner owner = {};
            struct hotplug_test_state state;

            hotplug_test_raw(&state);
            KUNIT_ASSERT_EQ(test, gemini_a72_hotplug_ledger_owner_begin(
                    &owner, &hotplug_test_ops, &state,
                    0x1234567887654321ULL), 0);
            hotplug_test_fill(&record, 1,
                             GEMINI_A72_HOTPLUG_REJECTED_PRECOMMIT, -EPERM);
            KUNIT_ASSERT_EQ(test, gemini_a72_hotplug_ledger_owner_checkpoint(
                    &owner, &hotplug_test_ops, &state,
                    0x1234567887654321ULL, &record), 0);
            KUNIT_EXPECT_TRUE(test, owner.sealed);
            KUNIT_EXPECT_EQ(test, gemini_a72_hotplug_ledger_owner_checkpoint(
                    &owner, &hotplug_test_ops, &state,
                    0x1234567887654321ULL, &record), -EALREADY);
    }

    static void hotplug_cpu_off_return_terminal_test(struct kunit *test)
    {
            struct gemini_a72_hotplug_ledger_record record;
            struct gemini_a72_hotplug_ledger_owner owner = {};
            struct hotplug_test_state state;
            u32 stage;

            hotplug_test_raw(&state);
            KUNIT_ASSERT_EQ(test, gemini_a72_hotplug_ledger_owner_begin(
                    &owner, &hotplug_test_ops, &state,
                    0x1234567887654321ULL), 0);
            for (stage = 1; stage <= 7; stage++) {
                    hotplug_test_fill(&record, stage, 0, 0);
                    KUNIT_ASSERT_EQ(test,
                            gemini_a72_hotplug_ledger_owner_checkpoint(
                                    &owner, &hotplug_test_ops, &state,
                                    0x1234567887654321ULL, &record), 0);
            }
            hotplug_test_fill(&record, 8,
                             GEMINI_A72_HOTPLUG_CPU_OFF_RETURN_FAULT, -EIO);
            KUNIT_ASSERT_EQ(test, gemini_a72_hotplug_ledger_owner_checkpoint(
                    &owner, &hotplug_test_ops, &state,
                    0x1234567887654321ULL, &record), 0);
            KUNIT_EXPECT_TRUE(test, owner.sealed);
    }

    static void hotplug_readback_fault_test(struct kunit *test)
    {
            struct gemini_a72_hotplug_ledger_record record;
            struct gemini_a72_hotplug_ledger_owner owner = {};
            struct hotplug_test_state state;

            hotplug_test_raw(&state);
            KUNIT_ASSERT_EQ(test, gemini_a72_hotplug_ledger_owner_begin(
                    &owner, &hotplug_test_ops, &state,
                    0x1234567887654321ULL), 0);
            hotplug_test_fill(&record, 1, 0, 0);
            state.corrupt_word = GEMINI_A72_HOTPLUG_LEDGER_HEADER_WORDS + 3;
            KUNIT_EXPECT_EQ(test, gemini_a72_hotplug_ledger_owner_checkpoint(
                    &owner, &hotplug_test_ops, &state,
                    0x1234567887654321ULL, &record), -EIO);
            KUNIT_EXPECT_TRUE(test, owner.failed);
            KUNIT_EXPECT_TRUE(test, owner.sealed);
    }

    static void hotplug_crc_and_ambiguity_test(struct kunit *test)
    {
            struct gemini_a72_hotplug_ledger_record latest;
            struct gemini_a72_hotplug_ledger_record record;
            struct gemini_a72_hotplug_ledger_owner owner = {};
            struct hotplug_test_state state;
            u32 copy = 0;

            hotplug_test_raw(&state);
            KUNIT_ASSERT_EQ(test, gemini_a72_hotplug_ledger_owner_begin(
                    &owner, &hotplug_test_ops, &state,
                    0x1234567887654321ULL), 0);
            hotplug_test_fill(&record, 1, 0, 0);
            KUNIT_ASSERT_EQ(test, gemini_a72_hotplug_ledger_owner_checkpoint(
                    &owner, &hotplug_test_ops, &state,
                    0x1234567887654321ULL, &record), 0);
            hotplug_test_fill(&record, 2, 0, 0);
            KUNIT_ASSERT_EQ(test, gemini_a72_hotplug_ledger_owner_checkpoint(
                    &owner, &hotplug_test_ops, &state,
                    0x1234567887654321ULL, &record), 0);
            KUNIT_ASSERT_TRUE(test, gemini_a72_hotplug_ledger_read_latest(
                    &hotplug_test_ops, &state, &latest, &copy));
            KUNIT_EXPECT_EQ(test, latest.generation, 2U);
            state.words[GEMINI_A72_HOTPLUG_LEDGER_HEADER_WORDS +
                        GEMINI_A72_HOTPLUG_LEDGER_COPY_WORDS + 26] ^= 1U;
            KUNIT_ASSERT_TRUE(test, gemini_a72_hotplug_ledger_read_latest(
                    &hotplug_test_ops, &state, &latest, &copy));
            KUNIT_EXPECT_EQ(test, latest.generation, 1U);
    }

    static void hotplug_shape_refusal_test(struct kunit *test)
    {
            struct gemini_a72_hotplug_ledger_record record;
            struct gemini_a72_hotplug_ledger_owner owner = {};
            struct hotplug_test_state state;

            hotplug_test_raw(&state);
            KUNIT_ASSERT_EQ(test, gemini_a72_hotplug_ledger_owner_begin(
                    &owner, &hotplug_test_ops, &state,
                    0x1234567887654321ULL), 0);
            hotplug_test_fill(&record, 1, 0, 0);
            record.cpu_off_calls = 2;
            KUNIT_EXPECT_EQ(test, gemini_a72_hotplug_ledger_owner_checkpoint(
                    &owner, &hotplug_test_ops, &state,
                    0x1234567887654321ULL, &record), -EINVAL);
            record.cpu_off_calls = 0;
            record.online_mask = BIT(10);
            KUNIT_EXPECT_EQ(test, gemini_a72_hotplug_ledger_owner_checkpoint(
                    &owner, &hotplug_test_ops, &state,
                    0x1234567887654321ULL, &record), -EINVAL);
            KUNIT_EXPECT_EQ(test, state.writes, 0U);
    }

    static struct kunit_case hotplug_ledger_cases[] = {
            KUNIT_CASE(hotplug_layout_test),
            KUNIT_CASE(hotplug_success_sequence_test),
            KUNIT_CASE(hotplug_pstore_empty_test),
            KUNIT_CASE(hotplug_nonempty_refusal_test),
            KUNIT_CASE(hotplug_sequence_refusal_test),
            KUNIT_CASE(hotplug_precommit_terminal_test),
            KUNIT_CASE(hotplug_cpu_off_return_terminal_test),
            KUNIT_CASE(hotplug_readback_fault_test),
            KUNIT_CASE(hotplug_crc_and_ambiguity_test),
            KUNIT_CASE(hotplug_shape_refusal_test),
            { }
    };

    static struct kunit_suite hotplug_ledger_suite = {
            .name = "gemini-a72-hotplug-ledger",
            .test_cases = hotplug_ledger_cases,
    };

    kunit_test_suite(hotplug_ledger_suite);

    MODULE_DESCRIPTION("Gemini A72 record-4 hotplug ledger KUnit tests");
    MODULE_LICENSE("GPL");
    """)


KCONFIG = dedent(r"""\
    config PSTORE_GEMINI_A72_HOTPLUG_LEDGER
            bool "Gemini A72 physical-hotplug record-4 ledger"
            depends on PSTORE_GEMINI_CPU9_PROGRESS_LEDGER=y
            default n
            help
              Add a one-shot 27-word, two-copy CRC ledger in exact ramoops
              dmesg record 4. It accepts only a raw-empty or pstore-empty lane,
              preserves records 0--3, and permits at most 16 commits and 451
              32-bit writes on the successful lifecycle path.

              This option adds no production caller, CPU request, PSCI call,
              watchdog action, snapshot, boot policy, or device trigger.

    config PSTORE_GEMINI_A72_HOTPLUG_LEDGER_KUNIT_TEST
            bool "KUnit tests for the Gemini A72 record-4 hotplug ledger"
            depends on KUNIT=y
            depends on PSTORE_GEMINI_A72_HOTPLUG_LEDGER=y
            default n
            help
              Test exact layout, empty-only ownership, bounded alternating
              writes, ordering, terminal sealing, CRC decode, and refusal paths
              using injected memory operations only.

              No retained RAM, MMIO, CPU request, PSCI, watchdog, reset, reboot,
              storage, network, or device action is performed by the tests.

    """)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    (root / "include/linux").mkdir(parents=True, exist_ok=True)
    (root / "fs/pstore").mkdir(parents=True, exist_ok=True)
    (root / "include/linux/gemini_a72_hotplug_ledger.h").write_text(
        PUBLIC_HEADER, encoding="utf-8"
    )
    (root / "fs/pstore/gemini_a72_hotplug_ledger_internal.h").write_text(
        INTERNAL_HEADER, encoding="utf-8"
    )
    (root / "fs/pstore/gemini_a72_hotplug_ledger.c").write_text(
        SOURCE, encoding="utf-8"
    )
    (root / "fs/pstore/gemini_a72_hotplug_ledger_test.c").write_text(
        TEST_SOURCE, encoding="utf-8"
    )
    replace_once(
        root / "fs/pstore/Kconfig",
        "config PSTORE_GEMINI_CPU9_PROGRESS_LEDGER_KUNIT_TEST\n",
        KCONFIG + "config PSTORE_GEMINI_CPU9_PROGRESS_LEDGER_KUNIT_TEST\n",
    )
    replace_once(
        root / "fs/pstore/Makefile",
        "obj-$(CONFIG_PSTORE_GEMINI_CPU9_PROGRESS_LEDGER_KUNIT_TEST) += gemini_cpu9_progress_ledger_test.o\n",
        "obj-$(CONFIG_PSTORE_GEMINI_CPU9_PROGRESS_LEDGER_KUNIT_TEST) += gemini_cpu9_progress_ledger_test.o\n"
        "obj-$(CONFIG_PSTORE_GEMINI_A72_HOTPLUG_LEDGER) += gemini_a72_hotplug_ledger.o\n"
        "obj-$(CONFIG_PSTORE_GEMINI_A72_HOTPLUG_LEDGER_KUNIT_TEST) += gemini_a72_hotplug_ledger_test.o\n",
    )


if __name__ == "__main__":
    main()
