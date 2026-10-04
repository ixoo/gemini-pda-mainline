# Gemian session A: passive baseline

Status: charger log and static battery DT subset collected on 2026-10-04.
The [receipt](results/charger-log-dt.json) owns exact identity, source-script and
private evidence hashes. The [roadmap](../../docs/ROADMAP.md#current-plan-2026-10-03-review)
owns remaining order. This is not completion of session A or register admission.

## Packet and decision branches

Hypothesis: existing Gemian logs and static battery DT distinguish the current
CV selection and board-policy inputs from the public source assumptions. One
40-second authenticated LAN connection checks the returned Gemian boot ID,
`3.18.41+`, AArch64, `MT6797X`, Debian 9, systemd and running system state before
collecting one existing dmesg snapshot (maximum 1 MiB) and named battery nodes.
Identity is checked afterward; stdout is bounded at 1.5 MiB and stderr at 16 KiB.
No active register or power-supply read is part of this packet.

The first static name selection found `/soc/battery` but no meter node. A second
connection uses bounded compatible-property discovery (maximum 4096 DT nodes,
eight battery matches) to resolve that naming uncertainty. It reads static
properties only, with per-property limits, retains short values and names, and
checks the same boot identity before/after. It does not repeat dmesg or perform
a hardware retry. The exact scripts, processes and hash-verified inventories
remain private under `artifacts/gemian-session-a/`.

A complete register dump would identify the logged REG06 value at its historical
instant; a missing dump or selected-value log cannot establish current latched
state. Conflicting DT/source values require binary-path attribution before
reusing vendor policy. Identity, transport or bound failure stops the packet.

## Observations and implications

The log has 25 `charging_set_cv_voltage` records, each naming register selector
`0x1f`, request `4340000` and selection `4336000` microvolts. No matching
`bq25890 reg@` dump is present in this snapshot. These are logged selections,
not proved register readbacks. There was no camera action, charger transaction
or new measurement of cell voltage.

`/soc/battery` contains compatible `mediatek,battery` and a name only. The meter
is spelled `/soc/bat_metter`, compatible `mediatek,bat_meter`. Its static
`high_battery_voltage_support` is zero, AC-current cell is 80000 (800 mA under
the vendor's 0.01 mA units), configured USB is 50000 (500 mA), and unconfigured
USB is 7000 (70 mA). The receipt also records selected temperature, pull-up and
gauge correction inputs. Their presence is not proof of runtime use.

The running log differs from the public fixed-selector `0x24` description and
the live AC-current DT cell differs from the public 2.05 A assumption. The
zero high-voltage flag coexists with the 4.34 V logged request; configuration,
compiled defaults and the actual setter path must be reconciled. Next inspect
the retained running binary in the RE VM, without a live charger transaction.
Keep first mainline policy at the separately reviewed 4.2 V and 500 mA; this
subset does not admit a charger node, prove safety or import vendor limits.

## Validation

Both capture transports completed with stable expected identity and empty
stderr. Saved private inventories rehash exactly. Public facts are derived
from exact numeric log patterns and four-byte big-endian cells, excluding raw
logs, tables, firmware, credentials and personal identifiers. Documentation
and JSON checks apply; no kernel, DT binding or device driver change is made.

The [matched-boot binary follow-up](CHARGER_CV_BINARY.md) now attributes the
log as computed-only: both branches request fixed VREG selector `0x24` afterward
and ignore the write result. Thus the logs do not contradict that fixed write
request. Physical REG06 state and other session-A work remain unresolved.

The [REG06 access review](REG06_ACCESS_REVIEW.md) rejects the shared sysfs cache
and vendor dump as attributable single-read paths. The matched kernel disables
I2C-dev. A driver-owned one-shot byte/status observation needs transport-budget
review and implementation; C2a must separately admit REG0C fault-history reads.

The [transport review](REG06_TRANSPORT_REVIEW.md) identifies unchecked FIFO
completion and controller/DMA resets on failures. The successor must retain
same-operation completion/count evidence before accepting a REG06 value.

The [adapter review](REG06_ADAPTER_REVIEW.md) confirms the static I2C0 binding
and SCP effects. It selects observation of one existing periodic REG06 read
instead of submitting an additional request; implementation is pending.

The [observer inputs](observer/README.md) now implement the default-off passive
hook and pass 159 host acceptance cases. Patch generation/replay, integration
validation and kernel compilation remain pending; no candidate is admitted.
