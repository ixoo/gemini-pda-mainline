# Native-crypto-delivery composition and runtime (proposal 0181)

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
- **Still to complete:** the host-side one-cycle session binding -- reusing the
  phase-b laptop-private host/capture and laptop-wifi-ssh for exactly one cycle,
  recording the device post-ACTIVE mode marker into the SSH receipt that
  classify-native checks, with classify-native as the verdict instead of the
  two-lifetime C3. Nothing here claims the Buildbox build produces a boot2 candidate.

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
   authored as `join-native.sh` (reviewed-pending). **STATUS: the host-side
   one-cycle session binding -- the laptop-private host/capture restricted to one
   cycle and laptop-wifi-ssh recording the mode marker into the receipt -- is not
   yet authored/executable-reviewed; this step is incomplete until it is.**
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
