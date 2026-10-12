# Native-crypto-delivery composition and runtime (proposal 0181)

How the admitted default-off diagnostic is composed into a build and a bounded
runtime. **Build and device remain held** until root reviews it. Candidate 32 /
runtime 33 stay pinned at `7b2bf45d` and are not touched — the native-delivery
diagnostic has its own candidate/runtime identity.

## Status (accurate scope)

- **Build-admitted and ready:** the kernel build profile below. Root's semantic
  review of the profile/fragment passed.
- **Offline scaffold only (not yet the executable tooling):**
  `prepare-native-delivery.py` validates the private inputs and the committed
  candidate receipt and creates the evidence root; it takes no device action and
  fabricates no hashes. The **laptop compositor, capture/session and the native
  classifier are still to be completed** (sections below describe the intended
  behaviour, reusing the candidate-32 tooling). Nothing here claims the Buildbox
  build produces a boot2 candidate.

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

## Laptop compositor — produces the boot2 candidate (reuse candidate-32)

The authored laptop compositor (reusing the existing candidate-32 compositor,
`../2026-10-07-mt6797-wifi-phase-b-join/build-candidate.py`, not a new
framework) consumes the validated package plus the **verified private parent /
RAM root**, changes only the intended kernel/release gate, preserves the DT,
PSCI, the clocks and the existing RAM members, produces/pads/validates the boot2
image, and generates the **real candidate receipt**
(`results/native-delivery-candidate.json`) with its true build commit, package
sha and padded-image sha. (This executable step is the to-be-completed tooling.)

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

## Native classifier (its own, not the translated C3 counters)

Success is classified by a **native** classifier over the native frame counts,
the firmware mode and the credit sequence together with the actual fresh Wi-Fi
challenge — never the legacy translated C3 counters. A completed native-only
challenge is route-4's precondition met for that mode and sample (intact
ciphertext + authenticated producer + MIC + working replay under the live key),
**not** sustained operation, not the enforcement answer, not driver completion.
A negative is **inconclusive** — never a capability claim, and never retried or
fallen back to ordinary plaintext.
