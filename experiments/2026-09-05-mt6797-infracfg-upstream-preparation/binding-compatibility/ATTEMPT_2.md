# Compatibility attempt 2: decoder diagnostic refusal

The single newly admitted run at main
`b522e5e71d9346924ff3992f278f1705f72819b8` stopped **REFUSED** after 30.007
seconds with outer exit 1. It used the reviewed warning-chain correction and
unchanged inputs/budgets. There was no automatic repeat. Attempt 1 is unchanged.

Both binding meta-schema checks and processing commands passed; all 25 dtc
commands completed under their guards. The comparison child returned zero and
emitted 50 structured rows, but also emitted four unlabelled decoder diagnostics:
`#reset-cells: size (2) error for type uint32` and the equivalent size-1 message,
each twice. [Exact stderr](results/attempt-2-b522e5e7/compare.stderr) has SHA-256
`fc95e32cb76dce3832e66cd3c6ee1b088a6f26810eb385deca692b2ef7120c37`.
They do not identify the individual fixture or variant. The parent refused
before classifying rows or running the full post-source scan.

[The complete child output](results/attempt-2-b522e5e7/compare.stdout), SHA-256
`3853dbc027ea0d4633aaa954f34f3957904d9443b162a1bfeab2273a0cc5082c`,
also reveals two distinct issues requiring review:

- The malformed `mt6797-byte` node reports no schema errors and validity true
  in both variants, against the required rejection. Whitelisting stderr alone
  cannot make the reviewed expectation matrix pass. Decoder representation and
  raw property width need investigation; no silent acceptance relaxation is made.
- Mandatory `mt6797-unknown-property` reports both an additional-property error
  and missing required reset cells. Both pertain to the supplied fixture, but
  the classifier currently permits only additionalProperties for this case.
  The optional form reports just the additional-property error. The overall
  invalid outcome is expected in both; diagnostic-set attribution needs review.

The child reports old MT6797 omission rejected under mandatory and accepted
under optional, while the new explicit-one case is accepted in both. These
are retained observations within a refused run, not a completed compatibility
gate. [Offline review](results/attempt-2-b522e5e7/offline-review.json) checked all
50 unique row identities and their 25 recorded DTB digests; only the two byte-case
validity booleans differ from the expected matrix. It does not override the
parent refusal or establish complete negative-case attribution.

[The immutable result](results/attempt-2-b522e5e7/result.json) has SHA-256
`9de53cfdc44ecb305459cf690599617f85916717c945eae5856f8bf3521d62d5`.
All 32 commands returned zero within their individual budgets; no TERM/KILL,
timeout, capture limit or surviving child group occurred. The parent failed
its nonempty-stderr check. [Execution](results/attempt-2-b522e5e7/execution.json)
records the unchanged 1000-second outer ceiling and five-second kill grace.
[Fetch review](results/attempt-2-b522e5e7/fetch-review.json) records exactly 65
original regular receipt/log files, 62,128 bytes total, all hashes checked.
Each was below 256 KiB and the total below 1 MiB. No source, DTB or processed
schema was copied to the host.

Full pre-source integrity passed. Final checks confirmed all 11 source/9 build
pins, original processed-schema hash and tool identities; these are limited
failure-path checks, not a full post-tree scan. Scratch was removed, its ownership
marker retained, the exact project checkout remained clean, and the normal
lock was independently reacquired/released. The backend window is released.
No kernel build, source extraction, tool installation, QEMU or device action
occurred. No third run or protocol relaxation is admitted by this result.

## Integration review

Project Planning independently verified the 65 original member hashes/sizes,
all 32 command outcomes/log digests and all 50 unique row identities/recorded
DTB hashes. Both byte-case decoded-schema acceptances and the four decoder
diagnostics are present in the retained output. The refused classification
remains unchanged. Final backend preservation/cleanup was reviewed from the
worker's records, not repeated; no full post-tree verification is claimed.
