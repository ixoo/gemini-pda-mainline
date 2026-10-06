# Phase B compile 7: runtime-1 fixes

Status: validated compile-only; no candidate composed, no device test.

- Repository input: `db1b2aeae59b5bc117893b752f73e892efd78b10`, clean.
- Profile: `mt6797-a53-wifi-phase-b-compile`, 640 patches: the runtime-1
  selection plus proposals 0141 and 0142; `CONFIG_MT6797_STATION_JOIN=y` is
  resolved. Proposal 0140 stays unselected.
- Builder: Buildbox-1, 32 jobs; one submission, completed `2026-10-06T22:33:20Z`.
- Job: `db1b2aeae59b5bc117893b752f73e892efd78b10-mt6797-a53-wifi-phase-b-compile-m0`.
- Validated package inventory SHA-256: `47addc1327b7c843d530cded614b86b1baab504dd87557dbfec3212fc80421ae`.
- Release: `7.1.3-gemini-a53-wifi-phase-b-compile`.
- Managed job log SHA-256: `1bd3dd5c74cd1ced2ec5dad45877758da26fc47c05483321564830dbca2a33ce`.

Package checksums pass after fetch; both new patches are in the package
provenance, and the image carries the extended common-init failure footer
(`iir=… no-source=…`). The log has no MT6797 driver warning; its two
inherited warnings match [compile 1](COMPILE_1.md).

Before submission every fixture in `tests/` passed against the identical
source tree with ASan and UBSan: events, TX, RX and commands on the selected
headers; HIF, submit, rates, peer and handoff (join on and off); the unlinked
EAPOL decoder; and the two new runners for the WMT full I/O no-source cases
and join frame ownership. `check-repository` exited 0.

This is the package for the next Phase B candidate. It proves kernel
integration of the two fixes only; whether 0141 resolves the runtime-1
failure is decided by that boot's common-init result and footer.
