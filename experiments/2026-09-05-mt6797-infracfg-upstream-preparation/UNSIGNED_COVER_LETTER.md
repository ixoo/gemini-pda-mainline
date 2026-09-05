# Unsigned cover text — not sent

Draft subject: [RFC PATCH 0/6] clk: mediatek: MT6797 infracfg reset bounds and provider

This topic adds SET/CLEAR reset support to MT6797's existing infracfg clock
provider and validates reset translation before indexing the register bank
array. The public namespace exposes only thermal reset ID 0 and PMIC-wrapper
reset ID 1, mapped to SET/CLEAR pairs 0x120/0x124 and 0x140/0x144. Other reset
lines, TOPRGU, consumer wiring and power policy remain outside this topic.

The six review patches separate generic bounds protection, generic KUnit tests,
reset definitions, MT6797 provider integration, MT6797 descriptor tests and the
SoC DTS declaration. The existing reviewed binding patch makes reset cells
mandatory; the readiness review proposes dropping that requirement so old
MT6797 DT descriptions remain accepted. That proposal has not yet regenerated
the reviewed series.

The current six-patch revision builds against upstream commit
4d7d9486c04d917265f64c55bd23b2cc4fe7749c. Its emulator log reports all eight
intended test cases passing, but the original strict two-suite gate refused the
additional upstream refcount interrupt suite. The second bounded schema
collection completed with empty diagnostics and unchanged protected inputs.
Those receipts describe the current revision, not a future binding correction
or rebase. Physical mapping evidence comes from different local integrated
kernels; no hardware-tested trailer is asserted for this topic.

There is a direct overlap with Akari Tsuyukusa's August 3 MT6797 common
probe/remove conversion, which removes the private probe used by our provider
patch. Please advise the intended ordering. If that conversion goes first, the
reset descriptor can use the common helper's existing reset hook after a fresh
review of registration order and failure cleanup. In the inspected common
helper, reset-registration failure lacks removal of the already published clock
provider before clock data is freed; that path needs correction and focused
fault-injection coverage before adopting the hook. The standard reset-cell DTS
declaration has no new-header compile dependency and can follow the agreed
MediaTek route independently.

This text has no sender, author certification or sign-off. Before sending,
resolve the exact final source base, regenerate the compatibility correction,
review the resulting tests/evidence, and obtain truthful author/DCO decisions
as recorded in the submission readiness packet.
