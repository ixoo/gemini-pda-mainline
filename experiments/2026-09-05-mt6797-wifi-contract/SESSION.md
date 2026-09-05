# Wi-Fi parent attribution: device session packet

This packet is completed and consumed. Its source hashes describe the original
session, reconstructible at `bbe78e38a3a089ec674a9106e2529ea20a14b04a`.
The [integration review](INTEGRATION_REVIEW.md) identifies corrected current
helpers; they are not admitted for a new physical attempt by this packet.

## Identity and ownership

- Proposed queue ID: `wifi-parent-attribution`; implementation owner: Wi-Fi
  workstream. Shared registry integration remains with Project Planning.
- At initial design, preparation was **preparing** until script hashes, host test receipt,
  review, live-kernel identity and authentication are recorded. Device:
  **unselected** until custody release. Both metadata protocols subsequently
  completed with their finite budgets consumed; custody is released. The
  [session result](results/device-session.md) is the disposition authority.
- Repository parent: `de48e24af88ef4647f8e94ec69975e5bd00d12ec`.
- No new package, kernel/DT/config/profile, initramfs or boot2 candidate.
  Kernel compilation, LK container and deployment checks are inapplicable to
  this metadata-only observation, not assumed passed.
- The coordinator subsequently authorized a bounded Wi-Fi inspection slot and
  return to Gemian through the exact reviewed recovery path. This removes the
  earlier lack of physical authorization, not the custody, identity or test
  gates. Exact handoff and results belong in `results/` before completion.

## Hypothesis and dependencies

Hypothesis: on the named Gemini in its known-good Gemian kernel, `wlan0`
belongs directly to the `180f0000.wifi` platform device bound to `mt-wifi`.
The retained vendor source supports an AHB transport; an SDIO-labelled log
message does not independently establish an SDIO function parent.

Required predicates before observation:

1. Prior custodian explicitly releases the current session and confirms unique
   evidence is preserved. A completed thermal test does not alone release it.
2. If a return from mainline is needed, use only its exact reviewed native
   recovery routine after release, boot-ID and tool-identity checks. Confirm
   disconnect/reconnect, changed boot ID and expected Gemian release. A missing
   recovery contract stops execution; do not guess bootloader controls.
3. Named-device identity, expected running release and boot ID are verified
   over an authenticated administration path. USB is preferred; the known
   Gemian SSH path may itself use Wi-Fi. Existing host key is
   pinned; no trust-on-first-use bypass or password in logs. Python 3 exists
   on Gemian. No package installation is part of this packet.
4. The collector bytes match the reviewed digest and pass synthetic fixtures.
   Capture stdout/stderr separately with a finite outer deadline. Connection
   failure, identity drift or incomplete output consumes the attempt and
   requires review, not automatic repetition.
5. Stable power, no unexpected heat, storage errors, recovery anomaly or active
   conflicting observer. Reading metadata is not permission to toggle radios,
   increase load or rerun consumed thermal observations.

The future mainline radio path requires a frozen A53 baseline first-pass
authenticated USB/console receipt, preserved recovery, the shared AP-DMA and
CONSYS resource contract and radio-specific firmware/regulatory admission.
It does not require A72 completion or ten baseline cold boots. This first
Gemian-only probe has no dependency on a new A53 candidate.

## Finite effects and capture

- One collection attempt in one verified Gemian boot. At most one separately
  reviewed native recovery transition if already in mainline; zero boot2
  selections, deployments or partition writes.
- Collector wall deadline: 15 seconds; per-file cap: 4096 bytes; total read
  cap: 262144 bytes; SDIO entry cap: 32. Host transport deadline: 30 seconds
  for the collection command. Recovery reconnect waits, if needed, have a
  distinct bounded protocol supplied by the custodian.
- Allowed: read kernel release/boot identity, allowlisted Device Tree text,
  `wlan0` parent/driver/subsystem links and numeric SDIO identity metadata.
  Boot identity is checked again before a result is returned.
- Excluded: firmware/calibration reads or loads, `/dev` access, MMIO,
  `resourceN`, driver bind/unbind, WMT ioctls/proc debug, debugfs, dmesg dumps,
  packet capture, MAC/SSID/IP inventory, network scan, rfkill, module load,
  performance load, PMIC/clock/reset control and thermal sampling.
- No radio transaction is issued by the collector. The already running
  Gemian system may transmit; this packet does not claim RF silence and does
  not change its networking state.
- No remote temporary file is needed: the reviewed script may be streamed
  into `python3 -` over the authenticated connection. Host raw stdout/stderr
  and the recovery receipt stay under a single private mode-0700 ignored
  `artifacts/wifi-parent-attribution/` session directory, files mode 0600.
  Do not overwrite a previous attempt. Sanitize before committing a receipt.
- Failure output is preserved. A timeout, unknown bus or missing attribute is
  never converted to a successful empty inventory. The script cannot prove
  that sysfs links remained stable during every read; any detected mismatch
  is a refusal and a successful result is a bounded metadata observation.

## Interpretation and next decision

| Result | Meaning | Permitted next work |
| --- | --- | --- |
| Exact `wlan0` platform parent, `mt-wifi` and `mediatek,wifi` metadata | Confirms OS-visible parent attribution; consistent with source AHB selection | Continue the MT6797 AHB/HIF and shared-owner protocol audit; does not authorize DMA or firmware start |
| `wlan0` has an SDIO parent and matching enumerated numeric identity | Contradicts the direct-platform-parent hypothesis for this exact boot | Preserve identities; compare actual function protocol to upstream; do not bind based on the ID alone |
| Both platform and SDIO objects exist | They may be independent functions; ancestry distinguishes the WLAN owner | Attribute only the direct parent; unrelated SDIO IDs cannot identify WLAN |
| Unknown/absent parent, incomplete metadata, changed boot or timeout | Inconclusive/refused | Inspect the bounded failure offline, repair protocol if needed, obtain a new reviewed attempt |

No outcome proves RF die revision, bus transactions, firmware version,
association, traffic, stability, regulatory safety or upstream support. An
empty SDIO list cannot rule out a hidden/integrated bus. A new physical or
firmware-operation experiment needs its own immutable inputs and action budget.

## Owner session card

This is a brief inspection of the known-good Gemian system. Keep the reviewed
administration cable and power connected. No boot2 selection or key sequence
is requested. If the device is still in a completed mainline session, the
custodian's verified return-to-Gemian procedure must be used first. Stop if
the expected authenticated connection does not return or if heat, power or
recovery behavior changes. No new radio is enabled by this inspection.

## Result and readiness

### Distinct presence follow-up admitted after v1

The coordinator admitted one distinct follow-up within the released Wi-Fi
custody after reviewing the first inconclusive result. Its hypothesis is that
one identifiable component of the expected netdev/OF chain is unavailable;
localizing that component will separate a missing netdev from a missing
parent/driver/OF property. This is not another run of the first collector.

The consumed follow-up used `parent_presence.py` at the revision above, SHA-256
`f2e5e344b81d4f4faee1e56b602f02c460aba9f62d148e2026714f3025b27fcd`,
with the frozen helper SHA-256
`c89820e47e499fd6bc5ebc39846125ab7e64fd38df12a17bdb4ddc58c8489d65`.
Fifteen synthetic tests, including Python 3.5 grammar and the exact streamed
module composition, pass. Pin both loaded source byte strings on the host;
the helper's embedded digest field is provenance, not self-verification.

One attempt; **eight fixed logical paths**, maximum **ten seconds**; no
directory enumeration and no property contents except start/end kernel and
boot identity. Expected boot is `65ad474e-847b-4d48-880a-9693d5d1c7b1`,
release `3.18.41+`. Paths are `wlan0`, its `device`, `subsystem`, `driver`,
`of_node`, `compatible`, `clock-names`, and the fixed platform Wi-Fi driver
link. Emit only metadata kinds and comparisons against expected destinations.
No arbitrary target path is serialized. The host transport has a 30-second
outer deadline; a default dry run reads none of these paths.

All eight expected relations support the original parent model. A partial
chain localizes unavailable metadata without proving physical absence. A
different relation is a contradiction to preserve, not a driver-selection
permission. Identity/time failure refuses the result. This follow-up also
cannot prove silicon identity, firmware execution or association. Record its
result without replacing v1, consume its attempt and release physical custody.

The offline test/digest receipt is
[`results/host-validation.txt`](results/host-validation.txt). Live custody,
exact kernel and boot identity, script digest, attempt consumption, classified
result and final device disposition must be recorded separately before this
packet can be called complete. Any changed script, withdrawn identity or
consumed budget invalidates an earlier readiness claim. Queue admission is
owned by the coordinator; this packet is not a batch runner.
