# Focused schema acceptance

Project Planning accepts the focused infracfg binding and the two named MT6797
DTB checks from [schema attempt 2](SCHEMA_ATTEMPT_2.md), published at
`3f855c8d89df59465a31553f96789515c37ce6ed`. This is the integrator's separate
review decision. The original collector result remains
`COLLECTED_REVIEW_REQUIRED`, its accompanying worker review remains historical,
and the first schema/QEMU refusals remain unchanged.

## Exact evidence

The execution revision is `f4ff1028e883c63e980c61f6bb076d99b97454ac`, using
the retained `4ec63076` source/build and pinned schema environment. The
[evidence inventory](results/schema-attempt-2-f4ff1028/inventory.json) has
SHA-256 `14dd295d362356cd220eab49f6a2684ec6512cede88c566c79ea076ba80fa9ba`;
the original collector receipt has SHA-256
`c08e721c7cc0443f33f2e39694da2c5d4f6634dd9399b6f9a1e4b5c837d6fdcf`.

Independent review checked every one of the 19 published paths, all 15
inventory hashes and all 12 embedded command-log hashes. The coordinator also
verified the complete inventory locally. All six commands use the exact
contract arguments and ceilings, exit zero within their budgets, retain empty
stderr, and leave no process-group survivor or TERM/KILL cleanup. All thirteen
Linux fixtures passed before the admitted window.

Both full source-integrity checks returned the pinned digest. All eleven
protected source files and nine protected build files match their contract
before and after, including configuration, release, kernel image, production
and test objects, and both DTBs. No source repair or kernel/package replacement
was needed.

## Diagnostic and coverage review

The complete binding output records the filtered document, lint, style and
example checks with no diagnostic. Independent review inspected all 450 lines
and 202,483 bytes of DTB output, grouping only repeated known path/target
substitutions into 42 line forms; none was an unclassified diagnostic.
It confirmed 105 DTC recipe markers and 118 unique filtered validation
invocations. Since those recipes retain `|| true`, exit status alone was not
the acceptance basis.

Each separate direct validator emitted exactly the expected `Check:` line
for `mt6797-evb.dtb` or `mt6797-x20-dev.dtb`, with empty stderr. Both inspected
DTBs contain the unique matching `syscon@10001000` node and one reset argument
cell. The processed schema includes the selected binding and compatible and
is bound to SHA-256
`a3265d87a3617c19c3463fb3a728df2120b8932ee0be686dcd8c4f69fac82b38`.
Its reported 28,551,455 bytes fit the unchanged 128 MiB allowance; the generated
schema stays on Buildbox.

Acceptance covers `clock/mediatek,infracfg.yaml` and these two exact DTBs on
the retained source/configuration. The other filtered recipe invocations do
not establish an all-bindings pass. This evidence does not establish provider
MMIO behavior, new Gemini hardware support, final target-tree compatibility,
actual authorship or truthful DCO certification. Any changed topic inputs
require the relevant checks again. No further execution is selected here.
