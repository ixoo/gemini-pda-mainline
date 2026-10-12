# Native-crypto-delivery composition and runtime adapter (proposal 0181)

How the admitted default-off diagnostic is composed into a build and a bounded
runtime. This is the authored compositor root reviews and then executes with the
private laptop inputs; **build and device remain held until that review**.
Candidate 32 / runtime 33 stay pinned at `7b2bf45d` and are not touched — the
native-delivery diagnostic has its **own candidate/runtime identity**.

## Build identity (its own profile)

- Profile `mt6797-a53-wifi-native-delivery-diag` (`kernel/manifest.json`): the
  reviewed station-join base (`patches/series-a53-wifi-native-delivery-diag`,
  the compile-37 series with 0181 appended) plus
  `configs/gemini-a53-wifi-native-delivery-diag.fragment` applied last.
- The fragment sets `CONFIG_MT6797_NATIVE_DELIVERY_DIAG=y` (inert at CONFIG) and
  **force-arms** it on the command line with `mac.native_delivery_diag=1`
  (`CONFIG_CMDLINE_FORCE=y`; the parameter is read-only, prefix `mac` =
  KBUILD_MODNAME of `mac.o`). `clk_ignore_unused` is preserved, `CONFIG_ARM_PSCI_FW`
  (PSCI) is untouched, and the USB-gadget link carries a distinct
  `Gemini-Native-Delivery-Diag` identity so the laptop tells this boot apart.
- Build only on Buildbox: `./scripts/build-kernel --backend buildbox --profile
  mt6797-a53-wifi-native-delivery-diag` from a clean checkout of committed
  inputs. The build emits the candidate receipt
  `results/native-delivery-candidate.json` with the real
  `kernel_build_commit` / `kernel_package_sha256` / `boot2-padded.img` sha and
  `kernel_release = 7.1.3-gemini-a53-wifi-native-delivery-diag`,
  `physical_admission = false`, `native_delivery_diag = true`. No hash is
  pre-written in this repository.

## Runtime adapter (offline preparation)

- `prepare-native-delivery.py` is driven by `GEMINI_PRIVATE_REPO`,
  `GEMINI_RUNTIME_ROOT`, `GEMINI_JOIN_SCRIPT` (the same reviewed C2 join the
  diagnostic engages during). It validates the private inputs and the committed
  receipt (release, `physical_admission=false`, the armed marker; hashes **read**
  from the receipt, never fabricated) and creates a fresh evidence root
  (`native-delivery/session-nd1`, leaving `capture-nd1` for the capture to
  claim). It takes **no** device, radio, build or key action.

## Device runtime (reviewed, held)

1. Install the built kernel to logical `boot2` under the **reviewed device
   guard** (standing boot2 approval): resolve `boot2` from the live GPT in
   known-good Gemian, verify identity / inactive-unmounted-non-root / size /
   writability / stable power, pad to exact size, write, sync, full readback
   match. The predecessor is rederived by the guard at deployment, not pinned
   here. Shut down cleanly; the owner selects `boot2` physically.
2. Boot mainline. The forced parameter arms the diagnostic; the reviewed C2 join
   brings up the association and the one-shot window engages in its data phase.
3. **Observation** reuses `../2026-10-07-mt6797-wifi-phase-b-join/laptop-wifi-ssh.py`
   over the USB-gadget link: one bounded SSH exchange. Because every ordinary
   data frame in the window is delivered native-protected with the mac80211
   bypass flags clear and the FW-decrypted translated path withheld, a completed
   SSH exchange is itself the proof that mac80211 decrypted, MIC-verified and
   replay-accepted those frames under the live key. The in-kernel window is
   bounded by the implemented ceilings (10 s / 512 frames / 64 protected-native
   / 1 MiB) with the finite owed-completion drain (64 reads / 256 KiB / 750 ms);
   any budget end or ambiguity ends the window.
4. **Recovery** is the reviewed one-shot path back to Gemian after preserving
   evidence and verifying identity. No reassociation or reboot fallback; any
   ambiguity forbids further radio commands.

## Boundary

A completed SSH challenge is route-4's precondition met for that mode and sample
— intact ciphertext + authenticated producer + MIC + working replay under the
live key — **not** sustained operation, not the enforcement answer, not driver
completion. One negative is inconclusive, never a capability claim.
