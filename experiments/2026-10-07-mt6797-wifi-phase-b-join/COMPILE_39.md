# Compile39 — terminal regulatory producer fence (0186)

The source-reviewed two-line station guard blocks regulatory submissions after
explicit close, including after healthy cleanup. It preserves benign unclosed
healthy-stage3 restore and existing active/fatal fences. No poison reset, page
refund, guard/budget expansion, IRQ/register operation or restart claim is added.

## Exact source, tests and build

- Kernel input: `868ef7217d131daa469e8e866c0f442d77a0c1b5`.
- Profile: `mt6797-a53-wifi-phase-b-compile`, managed clean pushed checkout,
  32 jobs, experiment selector unset, one heavy build.
- Format-patch SHA:
  `d380e0865ca7f0c88f268080a12e81b99e1bd57f29ab0cdf8cc1f6358b6a8b80`.
- Parent mac.c: `fc356246a0b96a80911ffd6d8b9c463b9140ca6c62e23538f2e1a2ee11ba1a7a`.
- Exact replay and built mac.c:
  `ed789fda4fee06ad207e8e76cc17d123dd70b5cfe56d6a6d93ab6d587524fe37`.
- Fixture `tests/regulatory-close-test.c` SHA:
  `f99f0dd23d2092030916462dd0a4bd7fd1c0e5945b5e97a8e88e1361a58f6bf4`.
- Actual-function runner `tests/run-regulatory-close-test.py` SHA:
  `9bb56ff4772a76e888abbb492577f62f028eeecb81454e9a97b1790eb6333085`.
- Package inventory:
  `ce431869bcaaba805eb4b46bbbb455b3627c07d083123b28bed1bf646e88235c`.
- Image.gz: `9f97039a9874d93545d04a07cee6c1542ef73586aeffc506dc6e25ebb857a853`.
- Config: `975f8703e4061d8676dff6fc7835312f949f9ce3317b3fd900a3219cce0c312d`,
  byte-identical to compile38/C34. No native 0181/0185 selected.
- All 682 parent patch bytes/order unchanged, only additive0186; 683 selected
  patches replayed and validated. Package integrity/provenance and fetch passed;
  modules disabled, 123 DTBs, no hardware write.

The SAME actual stop/close/regulatory test fails the unmodified parent at the
post-close sender assertion and passes fixed replay/built source under strict
warnings + ASan/UBSan. Test calls during the simulated unlock/cancel gap and
after actual stop reach no sender/debit/new sequence. Benign unclosed stage3,
idle stop, active/fatal fences, sticky errors and unsent/submitted sentinel
ownership are covered. Kernel/policy/HIF/idle-retirement/scan-cancel boundaries
are mocked; this is not hardware retirement, firmware or kernel concurrency
proof. Existing absence dequeue/lifecycle fixtures also pass on built source.

Repository, all-profile canonical-order audit, staged whitespace/syntax/sensitive
data/manual review passed. Actual format-patch checkpatch has zero warnings;
only the standing internal-archive missing-signoff exception remains, with no
invented DCO. Inherited patch-application whitespace and unrelated unused CPU
inventory function warnings remain; no compiler error or new driver warning.
DT schemas/device tests were not run for this MAC-only change.

Decompressed image is 15960072 bytes, 65536 fewer than compile38; effective image
size is 16580608. This is an artifact-size observation, not a claimed cause or
hardware behavior. Configuration and exact reviewed source identities are pinned
above; no unrelated input change is inferred from size alone.

## Proactive composition/preparation, not a boot request

`build-candidate-35.py` reuses frozen C32 composition validation with this exact
kernel/package/Image.gz. Parent private DT/config/64-member RAM root must remain
byte-identical. The custodian supplies private parent inputs and returns the
real receipt; none is invented here. `prepare-runtime-36.py` binds fresh
`wifi-phase-b/session-36`/`capture-36` and refuses until that actual candidate35
receipt exists. Final receipt/installer/capture/session pins and predecessor
must follow actual composition and device-queue state; no placeholder deployment.

ND3 frozen `d37` remains installed and first; C34/R35 input1ed/package074/real8505
receipt and reviewed815 runtime remain immutable offline evidence. This guard
does not substitute a candidate in their queue or require an observer-only boot.

## Next concrete missing gate

Explicit close is still intentionally terminal; start rejects join_closed.
Normal stop/start/reuse needs verified submitted frame/page and owned peer/key/
channel retirement before fresh-start admission. Clearing terminal/poison flags
or reusing the capped key-done counts is not that gate. General status-owner,
IRQ/DMA, authenticated/replay delivery, rekey, consolidation and sustained WPA2/
DHCP/ping/ten-minute clean-profile SSH remain incomplete. This compile is one
producer fence toward that goal, not maintained-driver or runtime completion.
