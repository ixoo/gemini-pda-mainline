# First-review repair: independent evidence freeze

Freeze identity: `wlan-common-lifetime-evidence-v1`, declared during the
2026-09-06 first-review repair before changing the verifier. No new source
requests or citation changes are authorized by this repair.

The frozen objects are the existing 17 complete source identity tuples and 42
exact citation anchors from the first-review handoff, not regenerated expected
values on verifier startup. The source tuples include source ID, path, pinned
raw URL, whole-file SHA-256, Git blob SHA-1, byte size and line count. The
citation map includes each key's source ID, inclusive line pair and symbol.

| Object | Canonical SHA-256 |
| --- | --- |
| Source identity list, sorted by source_id | `babc630b39828d21513dec6c727ed5a2009409a48b0cd1254c9273123bb103ca` |
| Complete citation map | `f47ee47c50e76874537b33e0f357584073763e9f45106780a8855eab9c3b3fe0` |

Canonical encoding is Python JSON with `sort_keys=True`,
`separators=(',', ':')`, `ensure_ascii=True`, encoded as UTF-8 without a trailing
newline. The independently fixed constants in [verify.py](verify.py) implement
this freeze; the verifier must not derive its expected values from mutable
inputs or this document. Changes require an explicit reviewed replacement
freeze, not updating constants merely to make a failing check pass.

Pre-repair whole-file identities, measured before this declaration:

- [inputs.json](inputs.json):
  `67b821b2f67c719c25b6ff10c41c9946b339e4cbead8e83dd28b90ca50377944`.
- [verdicts.json](verdicts.json):
  `fbdec54de0b03a81894cef7f0c9a47ed2ccea62c5e9e5f613d6c21169c6a30bf`.
  This historical digest will change for the authorized unregister-state wording;
  its citation map remains frozen above.

All 13 reused source tuples must additionally match field-for-field against
the predecessor's pinned inputs JSON (SHA-256
`157c990f2f3a04099723ce7098e61840ec3756842381397e787b8ed5956e9496`).
Path comes from its allowlist; SHA-256, blob, size and line count come from its
raw-source rows; URL is derived from its fixed repository/pin and that path.
This check is independent of cross-consistency among new experiment records.

This freeze preserves reviewable evidence identities. It does not upgrade
source semantics, runtime equivalence, cleanup guarantees or hardware support.
