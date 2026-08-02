# DA921x post-event identification lifecycle

| Field | Value |
| --- | --- |
| ID | `2026-08-01-da921x-post-event-lifecycle` |
| Status | `inputs validated; exact Buildbox build pending` |
| Subsystem | regulator, I2C, driver core |
| Device variant | Named Gemini PDA development unit |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 3 identification lifecycle |

## Question or hypothesis

Now that Stage 26 proved the exact real-compatible client's natural add path
serviceable, can the already reviewed identification-only legacy DA921x driver
bind naturally, complete its exact two-pass fourteen-read contract, unbind
without a bus transaction, and rebind once while preserving the complete
serviceability baseline and issuing no register-data write?

This is not a repeat of the ambiguous 2026-07-29 lifecycle candidate. It is a
new configuration derivative of the runtime-proven Stage 26 source and retains
the durable Stage 26 natural-device-add observation path. The only functional
configuration change is `CONFIG_REGULATOR_DA9213_LEGACY=m` to `y`; a distinct
release and USB product string make the result attributable.

## Decision

- Initial natural bind must expose the exact driver link, one identity log,
  and controller/oracle counts `14/8/6` with every write/other counter zero.
- One bounded unbind must remove the driver link and secondary dummy client
  without changing any transfer or oracle counter.
- One explicit rebind must restore both software ownership links, add exactly
  fourteen more reads, produce a second identity log, and reach `28/16/12`
  with every write/other counter still zero.
- The Stage 26 event state must remain exact and CPU0--7, CPU8/9-offline,
  console, keyboard, USB, I2C5/AP-DMA, DVFSP, and native-reboot serviceability
  must remain unchanged.
- Success closes the identification lifecycle and permits the ownership audit
  and passive-provider design. It does not prove a regulator provider, a
  register-data write, suspend/resume ownership, or A72 power.
- A tuple mismatch, strict-prefix read count, transfer error, unexpected
  message, write, bind/unbind failure, or serviceability regression keeps the
  problem in the identification/I2C layer and blocks provider work.

## Safety and negative space

The driver and controller oracle are unchanged from canonical patches `0124`
and `0126`. The driver has no provider, regmap, register-data write, retry,
reset, IRQ, remove, shutdown, or PM callback. Its only hardware operation is
the fixed fourteen combined one-byte-pointer/one-byte-read transcript.

The runtime helper first proves the initial bind and every baseline gate while
sysfs is read-only. It then remounts only sysfs read-write, installs an exit
trap that restores it read-only, writes the exact `1-0068` name once to
`unbind` and once to `bind`, restores sysfs read-only, and validates the final
state. Unbind is software-only; rebind is the one predeclared repeat of the
fourteen-read identity hypothesis. There is no block-device, partition,
storage, module-load, provider, regulator-operation, or CPU8/9 path.

Build only through Buildbox from an exact clean pushed commit. Do not use a
native VM kernel build without an explicit owner request.

## Evidence plan

The exact successful sequence is `14 -> 14 -> 28` combined reads,
`8 -> 8 -> 16` primary reads, and `6 -> 6 -> 12` page2 reads. Controller
transfer, DMA-start, nonzero-start, and IRQ counts must follow the same
`14 -> 14 -> 28` sequence. All write-only, register-data-write, other-shape,
other-address, suspend, resume, and failure counters remain zero. A fresh
read-only postcheck must confirm the final bound state, exact counters,
read-only sysfs, helper removal, and complete serviceability.

Exact input, build, candidate, deployment, and runtime identities belong in
`results/` as each gate closes. Visual white/grey-screen or reboot behavior
alone remains inconclusive.

## Input validation

The profile exactly extends the runtime-proven Stage 26 fragment stack and
changes the identification driver from module-only to built-in. The canonical
136-patch series is unchanged; all 54 profiles satisfy the canonical-order
invariant and all eight focused mutations are rejected. The original
fourteen-read contract validator and its six unsafe-mutation cases pass. The
new static lifecycle contract passes, and its runtime classifier rejects five
decision-changing unsafe mutations. Bash syntax, Python compilation, and
managed-VM ShellCheck pass. No native VM kernel build was run and the device
was not accessed while preparing these inputs. Exact identities are in
`results/input-validation.txt`.
