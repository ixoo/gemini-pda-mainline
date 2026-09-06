# Evidence freeze protocol

Freeze identity: `wlan-builtin-lifecycle-evidence-v1`.

Declared before source reads: each fetch batch is written to search.json before
its requests. Clock samples are explicitly taken before that write, not guessed
freeze timestamps. All successes, failures and no-hit selections are counted.

Before verifier construction, the final complete source identity tuples and
exact source/line/symbol citation map will receive canonical SHA-256 identities
recorded here and as independent constants in the verifier. Canonical JSON uses
sorted keys, compact separators, ASCII escaping and UTF-8 with no newline;
source tuples are sorted by source_id. Expected values must never be generated
from mutable evidence at verifier startup. Reused tuples additionally compare
field-for-field to the independently pinned predecessor inputs.

## Final evidence freeze, before verifier construction

The three batches are complete. The following final identities freeze existing
evidence before implementing its verifier; they are not acceptance or runtime
claims and are never generated as expected values at verifier startup.

| Frozen object | Canonical SHA-256 |
| --- | --- |
| All 22 source identity tuples, sorted by source_id | `6bd252d81c02cbf7c87c14b160cbb6fd07d08f4858a6f749373e60901af0f8e1` |
| All 36 exact citation anchors | `ab5ce53493e19f0326cabd9f13d5f330f5ecb6c918228ab61659df1c4e6f6220` |

The corresponding whole-file SHA-256 values at this declaration are:

- [inputs.json](inputs.json):
  `c5e123769535553523f70ce0ad3bb15343bf6dfb9637d064059a896f43c5ae66`.
- [verdicts.json](verdicts.json):
  `9e8d702855374f7ed6d0c13d38b2168c238968442bec882470b6a443c3aad0eb`.

Ten source tuples are inherited field-for-field from predecessor inputs at
SHA-256 `67b821b2f67c719c25b6ff10c41c9946b339e4cbead8e83dd28b90ca50377944`;
twelve are newly fetched regular files. Failed paths are receipts, not source
tuples. The second read of platform.c adds only the previously unread bus data
initializer and must preserve its original whole-file identity. Inherited
include/table and driver-initializer context was already fetched by the prior
audit; no new request or contextual function-body reread was used.

Any evidence change requires an explicit reviewed replacement freeze, not
mechanically adjusting expected constants to make tests pass. The final
verifier checks exact tuples/anchors in addition to record cross-consistency.

## First-review request-evidence extension

Freeze identity: `wlan-builtin-lifecycle-request-evidence-v1`, declared before
the bounded repair to the verifier. Existing source tuples and citation anchors
remain unchanged. This extension freezes the canonical object containing the
search.json keys `budgets`, `batches`, `requests`, `contextual_rereads`,
`inherited_contexts`, `counts` and `no_hits`, using the same encoding above.
It includes every raw/contents receipt URL, response hash and byte count,
all exact directory entries, failures, timestamps, allowlists and no-hit records.

- Immutable request-evidence SHA-256:
  `243404485bfabccdb140a5b00cca58fa7ce11d9f285255939c03e610145257c0`.
- Whole search.json SHA-256 at this declaration:
  `f744eb95aa2f181da5ab2e942b6d8c9b75cf1810a062056cdf9e27484804f8f9`.

The verifier uses an independent constant, not an expected digest generated from
mutable records. No new source read or evidence change accompanies this freeze.
The original whole verdict-file identity above is historical: the authorized
first-review repair qualifies its next discriminator without changing its
semantic verdicts, state model or citation anchors.
