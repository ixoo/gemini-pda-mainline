# MT6797 connectivity AFE driver preparation

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-04-mt6797-afe-preparation` |
| Status | Driver draft; host, Buildbox compile/package and focused schema checks pass; runtime untested |
| Subsystem | CONSYS analog initialization before MCU release |
| Date | 2026-10-04 |
| Device action | None; no candidate construction or installation |

## Problem and change

The current owner releases the MCU after its checked ACR update without the
eleven AFE writes present in the selected Gemian reference. The
[source join](../2026-10-03-mt6797-wifi-audit/results/afe-source-join.json)
owns their order and provenance. These writes are a candidate explanation for
the missing receive path; they are not proved necessary or sufficient for RF.

Two independently authored preparation patches add an optional named `afe`
resource to the existing binding and insert the fixed sequence between the
checked ACR update and reset deassertion. Probe checks the exact `0x180b6000`,
`0x100` resource, name and resource-count bound and exclusively maps it before
domain attachment. The mapping stays local until resource acquisition succeeds.
A resource conflict or mapping error fails probe before power-on. The existing
power/reset/chip checks and retained uncertain-state policy remain in place.

An absent AFE resource produces no AFE writes. No board DT includes the resource;
existing profiles and the installed checked-version image are unchanged. The
new `mt6797-a53-consys-afe-compile` profile is the version-read compile profile
plus only the two patches, for compilation and binding checks. It is not a
runtime candidate and does not add a new one-shot selector.

GPS_SINGLE, the commented WF_TX_02 operation and the vendor's 64-word register
dump are excluded. The helper performs eleven MMIO writes without fabricated
readback acceptance. CPU-side ordered writes do not prove analog state or RF
effects. Hardware admission, safe access semantics and common-init completion
remain separate. The draft remains inside the existing experimental owner;
it does not yet supply the roadmap's re-triggerable common-init executor.

## Validation

The parent driver and binding were reconstructed by applying the exact selected
`patches/series-a53-wmt-versions` entries to just those two files. Their SHA-256
values match the published version-read integration receipt:

- Driver: `610eee5c625d4a0130531d545c5f57b32067c8ef545a535d3c5e7769bfbae1ec`.
- Binding: `10830407932eceb8eae5cffc7a4f86004308b67aad2fa7efeeacca635092c8e9`.

Both logical commits were exported with `git format-patch`, using a clearly
synthetic non-certifying internal author and no DCO. They are not submission-ready.

The [host fixture](test-afe.py) extracts and compiles the actual helper with
strict warnings, ASan and UBSan. It checks zero writes when the resource is
absent and all eleven addresses, values and ordering against the source receipt
when present. Supplemental source-order assertions check placement before reset
release, mapping before domain attachment and late publication of the mapping.
These assertions are not injected probe-failure coverage or kernel validation.

```sh
python3 experiments/2026-10-04-mt6797-afe-preparation/test-afe.py \
  /path/to/prepared/linux/drivers/soc/mediatek/mt6797-consys.c
KERNEL_PROFILE=mt6797-a53-consys-afe-compile ./scripts/build-kernel --backend buildbox
KERNEL_PROFILE=mt6797-a53-consys-afe-compile ./scripts/buildbox fetch-package
```

The [validation receipt](results/validation.json) binds the full Buildbox build
and validated fetched package to input commit `de521d6a`. The driver and binding
hashes in the prepared kernel exactly match the host-tested child. Both patches
pass strict checkpatch with only `MISSING_SIGN_OFF` excluded, because this is a
non-certifying draft. One patch-description line was wrapped after the build;
the kernel diff bytes and resulting source are unchanged, so this metadata-only
repair does not require another kernel build. The original package retains its
original patch inventory and commit identity.

Focused `dt_binding_check` passes. Direct DT validation accepts both the actual
nine-resource node and a temporary ten-resource fixture with AFE, and rejects a
wrong AFE name. The fetched package's board DT still has nine resources and no
AFE window. Two inherited warnings remain: trailing whitespace in historical
patch 0261 and an unused CPU rollback callback already reported by the parent
version-read build. Neither is an AFE driver warning.

No hardware acceptance is claimed. Before any later boot candidate, review the
effects and resource ownership, integrate the selected common-init steps, and
state the unique observation and decision branches. Preserve the currently
installed version-read candidate until its measurement is consumed.
