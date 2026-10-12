# Native-crypto-delivery composition and runtime (proposal 0181)

> **STATUS (checkpoint, NOT execution-ready).** The native device-side leaf,
> classifier, Wi-Fi SSH helper (marker-gated), installer and offline prepare are
> authored and pass offline CLI/unit preflight. The capture/session identity
> nesting (capture-private EXPERIMENT, passive-session RELEASE/_CANDIDATE/_RECEIPT)
> is bound and unit-tested, but NOT yet verified by a full real preflight with the
> actual private ND1 artifacts. **Native execution is NOT declared ready** until
> root's full real capture/session preflight with the ND1 receipt (e1) passes.
> No device/radio/build action. The committed ND1 receipt (e1) carries no
> `supplicant`/`wpa_cli` keys, so the native session preserves the required wpa+cli
> 64-member checks from the inherited C32 parent evidence (candidate-32), not from
> e1, and does not weaken them; the native identity re-pointing updates the actual
> passive-session prepare/check_ram_root namespace.


How the admitted default-off diagnostic is composed into a build and a bounded
runtime. **Build and device remain held** until root reviews it. Candidate 32 /
runtime 33 stay pinned at `7b2bf45d` and are not touched — the native-delivery
diagnostic has its own candidate/runtime identity.

## Status (accurate scope)

- **Build-admitted and ready:** the kernel build profile below. Root's semantic
  review of the profile/fragment passed.
- **Executable laptop compositor (authored):** `build-native-candidate.py`
  composes the native candidate from the validated d104 kernel package on the
  verified candidate-32 parent, offline and gated. `prepare-native-delivery.py`
  validates the private inputs and the committed candidate receipt and creates
  the evidence root. Both take no device action and fabricate no hashes; root
  executes the compositor with the private parent/package.
- **Authored:** `classify-native.py` (the hardened one-lifetime verdict) and
  `join-native.sh` (the single-cycle device join: the corrected two-lifetime leaf
  mechanics restricted to one cycle, auto-reconnect disabled before the scan, a
  disabled network with one manual select, finite owned-child quiescence and the
  boot-bound quiescence record, and the readiness marker written only AFTER native
  ACTIVE and tagged with the native-delivery mode). `install-native.py` binds the
  reviewed boot2 guard.
- **Authored:** the complete host-side one-lifetime runnable set (narrow native
  variants that do NOT modify the frozen R34 files or their pins):
  `laptop-wifi-ssh-native.py` (the frozen phase-b helper reused, restricted to one
  cycle, with probe GATED on the device post-ACTIVE native-delivery marker before
  any connection and the marker re-verified in the Wi-Fi exchange, merged into the
  receipt), `passive-host-native.py` (the phase-b C2 session machinery re-pointed
  to the native identity and one cycle, verdict = classify-native, NOT the
  two-lifetime C3), `laptop-capture-native.py` and `laptop-session-native.py` (the
  reviewed capture/session with the private-source remap and the ND1 identity),
  and `install-native.py` (the reviewed boot2 guard, now binding its real program
  name and native receipt). Nothing here claims the Buildbox build produces a boot2
  candidate.

## Exact run order (root, with the private inputs; no device action authored here)

The private join binder is produced with the EXISTING reviewed API (no new
framework): `bind-target.bind(target, source, psk)` in
`../2026-10-07-mt6797-wifi-phase-b-join/bind-target.py`, where `target` is the
private mode-0600 channel-40 target JSON (ssid/bssid/frequency/channel), `source`
is the committed `join-native.sh`, and `psk` is the PSK hex. It returns the binder
bytes (`TARGET_SSID=`...`WPA_PSK_HEX=`/`TARGET_SSID_HEX=` prefix, never printed,
then the exact `join-native.sh` suffix); write them to a mode-0600 file and pass it
as `GEMINI_JOIN_SCRIPT`. `prepare-native-delivery.py` validates that suffix is the
current `join-native.sh`, the PSK/hex-SSID markers and the 0600 mode.

1. `GEMINI_PRIVATE_REPO=... GEMINI_RUNTIME_ROOT=... GEMINI_JOIN_SCRIPT=<binder>
   python3 prepare-native-delivery.py` -- validates the private inputs and the
   committed ND1 receipt, creates `native-delivery/session-nd1`, leaves
   `capture-nd1` for the capture to claim.
2. `install-native.py prepare --previous-gemian-boot <fresh-Gemian> --candidate
   <ND1 dir> --output <new dir>` -- generates `install.sh` offline (no `--execute`);
   root inspects it and runs `install.sh` under the reviewed boot2 guard (C33
   predecessor `74c5...` rederived from live GPT). Owner selects boot2 physically.
3. On the verified ND1 boot: `laptop-capture-native.py` (Phase-A, writes
   `capture-nd1/phase-a-result.json`), then `GEMINI_WIFI_SSH_KEYS=...
   GEMINI_WIFI_SSH_BOOT=<verified sealed boot> laptop-session-native.py
   --candidate <ND1 dir> --execute` -- one association, one post-ACTIVE Wi-Fi
   challenge, finite export/quiescence/seal/A53 regression/one reviewed recovery;
   the verdict is `classify-native` over the kmsg, the marker-bearing receipt and
   the verified boot. Return to Gemian through the reviewed recovery only.

## Build identity — Buildbox emits a kernel PACKAGE, not a boot2 image

- Profile `mt6797-a53-wifi-native-delivery-diag` = the reviewed station-join
  base (`patches/series-a53-wifi-native-delivery-diag`) plus
  `configs/gemini-a53-wifi-native-delivery-diag.fragment` applied last. The
  fragment sets `CONFIG_MT6797_NATIVE_DELIVERY_DIAG=y` and force-arms the
  read-only `mac.native_delivery_diag=1` (`CONFIG_CMDLINE_FORCE=y`; prefix `mac`
  = KBUILD_MODNAME of `mac.o`), preserving `clk_ignore_unused` and PSCI
  (`CONFIG_ARM_PSCI_FW` untouched) with a distinct USB-gadget identity.
- Build on buildbox-1: `BUILDBOX_HOST=buildbox-1 KERNEL_PROFILE=mt6797-a53-wifi-native-delivery-diag
  KERNEL_JOBS=32 ./scripts/build-kernel --backend buildbox` from a clean pushed
  checkout, in the persistent `/workspace` build root. Buildbox has **no private
  RAM root or parent**: it emits a **validated kernel package** for the HEAD and
  profile. No candidate receipt or boot2 hash is produced here or pre-written.

## Laptop compositor — produces the boot2 candidate

`build-native-candidate.py` consumes the validated d104 package plus the
**verified candidate-32 parent**, reusing candidate 32's board DT and its whole
64-member private RAM root byte-identical except the one release-gate string the
init checks (phase-b -> native-delivery). The kernel configuration is candidate
32's plus exactly three verified changes -- the forced
`mac.native_delivery_diag=1` command line and the distinct USB identity, the
LOCALVERSION, and `CONFIG_MT6797_NATIVE_DELIVERY_DIAG=y` -- and anything else
differing is refused. It produces, pads and validates the boot2 image and the
**real candidate receipt** (with its true build commit d104654d, package sha
aa305e66…, padded-image sha) and `native_delivery_diag: true`. Reuses only
require/regular/sha/nodes, the newc parse/encode and the boot builder/analyzer,
not the C37-pinned Phase-A composer. Offline, no device action; root runs it with
the private parent/package. CLI:
`./build-native-candidate.py --kernel-package <linux-7.1.3-gemini-aa305e66… dir> --parent <candidate-32 dir> --output <native-candidate dir>`

## Runtime — one native diagnostic lifetime (not join-twice)

1. Install the composed image to logical `boot2` under the **reviewed device
   guard** (standing boot2 approval); the predecessor is rederived from the live
   GPT at deployment. Shut down cleanly; the owner selects `boot2` physically.
2. Boot mainline. The forced parameter arms the diagnostic. The runtime drives a
   **single** association: the existing `wpa_cli` contract disables
   auto-reconnect before any scan and selects exactly **one** cycle
   (`join-once.sh`, not `join-twice.sh`). After its first window the diagnostic
   stays CLOSED with the sticky plaintext withhold in force; the admitted
   protocol does **not** authorize a second association.
3. **Observation is Wi-Fi, not USB.** The device writes a fresh boot/mode-bound
   ready marker only **after** native state reaches ACTIVE; a fresh Wi-Fi SSH
   exchange to the station's DHCP address, gated on that marker, is the proof.
   USB-gadget is used only for readiness and the reviewed guards, never as proof
   of Wi-Fi crypto, and never a pre-switch receipt.
4. **Recovery** is the reviewed one-shot path once, after preserving the raw
   kernel/supplicant/result evidence and owning+quiescing the helper group
   before any export/seal; confirm fresh Gemian afterward. Any ambiguity forbids
   further radio commands; no reassociation, reboot or ordinary-plaintext
   fallback.

## Native runtime CLI (one lifetime; root runs offline-reviewed, installs after R34)

candidate 33 (runtime 34) is installed first; ND1 is installed only after runtime
34 is complete and recovered. The install predecessor is the currently-installed
candidate 33 (74c5f711), which the reviewed guard rederives and verifies at
deployment. `<nd1>` is the composed native candidate directory.

1. Compose (root-run, offline): `./build-native-candidate.py --kernel-package
   <linux-7.1.3-gemini-aa305e66… dir> --parent <candidate-32 dir> --output <nd1>`
2. Offline prepare (own evidence root native-delivery/session-nd1):
   `./prepare-native-delivery.py`
3. Installer — generate the derived guard OFFLINE (no device write), then root
   runs the derived install.sh under the standing guard:
   `./install-native.py prepare --previous-gemian-boot <gemian> --candidate <nd1> --output <install-dir>`
   then `bash <install-dir>/install.sh` (no session selector needed; this is a
   single native candidate, not a 33/34-parameterized tool).
4. Phase-A capture and the single reviewed C2 join: the SINGLE-lifetime join
   (join-once.sh: auto-reconnect disabled via wpa_cli, one selection and
   association only); the diagnostic engages in the data phase; the device writes
   a fresh boot-AND-mode-bound marker only AFTER native state ACTIVE; the fresh
   Wi-Fi SSH challenge runs only after that marker, and its receipt records the
   marker (boot, mode, after-ACTIVE). The reviewed finite helper/supplicant/
   listener quiescence, the registered export budgets and the single reviewed
   recovery all apply. The device join and the post-ACTIVE mode-bound marker are
   authored as `join-native.sh`. **STATUS: the complete host-side one-lifetime
   runnable set (capture/session/helper/host/installer/binder validation) is
   authored with offline CLI preflight tests; root exercises it with the actual
   private inputs before any device action. No device action is taken here.**
5. Verdict: `classify-native.py <kmsg.log> <wifi-ssh-receipt.json> <verified-boot>`
   keeps two separate conclusions. ELIGIBLE DELIVERY (necessary, not sufficient):
   the exact owned one-cycle state/action sequence (1 act1, 2 act0, 3 act2, 4
   act0), no fault, and >=1 protected-native MPDU queued with crypto-bypass flags
   0x0. AUTHENTICATED (the positive): a fresh Wi-Fi SSH exchange through
   exclusively native RX completed, its receipt bound to the VERIFIED sealed boot
   and the device post-ACTIVE native-mode marker. native= counts eligible MPDUs,
   not authentication; translated C3 counters are never used.

## Native classifier (its own, not the translated C3 counters)

Success is classified by a **native** classifier over the native frame counts,
the firmware mode and the credit sequence together with the actual fresh Wi-Fi
challenge — never the legacy translated C3 counters. A completed native-only
challenge is route-4's precondition met for that mode and sample (intact
ciphertext + authenticated producer + MIC + working replay under the live key),
**not** sustained operation, not the enforcement answer, not driver completion.
A negative is **inconclusive** — never a capability claim, and never retried or
fallen back to ordinary plaintext.