# Passive dynamic-declaration session

## Hypothesis and result branches

The live reg-less `consys-reserve-memory` node supplies a nonzero `size`, valid
optional `alignment` and optional `alloc-ranges` using the observed equal
two-cell address/size widths. A coherent result validates the declaration shape
accepted by the compile-tested parser. Missing or malformed properties are a
negative result. Identity drift or wider access is refusal. No branch proves
that Linux allocated, reserved, protected or mapped the range.

## Exact finite protocol

- Candidate: already-running known-good Gemian; no deployment or reboot.
- Identity: release `3.18.41+`, boot ID
  `ce741f2c-462f-424e-aa90-49bada3a116f`, model `MT6797X`, checked before and
  after property reads.
- Budget: one SSH process, one script execution, ten remote seconds, fifteen
  host seconds, 16 KiB combined output. Failure consumes the attempt.
- Reads: exact DT root/reserved-memory cell widths and ranges, plus the exact
  `consys-reserve-memory` node's six named properties/presence markers.
- Excluded: every write, privilege request, mount, device/debug interface,
  `/proc/iomem`, register/resource read, radio control, firmware or calibration.
- Recovery: none; the protocol has no state-changing action.

No physical owner action is needed. The device remains on Gemian.

## Consumed result

The sole collection completed in 0.7 seconds with unchanged identity. The
exact node has no `reg`, declares 2 MiB `size` and 2 MiB `alignment`, one
allocation range from `0x40000000` through `0xbfffffff`, `no-map`, and no
`reusable`. Root and reserved-memory address/size widths are all two cells;
reserved-memory `ranges` is present and empty. The sequential property set is
syntactically compatible with the compiled dynamic parser. It supplies no
initialized `reserved_mem` base/size and proves no allocation or protection.
The attempt is consumed and must not be repeated under this contract.
