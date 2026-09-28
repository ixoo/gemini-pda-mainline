# Mainline VCN28 boot-control observation

The passive CONSYS owner can acquire the MT6351 VCN28 regulator handle and
confirm the CONN power domain is OFF, but it cannot yet account for VCN28's
separate hardware-control selector. The [Gemian v8 cycle](../2026-09-26-gemian-wifi-reference/results/vcn28-cycle-v8-1.json)
observed bit 3 of `LDO_VCN28_CON0` (`0x0a0c`) change 1→0→1 across a last-client
off/on cycle. The source-clock selector fields stayed 3. That observation does
not establish what a mainline cold boot inherits from the loader.

The `mt6797-a53-vcn28-boot-observe` profile adds one read-only probe sample to
the exact boot-tested passive domain-link foundation. After the checked-OFF
query, the owner verifies its `vcn28-supply` node is `ldo-vcn28` under the
MT6351 regulator and PMIC nodes, then reads `0x0a0c` through the acquired
regulator's shared regmap. It records the raw value, bit 3, bits 7:5 and bits
13:11 once in the kernel log. It makes no regulator vote, PMIC write, reset or
domain transition. A failed read refuses the manager bind and detaches it from
the domain.

## One-boot decision

Hypothesis: a cold mainline boot with CONN checked OFF has an attributable
VCN28 control value, and the passive A53 service baseline remains healthy.
The unique observation is the raw PMIC value in a complete authenticated
mainline log, tied to the exact boot2 candidate and changed boot ID. If bit 3
is zero, the owner may use that value as this boot's initial software-control
state only. If it is one, the owner must treat hardware-control mode as
already selected before its first rail vote. If either source-clock field
differs from Gemian's observed 3, investigate the earlier writer before
selecting a mainline mode sequence. A read error or A53 regression rejects
this candidate. No branch admits an active VCN28 or CONN transition by itself;
exclusive votes, physical control inputs and retained-fault recovery remain
separate gates.

Only the active named candidate will be installed in boot2 through the
reviewed live-GPT guard, full readback and clean shutdown. The owner selects
boot2 physically after the USB collector is armed. Complete logs and device
identifiers remain private; publish only sanitized results and hashes.

This internal patch has synthetic non-certifying authorship and is not an
upstream submission.
