# CCMP1 — registration refusal before radio/data; available evidence preserved

**Closed to repetition. No association/parser/crypto data test occurred.** ROOT
ran ONE capture on boot `da2acc9f-8821-4452-8631-ca7d487e4793`, input
`83b91a6c54e45159763f62652b14710670bf895f`, source9b7bad2, packagef07c722c,
real [receipt](results/ccmp-stable-monitor-candidate.json)725a5422/raw94a281/full41881.
The installed bytes/release matched; no worker accessed the device.

## Observations and diagnosis

- Common init completed285/285, calibration/negotiation passed, WLAN private
  record prepared. Registration then warned at Linux7.1.3 `main.c:1076`,
  `ieee80211_register_hw+0xa30/0xc7c`, called from
  `mt6797_mac_register+0x3f0/0x460`; regulatory configuration stopped -22.
- Exact source predicate is SW_CRYPTO_CONTROL with NULL `wiphy->cipher_suites`.
  CCMP1 set that flag without an explicit suite list. This is a standard core
  admission defect, not an RX descriptor/PN/MIC/replay/producer result.
- Phase A `ready_for_scan=false`; no association, CCMP queue, DHCP/ping/SSH or
  helper launch. Absence is not a zero-valued successful data test.
- ONE `laptop-session-ccmp --execute` claimed observation/probe, then refused
  log-export: the enabled but never-started helper defaulted owned=true/safe=false.
  No recovery was sent by that failed session.

## Preservation and exactly one recovery

ROOT reviewed and actually preflighted the [specific continuation](CCMP1_CONTINUATION.md).
Exact9d9588b ran ONCE: seal/export and pending read-only regression probes passed;
the original snapshot verified37 files. Its additional full-log-through-seal
requirement incorrectly blocked the unused recovery budget. Original evidence
and that failed result were retained, not renamed/deleted/reclaimed.

Logger was already terminal at its finite600000ms deadline: firstseq0/last1995,
1996 records/145634B, sealed=yes/result=failed/deadline-expired/exit1. Export
transport, stable untruncated available-byte preservation and export were
complete. **Complete available preservation is not complete log through the
current seal**, nor a successful regression verdict. Original37-file manifest:
`c467e5071ceafc87ccc702260cf5eeeabfa07683ec7cf01c9c7e4f5071a0d7e2`;
kmsg SHA256 `c22fb27e2c521aafffc2df0f76f168e98c27691985deb50a27afef0979908ba5`.

ROOT reviewed/preflighted exact [recovery-only](recover-ccmp1-preserved.py)9f947213,
then executed it ONCE. It rebound all39 current files without another seal,
export, probe, startup or session; additional available manifest SHA256
`450c6c5041bbde97b576116af33853d7a0808f6d72f39685f92b1c14b87683c7`.
The original identity/recovery-binary script classified native request_count1.
Return v2 confirmed changed-ID Gemian after30.509s with **three connection
attempts, not three recoveries**. ROOT independently verified strict pinned LAN:
3.18.41+/aarch64/`a55435c4-ad0f-4aa3-9a53-67c9f2fa29e2`, different from mainline
and prior Gemian929b50a1. Both manifests and original unchanged files were verified.

Final result: `returned-with-incomplete-log`; available preservation=true,
recovery confirmed=true, log-complete=false, regression=false, compatibility=false,
scan=false. No emergency RAM-loss assumption or invented child quiescence.

## Evidence, successor and limits

The agent verified all11 sanitized final payload hashes from ROOT's retained
bundle; inventory SHA256
`9f6b9e12105e666bceac7c7ab0be26bee8cd3ba3b105035e8727a6cfdeeea6dc`.
Only sanitized scalar/result/hash metadata was transferred; raw logs, private
candidate/RAM, keys and AP identifiers were not published.

ROOT approved the three-addition source correction (MACa140b36a): a static CCMP
suite and pointer/count in the new-mode branch. Retain SW_CRYPTO_CONTROL plus the
actual key/TX/no-fallback gates; the flag alone does not prove every path avoids
software crypto. Source/host tests are not parser/hardware support.

Successor is fresh CCMP2, exact684 foundation +0190/0191 +one logical0192, total687.
Keep CCMP1 inputs/tools/roots/evidence frozen. Use new named series/profile so
the old explicit CCMP1 profile remains reproducible; canonical additions still
affect four historical implicit consumers, never new build foundations.
Future genuine no-scan must use the underlying no-leaf preparation and require
helper never started, preserving real started-child quiescence guards. No
repetition of CCMP1 or its consumed continuations. Full normal producer/GTK/
rekey/reuse/IRQ-DMA/clean-profile ten-minute Wi-Fi support remains incomplete.
