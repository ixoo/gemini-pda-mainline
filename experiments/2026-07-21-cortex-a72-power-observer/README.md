# Experiment: observe the MT6797 Cortex-A72 power resources without mutation

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-21-cortex-a72-power-observer` |
| Status | `attempt 1 failed/inconclusive; automatic watchdog-class return; do not repeat exact AE` |
| Subsystem | MT6797 Cortex-A72 power prerequisites, DA9214, TOPRGU reset, SPM/MCUCFG |
| Device variant | Current named Gemini PDA unit |
| Date(s) | 2026-07-21 |
| Investigator(s) | Project maintainers |
| Candidate | `AE` |

## Question or hypothesis

Can a kernel that differs from hardware-passed Candidate AD only in the
kernel/DT resource description and observer configuration bind all known
Cortex-A72 power prerequisites, read the inherited fixed-voltage state, and
retain the exact working eight-Cortex-A53 runtime without initiating a CPU8 or
CPU9 `CPU_ON` request or changing any power resource?

This is not an A72 boot test. Candidate AE keeps `maxcpus=8` and reuses AD's
initramfs byte-for-byte. Its observer advertises `ready=0`, `hooks_armed=0`,
and `provider_mode=observe-only`; those values explicitly deny use by a later
CPU-hotplug diagnostic.

## Evidence basis

The public Gemian kernel source is pinned locally at commit
`d388d350cb2dda8f23b99be6fa5db9628896e87f`. Its MT6797 A72 path coordinates
the external DA9214 BUCKB rail, TOPRGU PWRAP reset, SPM isolation state,
MCUCFG DCM, and private secure-firmware calls before PSCI. Live Gemian evidence
identifies the fixed pre-boot state as BUCKB enabled at 1,000,000 uV, with
SRAM requested at 1.1 V; the optional dynamic iDVFS enable returned early and
was not required for the observed vendor A72 boot. These facts justify a
resource observer, not an active mainline sequence.

Candidate AE describes I2C6 and both DA9214 outputs, exposes the MT6797 TOPRGU
reset controller, and instantiates a board-specific resource node. The driver
only acquires handles and performs `regulator_is_enabled()`,
`regulator_get_voltage()`, `regmap_read()`, and `readl()` snapshots. Package
validation rejects active regulator, reset, MMIO-write, SMC, `cpu_up`, or
CPU-hotplug registration calls in the added observer source.

CPU8 and CPU9 use the observer-stage `mediatek,mt6797-psci` method, which
returns before generic PSCI `CPU_ON`. This is a rejecting safety gate, not an
active power provider. AE must never exercise it: a rejection message means an
unexpected online request occurred and fails the experiment.

## Pre-boot contract

Kernel/DT/configuration hypothesis:

- Linux remains pinned to `7.1.3` and the new patch stack must be an append-only
  extension of Candidate AD's exact patch series.
- The isolated manifest profile is
  `observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-observer`.
  It must be exact AD plus `configs/gemini-a72-observer.fragment`.
- The resolved configuration changes from AD only by enabling built-in
  `CONFIG_REGULATOR_DA9211=y`, enabling built-in
  `CONFIG_MTK_MT6797_A72_POWER=y`, and appending exactly one
  `regulator_ignore_unused` token to the forced AD command line.
- `maxcpus=8` remains exact, so boot-time SMP initializes only CPU0--7.
- CPU8 and CPU9 must both retain the rejecting `mediatek,mt6797-psci`
  enable-method; CPU0--7 remain on generic PSCI.
- Candidate AE's ramdisk, USB shell, console, keyboard map, and reboot helpers
  are byte-exact Candidate AD. Only the rebuilt kernel and final DTB change.

Unique attributable evidence:

- Two reproduced kernel packages and two reproduced Android-v0 artifacts must
  agree byte-for-byte after normalizing only `generated_utc`.
- The installed full-partition SHA-256 and exact live forced command line
  identify AE; the inherited AD initramfs marker is lineage evidence only.
- A unique `10222000.a72-power` sysfs device must report `ready=0`,
  `resources_ready=1`, `abi=observer-v1`, `hooks_armed=0`, and
  `provider_mode=observe-only` on two reads five seconds apart.
- The snapshot must identify CPUs 8 and 9, an acquired PWRAP reset handle,
  enabled 1,000,000 uV Vproc, and readable SPM/MCUCFG values.
- Live CPU masks must remain `possible=present=0-9`, `online=0-7`, and
  `offline=8-9`; dmesg must contain one successful observer probe and no A72
  boot/rejection, PSCI error, or kernel fault.
- A stable boot ID and a capture after 45 seconds distinguish a real boot from
  package-only support or an early automatic reset.

How results change the next action:

- If every gate passes, preserve this evidence and use a new candidate for the
  first watchdog-backed CPU8 power-sequence test. AE itself is never promoted
  as active A72 support.
- If the observer does not bind, defers indefinitely, or lacks any resource,
  do not request CPU8; fix only the missing regulator/reset/syscon/DT contract.
- If BUCKB is disabled or not exactly 1,000,000 uV, do not enable it in AE and
  do not request CPU8. Reconcile bootloader/Gemian rail state first.
- If CPU8/9 comes online, an online request is rejected, the CPU masks change,
  or any fault/reset occurs, return to known-good Gemian, collect pstore, and
  do not repeat an identical artifact.

## Safety assessment

The observer source intentionally has no regulator enable/disable/voltage set,
reset assert/deassert, direct MMIO write, private SMC, CPU-hotplug callback, or
CPU online write. All sysfs attributes are read-only and unbind is suppressed.
`regulator_ignore_unused` prevents late regulator cleanup from changing
firmware state without incorrectly declaring either DA9214 output `boot-on` or
`always-on` in DT.

Post-attempt source audit narrows that statement to the observer source. The
whole candidate is not hardware-write-free: the enabled DA9211-family driver's
paged regmap performs `PAGE_CON` selector writes while reading DA9214 registers,
and lazy SCPSYS syscon reads may gate the node's attached MFG clock around the
read. The original package validator checked only explicit calls in the new
observer source and did not cover those supplier side effects. This is now a
known validation defect and is part of the reason exact AE must not be retried.

The exact AD storage-disabled configuration remains in force. The artifact
builder performs no device access, install, reboot, or flash action. The
runtime collector verifies the exact USB interface and uses only reads,
variable assignments, output, and bounded sleeps on the target. It never
writes CPU sysfs, regulator sysfs, reset controls, `/dev/watchdog0`, or storage.

## Associated code

- `configs/gemini-a72-observer.fragment`: final-wins observer and forced-command-line policy.
- `scripts/validate-package.py`: exact AD baseline, repository provenance,
  resolved-config delta, observer-source safety, built-in image, DTB, and
  two-package reproduction gates.
- `scripts/build-candidate-ae.sh`: deterministic Android-v0 assembly from the
  new package plus byte-exact AD initramfs and userspace payloads.
- `scripts/validate-boot.py`: canonical container, capacity, observer marker,
  and exact AD initramfs lineage checks.
- `scripts/validate-artifact-reproduction.py`: byte-and-mode artifact comparison.
- `scripts/collect-runtime.sh`: bounded, read-only collection through the
  inherited USB `nc` shell.
- `scripts/validate-runtime.py`: live identity, observer ABI/snapshot, CPU mask,
  45-second stability, dmesg, and fault gates.
- `scripts/derive-installer.py`: hash-pinned reconstruction or acceptance of the
  exact validated AD installer followed by an identity-only AE derivation.
- `scripts/test-installer-derivation.py`: non-device reconstruction, syntax,
  placeholder, override-surface, and storage-safety mutation tests.

## Procedure

1. Add the isolated profile named above to `kernel/manifest.json`, after all
   observer patches and their order are final.
2. Build it twice in independent guest build roots with
   `./scripts/dev-vm build-kernel`. Run the package validator once against
   exact AD and each AE package, then run its `--first/--second` reproduction
   mode.
3. Run `build-candidate-ae.sh` independently for both reproduced packages.
   Require the two output trees to pass `validate-artifact-reproduction.py`.
4. Before installation, record final package, config, Image.gz, DTB, raw boot,
   and exact-size padded boot2 hashes. Pin the three installer constants listed
   below, rerun the static tests, and derive the guarded installer. Use that
   guarded boot2 workflow only; the builder in this experiment does not install
   anything.
5. Manually select logical `boot2`. Do not type or remotely issue any CPU
   online, regulator, reset, watchdog, or low-level memory command.
6. Once the inherited USB service appears, run
   `collect-runtime.sh --interface IFACE --output NEW_FILE`. The collector
   waits read-only until 45 seconds uptime when necessary and repeats the
   observer read after five seconds.
7. After evidence is safely copied, use the already-proven bare `reboot`
   command through the USB shell and confirm return to a changed known-good
   boot ID. Reboot validation is inherited behavior, not AE's unique result.

## Guarded installer derivation

The production deriver currently refuses immediately because these exact
source constants are deliberately uncalibrated:

```text
AE_RAW_SHA256=TO_PIN_AE_RAW_SHA256
AE_RAW_SIZE=TO_PIN_AE_RAW_SIZE
AE_PADDED_SHA256=TO_PIN_AE_PADDED_SHA256
```

After the two reproduced AE artifact trees agree, pin `AE_RAW_SHA256` to the
SHA-256 of `gemini-a72-observer.boot.img`, `AE_RAW_SIZE` to its decimal byte
size, and `AE_PADDED_SHA256` to the SHA-256 after zero-padding that exact image
to 16,777,216 bytes. Those are the only three calibration edits. The installed
predecessor remains source-pinned to AD's full-partition SHA-256
`371fda65cf9c21406d6b08e52ffb46690426a7d356ba67aa9ffe1410e7d1e495`.

Run the non-device test before deriving:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 \
  experiments/2026-07-21-cortex-a72-power-observer/scripts/test-installer-derivation.py
```

With the three constants pinned, omitting `--source` reconstructs the exact
X-through-AD tracked installer lineage; alternatively, `--source` accepts only
the validated AD installer with SHA-256
`41f8a20b04f0bed34ce7b3a77662ee31ecae778b2372afb5275c436914d944c3`:

```sh
python3 experiments/2026-07-21-cortex-a72-power-observer/scripts/derive-installer.py \
  --output /PRIVATE/DIR/install-candidate-ae-boot2.sh
```

Fixture calibration is available only to the imported pure transform used by
the static test; the executable exposes no hash, size, predecessor, partition,
credential, or power-policy override. The derived installer retains exact live
GPT resolution on every gate, strict known-host checking with the repository's
mode-0600 Gemini key, inactive-root/unmounted/no-swap/no-holder checks, stable
external power plus full healthy battery, full private backup and checksum,
exact-match skip, one bounded 16 MiB write, sync/flush/full readback, and no
reboot or slot selection. Invoke it only for the named
`gemini@192.168.1.50` recovery target and a new direct child of the ignored
`artifacts/device-partitions/` directory.

## Observations

Two independent kernel builds reproduce all non-dynamic package payloads and
modes. Two independent Android-v0 constructions are recursively byte- and
mode-identical across 17 members. The final raw 7,385,088-byte image is SHA-256
`d9895f619ea9b4bd8fcd5ba8e8bb546d50afd65bccc1a4209d950f56408c1e0d`;
its exact 16 MiB zero-padded identity is
`0e7cc17ce214f3904bae7172c81e50327ffda19fa46601c76bac36232b1079a9`.

The calibrated guarded installer reconstructs exact Candidate AD, reproduces
twice at SHA-256
`df0a57334d8fb15251ee49d6a6fac029488714fe9823f9e8c569182ef57e8df7`,
and rejects all 32 safety mutations. It resolved live logical `boot2` as
inactive `/dev/mmcblk0p30`, preserved the full exact AD predecessor, wrote AE
once, synchronized and flushed it, and obtained a complete matching 16 MiB
readback. The install did not reboot or select a slot.

In attempt 1, the owner selected `boot2`; LK was the last visible stage, no
mainline console appeared, and the device then returned automatically to
Gemian. The post-return Gemian boot ID differed from the stable pre-attempt ID,
and the sanitized reset fields were `boot_reason=4`,
`androidboot.bootreason=wdt_by_pass_pwk`, and `powerup_reason=reboot`. That is a
watchdog-block-class return but does not distinguish watchdog expiry from a
direct TOPRGU software reset.

The authenticated recovery capture found configured ramoops and an empty
pstore archive. It contains no AE kernel/initramfs marker, observer line, CPU
request, fault, or last-progress boundary. A fresh full read of live-GPT
logical `boot2` still matches exact padded AE, while Gemian is rooted on the
separate primary partition. Thus storage integrity and the automatic return
are established, but AE kernel entry and even independently observed `boot2`
selection are not. See the [attempt-1 runtime
record](results/runtime-candidate-ae-attempt-1-20260722.txt).

## Analysis

The attempt fails AE's runtime gate and remains inconclusive about its internal
failure boundary. Source review ranks the new 3.4 MHz I2C6/DA9214 paged-regmap
probe first and the observer's MCUCFG/SPM/syscon snapshot second. TOPRGU reset
controller registration and the capped-off CPU8/9 PSCI gate are lower-risk:
neither invokes a reset or CPU_ON operation in this candidate.

## Conclusion

`failed/inconclusive; do not repeat exact AE`. The attempt does not prove that
the observer ran and adds no A72 support claim.

## Follow-up

Build Candidate AF as exact AE plus the sole forced-command-line token
`initcall_blacklist=mt6797_a72_power_driver_init`. This keeps I2C6 and the
DA9214 probe live while preventing only the observer registration/probe. A
stable console/USB runtime isolates the observer snapshot/syscon path; another
automatic return makes DA9214/I2C6 dominant and requires a separate DA9211
initcall-blacklist candidate. Do not construct or boot the active CPU8 provider
until this resource-path split passes. CPU9 and an all-ten-CPU boot remain
separate later experiments.
