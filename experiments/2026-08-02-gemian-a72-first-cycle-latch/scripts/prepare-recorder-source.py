#!/usr/bin/env python3
"""Prepare the recorder-only latch change in an already patched source tree."""

import argparse
import re
from pathlib import Path


CORE = Path(
    "drivers/misc/mediatek/base/power/mt6797/mt_a72_transition_observer.c"
)
HEADER = Path("include/linux/mt6797_a72_transition_observer.h")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one exact source fragment, found {count}")
    return text.replace(old, new, 1)


def replace_regex_once(text: str, pattern: str, new: str, label: str) -> str:
    updated, count = re.subn(pattern, new, text, count=1, flags=re.DOTALL)
    if count != 1:
        raise SystemExit(f"{label}: expected one source match, found {count}")
    return updated


def update_core(path: Path) -> None:
    text = path.read_text()
    text = replace_once(
        text,
        """struct mt6797_a72_obs_snapshot {
\tu64 overwritten;
\tu32 count;
\tstruct mt6797_a72_obs_record records[MT6797_A72_OBS_RING_SIZE];
};
""",
        """enum mt6797_a72_obs_state {
\tMT6797_A72_OBS_WAIT_UP,
\tMT6797_A72_OBS_CAPTURE_UP,
\tMT6797_A72_OBS_WAIT_DOWN,
\tMT6797_A72_OBS_CAPTURE_DOWN,
\tMT6797_A72_OBS_FROZEN_COMPLETE,
\tMT6797_A72_OBS_FROZEN_UP_FAILED,
\tMT6797_A72_OBS_FROZEN_DOWN_FAILED,
\tMT6797_A72_OBS_FROZEN_CPU9,
\tMT6797_A72_OBS_FROZEN_PROTOCOL,
\tMT6797_A72_OBS_FROZEN_OVERFLOW,
};

struct mt6797_a72_obs_snapshot {
\tu64 up_transaction;
\tu64 down_transaction;
\tu32 count;
\tu16 state;
\tu8 overflow;
\tu8 reserved;
\tstruct mt6797_a72_obs_record records[MT6797_A72_OBS_RING_SIZE];
};
""",
        "snapshot metadata",
    )
    text = replace_once(
        text,
        """static u64 mt6797_a72_obs_transactions[2];
static u64 mt6797_a72_obs_overwritten;
static u32 mt6797_a72_obs_head;
static u32 mt6797_a72_obs_count;
""",
        """static u64 mt6797_a72_obs_transactions[2];
static u64 mt6797_a72_obs_up_transaction;
static u64 mt6797_a72_obs_down_transaction;
static u32 mt6797_a72_obs_count;
static enum mt6797_a72_obs_state mt6797_a72_obs_state =
\tMT6797_A72_OBS_WAIT_UP;
static bool mt6797_a72_obs_overflow;
""",
        "recorder globals",
    )
    text = replace_regex_once(
        text,
        r"static void mt6797_a72_obs_append\(struct mt6797_a72_obs_record \*record\)\n"
        r"\{.*?\n\}\n\nunsigned int mt6797_a72_obs_active_cpu\(void\)\n"
        r"\{.*?\n\}\n",
        r"""static bool mt6797_a72_obs_is_boundary(const struct mt6797_a72_obs_record *r,
\t\t\t\t\tu16 phase)
{
\treturn r->header.event == MT6797_A72_EVENT_LIFECYCLE &&
\t       r->header.phase == phase;
}

static bool mt6797_a72_obs_is_terminal(enum mt6797_a72_obs_state state)
{
\treturn state >= MT6797_A72_OBS_FROZEN_COMPLETE;
}

static void mt6797_a72_obs_append(struct mt6797_a72_obs_record *record)
{
\tenum mt6797_a72_obs_state next_state;
\tunsigned long flags;
\tbool retain = false;

\trecord->header.timestamp_ns = ktime_get_ns();
\trecord->header.online_mask = mt6797_a72_obs_online_mask();
\trecord->header.actor_cpu = raw_smp_processor_id();

\tspin_lock_irqsave(&mt6797_a72_obs_lock, flags);
\tif (mt6797_a72_obs_is_terminal(mt6797_a72_obs_state))
\t\tgoto out;

\trecord->header.transaction =
\t\tmt6797_a72_obs_transaction_locked(record->header.target_cpu);
\tnext_state = mt6797_a72_obs_state;

\tif (mt6797_a72_obs_state == MT6797_A72_OBS_WAIT_UP) {
\t\tif (record->header.target_cpu != 8 ||
\t\t    !record->header.transaction ||
\t\t    !mt6797_a72_obs_is_boundary(record,
\t\t\tMT6797_A72_PHASE_HPS_CPU_UP_BEGIN))
\t\t\tgoto out;
\t\tmt6797_a72_obs_up_transaction = record->header.transaction;
\t\tnext_state = MT6797_A72_OBS_CAPTURE_UP;
\t\tretain = true;
\t} else if (record->header.target_cpu == 9) {
\t\tnext_state = MT6797_A72_OBS_FROZEN_CPU9;
\t\tretain = true;
\t} else if (record->header.target_cpu != 8) {
\t\tnext_state = MT6797_A72_OBS_FROZEN_PROTOCOL;
\t\tretain = true;
\t} else if (mt6797_a72_obs_state == MT6797_A72_OBS_CAPTURE_UP) {
\t\tretain = true;
\t\tif (record->header.transaction !=
\t\t    mt6797_a72_obs_up_transaction ||
\t\t    mt6797_a72_obs_is_boundary(record,
\t\t\tMT6797_A72_PHASE_HPS_CPU_UP_BEGIN) ||
\t\t    mt6797_a72_obs_is_boundary(record,
\t\t\tMT6797_A72_PHASE_HPS_CPU_DOWN_BEGIN) ||
\t\t    mt6797_a72_obs_is_boundary(record,
\t\t\tMT6797_A72_PHASE_HPS_CPU_DOWN_END)) {
\t\t\tnext_state = MT6797_A72_OBS_FROZEN_PROTOCOL;
\t\t} else if (mt6797_a72_obs_is_boundary(record,
\t\t\t   MT6797_A72_PHASE_HPS_CPU_UP_END)) {
\t\t\tnext_state = record->payload.lifecycle.result ?
\t\t\t\tMT6797_A72_OBS_FROZEN_UP_FAILED :
\t\t\t\tMT6797_A72_OBS_WAIT_DOWN;
\t\t}
\t} else if (mt6797_a72_obs_state == MT6797_A72_OBS_WAIT_DOWN) {
\t\tif (mt6797_a72_obs_is_boundary(record,
\t\t\t    MT6797_A72_PHASE_HPS_CPU_DOWN_BEGIN)) {
\t\t\tretain = true;
\t\t\tif (!record->header.transaction ||
\t\t\t    record->header.transaction ==
\t\t\t\tmt6797_a72_obs_up_transaction) {
\t\t\t\tnext_state = MT6797_A72_OBS_FROZEN_PROTOCOL;
\t\t\t} else {
\t\t\t\tmt6797_a72_obs_down_transaction =
\t\t\t\t\trecord->header.transaction;
\t\t\t\tnext_state = MT6797_A72_OBS_CAPTURE_DOWN;
\t\t\t}
\t\t} else if (mt6797_a72_obs_is_boundary(record,
\t\t\t   MT6797_A72_PHASE_HPS_CPU_UP_BEGIN) ||
\t\t\t   mt6797_a72_obs_is_boundary(record,
\t\t\t   MT6797_A72_PHASE_HPS_CPU_UP_END) ||
\t\t\t   mt6797_a72_obs_is_boundary(record,
\t\t\t   MT6797_A72_PHASE_HPS_CPU_DOWN_END)) {
\t\t\tretain = true;
\t\t\tnext_state = MT6797_A72_OBS_FROZEN_PROTOCOL;
\t\t}
\t} else if (mt6797_a72_obs_state == MT6797_A72_OBS_CAPTURE_DOWN) {
\t\tretain = true;
\t\tif (record->header.transaction !=
\t\t    mt6797_a72_obs_down_transaction ||
\t\t    mt6797_a72_obs_is_boundary(record,
\t\t\tMT6797_A72_PHASE_HPS_CPU_UP_BEGIN) ||
\t\t    mt6797_a72_obs_is_boundary(record,
\t\t\tMT6797_A72_PHASE_HPS_CPU_UP_END) ||
\t\t    mt6797_a72_obs_is_boundary(record,
\t\t\tMT6797_A72_PHASE_HPS_CPU_DOWN_BEGIN)) {
\t\t\tnext_state = MT6797_A72_OBS_FROZEN_PROTOCOL;
\t\t} else if (mt6797_a72_obs_is_boundary(record,
\t\t\t   MT6797_A72_PHASE_HPS_CPU_DOWN_END)) {
\t\t\tnext_state = record->payload.lifecycle.result ?
\t\t\t\tMT6797_A72_OBS_FROZEN_DOWN_FAILED :
\t\t\t\tMT6797_A72_OBS_FROZEN_COMPLETE;
\t\t}
\t}

\tif (!retain)
\t\tgoto out;
\tif (mt6797_a72_obs_count == MT6797_A72_OBS_RING_SIZE) {
\t\tmt6797_a72_obs_overflow = true;
\t\tmt6797_a72_obs_state = MT6797_A72_OBS_FROZEN_OVERFLOW;
\t\tgoto out;
\t}

\trecord->header.sequence = mt6797_a72_obs_next_sequence++;
\tmt6797_a72_obs_ring[mt6797_a72_obs_count++] = *record;
\tmt6797_a72_obs_state = next_state;
out:
\tspin_unlock_irqrestore(&mt6797_a72_obs_lock, flags);
}

bool mt6797_a72_obs_accepts_sampling(unsigned int cpu)
{
\tunsigned long flags;
\tbool accepts;

\tspin_lock_irqsave(&mt6797_a72_obs_lock, flags);
\taccepts = cpu == 8 &&
\t\t(mt6797_a72_obs_state == MT6797_A72_OBS_CAPTURE_UP ||
\t\t mt6797_a72_obs_state == MT6797_A72_OBS_CAPTURE_DOWN);
\tspin_unlock_irqrestore(&mt6797_a72_obs_lock, flags);
\treturn accepts;
}

unsigned int mt6797_a72_obs_active_cpu(void)
{
\tunsigned long flags;
\tunsigned int cpu = ~0U;

\tspin_lock_irqsave(&mt6797_a72_obs_lock, flags);
\tif ((mt6797_a72_obs_state == MT6797_A72_OBS_CAPTURE_UP ||
\t     mt6797_a72_obs_state == MT6797_A72_OBS_CAPTURE_DOWN) &&
\t    mt6797_a72_obs_transactions[0] &&
\t    !mt6797_a72_obs_transactions[1])
\t\tcpu = 8;
\tspin_unlock_irqrestore(&mt6797_a72_obs_lock, flags);

\treturn cpu;
}
""",
        "append and active-state implementation",
    )
    text = replace_once(
        text,
        "static const char *mt6797_a72_obs_event_name(u16 event)\n",
        """static const char *mt6797_a72_obs_state_name(u16 state)
{
\tswitch (state) {
\tcase MT6797_A72_OBS_WAIT_UP: return "wait-up";
\tcase MT6797_A72_OBS_CAPTURE_UP: return "capture-up";
\tcase MT6797_A72_OBS_WAIT_DOWN: return "wait-down";
\tcase MT6797_A72_OBS_CAPTURE_DOWN: return "capture-down";
\tcase MT6797_A72_OBS_FROZEN_COMPLETE: return "frozen-complete";
\tcase MT6797_A72_OBS_FROZEN_UP_FAILED: return "frozen-up-failed";
\tcase MT6797_A72_OBS_FROZEN_DOWN_FAILED: return "frozen-down-failed";
\tcase MT6797_A72_OBS_FROZEN_CPU9: return "frozen-cpu9";
\tcase MT6797_A72_OBS_FROZEN_PROTOCOL: return "frozen-protocol";
\tcase MT6797_A72_OBS_FROZEN_OVERFLOW: return "frozen-overflow";
\tdefault: return "invalid";
\t}
}

static const char *mt6797_a72_obs_event_name(u16 event)
""",
        "state-name insertion",
    )
    text = replace_once(
        text,
        """\tseq_printf(m, "abi=mt6797-a72-transition-observer-v1"
\t\t   " count=%u overwritten=%llu\\n",
\t\t   snapshot->count,
\t\t   (unsigned long long)snapshot->overwritten);
""",
        """\tseq_printf(m, "abi=mt6797-a72-transition-observer-v2"
\t\t   " state=%s count=%u overflow=%u up_tx=%llu"
\t\t   " down_tx=%llu\\n",
\t\t   mt6797_a72_obs_state_name(snapshot->state),
\t\t   snapshot->count, snapshot->overflow,
\t\t   (unsigned long long)snapshot->up_transaction,
\t\t   (unsigned long long)snapshot->down_transaction);
""",
        "proc ABI",
    )
    text = replace_once(
        text,
        "\tunsigned int first;\n\tunsigned int i;\n",
        "\tunsigned int i;\n",
        "proc local variables",
    )
    text = replace_once(
        text,
        """\tsnapshot->count = mt6797_a72_obs_count;
\tsnapshot->overwritten = mt6797_a72_obs_overwritten;
\tfirst = (mt6797_a72_obs_head + MT6797_A72_OBS_RING_SIZE -
\t\t snapshot->count) % MT6797_A72_OBS_RING_SIZE;
\tfor (i = 0; i < snapshot->count; i++)
\t\tsnapshot->records[i] =
\t\t\tmt6797_a72_obs_ring[(first + i) %
\t\t\t\tMT6797_A72_OBS_RING_SIZE];
""",
        """\tsnapshot->count = mt6797_a72_obs_count;
\tsnapshot->state = mt6797_a72_obs_state;
\tsnapshot->overflow = mt6797_a72_obs_overflow;
\tsnapshot->up_transaction = mt6797_a72_obs_up_transaction;
\tsnapshot->down_transaction = mt6797_a72_obs_down_transaction;
\tfor (i = 0; i < snapshot->count; i++)
\t\tsnapshot->records[i] = mt6797_a72_obs_ring[i];
""",
        "proc snapshot copy",
    )
    for obsolete in (
        "mt6797_a72_obs_overwritten",
        "mt6797_a72_obs_head",
        "observer-v1",
        "snapshot->overwritten",
    ):
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(obsolete)}(?![A-Za-z0-9_])", text):
            raise SystemExit(f"obsolete recorder token remains: {obsolete}")
    path.write_text(text)


def update_header(path: Path) -> None:
    text = path.read_text()
    text = replace_once(
        text,
        "bool mt6797_a72_obs_is_cpu(unsigned int cpu);\n",
        """bool mt6797_a72_obs_is_cpu(unsigned int cpu);
bool mt6797_a72_obs_accepts_sampling(unsigned int cpu);
""",
        "sampling-gate declaration",
    )
    path.write_text(text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    args = parser.parse_args()
    root = args.source_root.resolve()
    core = root / CORE
    header = root / HEADER
    if not core.is_file() or not header.is_file():
        raise SystemExit("source root does not contain the patched observer")
    update_core(core)
    update_header(header)
    print("prepared=recorder-first-cycle-latch-v2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
