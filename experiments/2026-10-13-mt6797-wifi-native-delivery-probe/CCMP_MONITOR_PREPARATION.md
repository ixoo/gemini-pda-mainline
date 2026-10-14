# CCMP monitor compatibility — build and composition preparation

This is **a validated build/fetch and real ROOT composition, not a boot or Wi-Fi result**. ROOT approved
the final source and separate ND6+0190+0191 selection. See the
[source/selection review](CCMP_MONITOR_INTEGRATION_REVIEW.md) and
[real build pins](results/ccmp-stable-monitor-build.json).

Kernel input is clean pushed `83b91a6c54e45159763f62652b14710670bf895f`, profile
`mt6797-a53-wifi-ccmp-stable-monitor`,32 jobs/modulesfalse/ordinary provenance on
Buildbox-1. The managed validator completed and fetch verified the exact package
inventory/provenance. All actual built driver files match final source9b7bad2.
Resolved config SHA256 is483e0165; its complete bytes equal C32's config plus only
the reviewed identity/release/mode/symbol changes. No API/type fix or rebuild was
needed. No historical profile was built.

## ROOT composition (offline, no extra assembly permission)

Use [the compositor](build-ccmp-candidate.py) with the validated exact package and
the existing private C32 parent. It checks all parent/package identities, the
whole kernel config, unmodified board DT/SMC/clock contract, exact64-member RAM
(only init release gate changes), boot container and exact full-partition padding.
It emits a **real** candidate receipt, without performing a device action.

```sh
BUILDBOX_HOST=buildbox-1 KERNEL_PROFILE=mt6797-a53-wifi-ccmp-stable-monitor BUILD_MODULES=0 ./scripts/buildbox fetch-package
python3 experiments/2026-10-13-mt6797-wifi-native-delivery-probe/build-ccmp-candidate.py --kernel-package <validated-package> --parent <private-C32-parent> --output <new-private-output>
```

The package remains pinned to kernel input83b91a6c even if later **tooling-only**
commits publish the compositor/bindings. No binding-only kernel rebuild. The
fetched package is under ignored `artifacts/buildbox/83b91a6c.../linux-7.1.3-gemini-f07c722c.../`.
Choose a fresh output directory; a real candidate receipt and all image digests
were returned before receipt-bound runtime/installer code was finalized. The real
receipt is linked below; no live boot identity or deployment receipt is invented.

Focused compositor tests compare a reconstructed, hash-verified **non-secret**
C32 config with the real new package and test parent/config mutations. They do
not read the private parent or prove its RAM/container composition. ROOT's actual
compositor run performed those gates. Use only the fresh receipt-bound CCMP tools
below, not a historical native installer/session for the new mode.

First runtime stays normal DHCP only, helpers prepared before ACTIVE, WLAN-bound
ping and fresh boot/mode-bound SSH within the real finite ACTIVE window. Failure
or short window is a partial result. GTK RX, normal producer, rekey/reuse,
IRQ-DMA reliability and clean-profile ten-minute Wi-Fi SSH remain unresolved.
Only ROOT operates the device and private C32/RAM. Guarded install/full readback/
clean shutdown and owner physical boot2 remain mandatory after real bindings.

## Real composition and receipt-bound tools

ROOT ran tool `72cd7ecd193ec3533cdc44cbf57fc7b316a61f33`, compositor SHA256
`91c5013258bdbb8ecc360776c0e419736e7fd16498ea28939d13505eb7606727`, with validated
package f07c722c and private C32. ROOT independently verified all6 files, exact
padding/config/board and64 RAM members (only init's release gate changed).
The agent received only the real hash/size [receipt](results/ccmp-stable-monitor-candidate.json),
SHA256 `725a5422eaf4cbf2014bd84bee4a5c7b9c8bd67e843ed348aea16138adc00544`;
no images, RAM, credentials or device access. The [runtime identity copy](runtime-ccmp1/results/candidate.json)
is byte-identical, not an invented execution receipt.

Required private candidate leaf:
`candidate-94a281d899d4caac51419352eda7a2cb28fb2f773f1e3888b61e0b903fe91bec`.
Raw boot is12670976B; full boot2 is16777216B/SHA256
`41881cb1345a9b1e3d39930c646a63d21499d5d7222039b8abfa7a9bf3b0be8e`.
Expected predecessor is last-installed ND6 full
`bf49d91c73689e479c7865ab15e298a72e859b95dfe5cfe449bae1e7c45791ef`, not a current
identity claim. ROOT freshly verifies Gemian boot/OS, GPT/root/inactive state,
stable power and full predecessor through the unchanged reviewed boot2 guard.

- [prepare-ccmp.py](prepare-ccmp.py): exact mode-0600 private binder suffix and
  real receipt; fresh `ccmp-stable-monitor/session-ccmp1`, capture left unclaimed.
- [install-ccmp.py](install-ccmp.py): real receipt/program/digest/predecessor
  binding to the existing private-source installer/guard, no write-policy change.
- [laptop-capture-ccmp.py](laptop-capture-ccmp.py): one reviewed Phase-A capture,
  fresh receipt/release/experiment/deployment-summary identity.
- [passive-host-ccmp.py](passive-host-ccmp.py) and
  [laptop-session-ccmp.py](laptop-session-ccmp.py): real namespace binding, C32
  required supplicant/CLI/private64 checks, unchanged evidence seal, owned-child
  quiescence, A53 regression and exactly one reviewed recovery.
- [join-ccmp.sh](join-ccmp.sh): one select with auto-reconnect disabled, DHCP
  hook/tool/listener prerequisites prepared **before select/ACTIVE**, real lease
  only, listener bound to leased WLAN address/interface, ping `-I wlan0`.
- [laptop-wifi-ssh-ccmp.py](laptop-wifi-ssh-ccmp.py): owned helper starts before
  join, mode/boot/lease/PID-bound challenge and ack; actual ACTIVE required in the
  probe/challenge/leaf, not historical ACTIVE during disable/cleanup.
- [classify-ccmp.py](classify-ccmp.py): separately named CCMP queue and provisional
  compatibility verdict; exact engine/zero-native/count/flag/healthy-cleanup
  grammar, verified sealed boot/fresh-mode SSH **and complete boot/cycle-bound
  leaf/process/export proof of real DHCP, listener, ping3/3 and consumed host ack**
  required. Early READY/SSH cannot overrule a later ping/window failure. Absence remains null,
  not zero. Hardware replay/key deletion/maintained support are never asserted.

Concrete ROOT-only commands, after setting the private paths and a private binder
whose suffix is exactly `join-ccmp.sh` (never publish its prefix):

```sh
export GEMINI_PRIVATE_REPO=<private-checkout>
export GEMINI_RUNTIME_ROOT=<private-runtime-root>
export GEMINI_JOIN_SCRIPT=<mode-0600-private-CCMP-binder>
python3 experiments/2026-10-13-mt6797-wifi-native-delivery-probe/prepare-ccmp.py
python3 experiments/2026-10-13-mt6797-wifi-native-delivery-probe/install-ccmp.py validate --candidate "$CANDIDATE" --previous-gemian-boot "$PREVIOUS_GEMIAN_BOOT"
python3 experiments/2026-10-13-mt6797-wifi-native-delivery-probe/install-ccmp.py prepare --candidate "$CANDIDATE" --previous-gemian-boot "$PREVIOUS_GEMIAN_BOOT" --output "$INSTALL_OUTPUT"
```

`PREVIOUS_GEMIAN_BOOT` must be ROOT's fresh verified Gemian identity, not a value
from historical evidence. ROOT reviews/preflights the derived private installer,
executes its guarded install/full readback/clean shutdown and retains the actual
deployment summary under `ccmp-stable-monitor/session-ccmp1/deployment-summary.txt`.
Only the owner physically selects boot2; no automatic substitute reboot.

After physical boot and ROOT's fresh authenticated release/boot verification:

```sh
export GEMINI_WIFI_SSH_KEYS=<existing-private-key-root>
export GEMINI_WIFI_SSH_BOOT=<fresh-authenticated-CCMP-boot-UUID>
python3 experiments/2026-10-13-mt6797-wifi-native-delivery-probe/laptop-capture-ccmp.py --candidate "$CANDIDATE" --execute
python3 experiments/2026-10-13-mt6797-wifi-native-delivery-probe/laptop-session-ccmp.py --candidate "$CANDIDATE" --execute
```

Do not rerun a claimed capture/session or repeat identical artifacts. If Phase A
is not ready, the inherited failure-session path withholds scan but still requires
preservation/quiescence/regression/one reviewed recovery; don't invent readiness.
No worker may execute any live-device command above.

## First boot hypothesis, evidence and decisions

Hypothesis: the admitted finite monitor producer provides complete G4/G1 CCMP
translated unicast for one provisional initial stable PTK; standard authorized
mac80211 decap plus strict driver PN allows a real DHCP lease, WLAN ping and fresh
mode/boot-bound SSH. Initial GTK install is allowed, GTK RX remains blocked, so
broadcast DHCP/ARP replies may prevent completion; no static fallback is admitted.

Unique evidence is this candidate's actual key/event/credit chronology, separately
named CCMP queue/flags/counts and original bounded engine, actual leaf DHCP/ping/
ready/SSH evidence and healthy cleanup or fault terminal, bound to the fresh boot.
No additional packet descriptor sample, observer, arbitrary radio write, HIF
predicate relaxation or identical retry is admitted. Same allRX512/1MiB/delivery64/
wall10s-or-lower grant/finite drain/deauth/cleanup/recovery contracts remain.

- Healthy queue + real DHCP/ping/mode SSH + sealed regression/recovery: first
  provisional finite compatibility only, not normal-mode or maintained support.
- Queue but no real lease/ping/SSH or too-short window: truthful partial; missing
  leaf evidence is absent, not fabricated zeros. No lease/READY fabrication.
- No accepted queue: preserve refusals/chronology; no new producer guarantee or
  crypto relaxation inferred from metadata. Do not retry unchanged input.
- HIF poison/deadline/cleanup ambiguity: preserve exact fault and unique evidence,
  no healthy retirement claim/retry; require the existing finite stop/quiescence/
  seal/regression and one reviewed recovery after ROOT verifies its identities.

Focused [runtime negatives](tests/ccmp-runtime-test.py) and
[actual namespace/installer/preparation tests](tests/ccmp-wiring-test.py) are host
simulations only. They cover exact receipt copies, fresh-root claims, binder/
permission/missing/changed-receipt refusals, actual lower namespaces/private64
requirements and derived real tool/digest routing, one-cycle helper ownership,
old/wrong-mode/boot/flags/count/cleanup refusals and actual shell ACTIVE gates.
The corrected protocol gate reuses retained C3 token/export validators, inspecting
their actual nested `cycles -> filename -> bytes` shape. Their inherited
two-cycle `complete` flag is false for a healthy one-cycle export, so a fixed
cycle1/all9-file framing/byte-count check supplies the separate one-cycle gate;
no new runtime export/effect is added. Complete process status, same before/after
boot, completed1/rearmed0/terminal1/overall0, explicit DHCP/lease/listener fields,
ping3/3 and leaf host-ack consumption are required. Missing/truncated/unexported
evidence fails the full verdict but retains queue/SSH partial fields. Tests cover
23 leaf/export negatives, a true all-evidence case and actual host-main rc1
handling with failed ping versus complete proof (executor mocked; no device).
Shell syntax/ShellCheck and repository guard/metadata/link/sensitive checks also
apply. They do not prove live kernel RCU/core/firmware behavior or actual deployment.
