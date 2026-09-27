# Passive CONMCU reset binding for the shared Wi-Fi owner

The permanent MT6797 CONSYS owner already binds the boot reservation, shared
remap register and three real VCN regulator handles. It still has no handle to
the independent CONMCU reset line needed to hold the controller through a
future ordered power transition. The selected TOPRGU driver already exposes
that line as `MT6797_TOPRGU_CONMCU_SW_RST` (bit 12); duplicating its keyed
register writer in the Wi-Fi driver would create a second reset authority.

The [single internal format patch](../../patches/proposals/0028-soc-mediatek-bind-MT6797-CONMCU-reset-to-owner.patch)
requires one named reset phandle, links Gemini's existing TOPRGU provider and
acquires a nonoptional exclusive reset handle during owner probe. It adds no
`reset_control_assert()` or `reset_control_deassert()` call, regulator vote,
CONN domain attachment, remap write, EMI change, firmware load or WLAN child.
The owner remains built in and suppresses manual unbinding. The patch was
exported from three exact files in the previously prepared Buildbox A53
firmware-prepare source, with SHA-256 inputs `c6750fa7…4deb4c2`,
`2fa60456…e72b4976` and `44aa0d05…6bd315` for the binding, owner and
Gemini DTS respectively. Its synthetic author does not certify DCO.

The `mt6797-a53-consys-reset-passive` profile extends the validated
firmware-prepare series in canonical order and retains its exact A53 config
fragments. Its compile hypothesis is that Linux 7.1.3 applies the patch,
resolves the reset and watchdog providers, links the owner and produces a
Gemini DTB with exactly one CONMCU reset phandle on the owner. A patch,
schema, config, compilation, DTB or package failure refuses promotion. Build
only from a clean pushed commit:

```sh
KERNEL_PROFILE=mt6797-a53-consys-reset-passive ./scripts/build-kernel --backend buildbox
```

A successful build is not a boot candidate or proof that the reset provider
registered on the PDA. The next bounded passive device gate would require a
guarded boot2 candidate and one authenticated changed boot. Its unique
observation is owner probe success with all existing resources plus the
exclusive CONMCU reset handle, a complete log and changed-boot Gemian return.
Probe refusal redirects the provider/phandle investigation; successful binding
allows the later owner transition to use the real reset API. Neither result
admits a reset assertion, rail transition, EMI write or firmware execution.

## Build result

The [sanitized receipt](results/build.json) pins the successful clean Buildbox
package from `766ada26`. All 540 selected patches applied; Linux 7.1.3 linked
the owner, TOPRGU watchdog and reset framework with the firmware-preparation
helper. The fetched package inventory passed. Focused schema validation,
binding/example compilation and validation of the packaged Gemini DTB all
passed without diagnostics. The owner node has one named reset phandle to
TOPRGU bit 12 and no power-domain attachment. Strict checkpatch found no
source-style issue; it reports the missing DCO sign-off and a warning that
DT binding files are usually split from driver changes for submission.

This is source/DT integration only. The packaged DTB differs from the
previously boot-tested service board image beyond the reset properties, so the
package itself must not be installed directly on boot2.

## Validated offline candidate

The [candidate recipe](build-candidate.py) retained the boot-tested passive
VCN image's initramfs, kernel configuration and board tree. It substituted the
newly built kernel and added only four properties to the accepted tree:
watchdog `#reset-cells` and phandle, and owner `resets` and `reset-names`.
The recipe checked the parent and Buildbox package identities, complete
candidate inventory, exact decompiled tree additions, LK boot container and
16 MiB boot2 padding. The [sanitized candidate receipt](results/candidate.json)
pins boot image SHA-256 `bfdd4ca0…8da14507` and full boot2 SHA-256
`9483e4bc…abfc2de`. The image, initramfs and keys remain private. Composition
took no device action. The [guarded installer](install-passive.py) is pinned to
this manifest, Gemian boot identity and observed keyboard-image predecessor
SHA-256 `34b56a58…780020`; its generated shell passed syntax and ShellCheck
offline. The [session wrapper](passive-session.py) accepted the
candidate offline and the [host collector](passive-host.py) expects the new
one-record reset-handle marker.

The next device test is one passive authenticated boot. A successful exact
owner record and complete service log would establish reset-provider binding
and handle lifetime; a provider/probe failure would redirect driver or DT
diagnosis; a boot or observation failure would remain inconclusive. No branch
may claim reset operation, active firmware loading or usable Wi-Fi. Installation
still requires the reviewed live-GPT boot2 guard, predecessor verification,
full-partition readback and clean shutdown. The owner selects boot2 physically
after the collector is armed.

## Live preflight

A bounded read-only [Gemian check](results/live-preflight.json) in boot
`b216072f…27055` found `wlan0` carrier 1 and the exact 16 MiB inactive
`boot2` partition at `/dev/mmcblk0p30`. The reviewed block-identity guard
passed with root on a distinct partition, and the full boot2 checksum matched
the installer-pinned predecessor. No write or shutdown occurred. These
point-in-time observations must be repeated by the installer immediately
before any write; they are not a deployment receipt.
