# Source-wiring integration review

Project Planning reviewed the additive topic history from `2891e041` through
`e1bfec0ed7004ba0e2f4a3eaa4894992c2e9b0d5`, integrating against `82bd2563`.
This includes the original source contract, profile-preservation oracle,
maintainer routing, acquisition evidence and production source-selection work.
Historical receipts retain their original revisions and limits.

## Corrective review

Independent production review found one archive-containment defect in
`e3f0304d`: normalizing `sub/../outside` before checking link ancestors could
hide a symlink traversal outside the source root. The correction at `e1bfec0e`
checks components against the complete member inventory before normalization
can discard them. Inspection and hard-link extraction share that check.

Independent re-review verified that the original accepts the counterexample in
both member orders and the correction rejects both. All seven archive fixture
groups pass. Additional cases reject hidden hard-link traversal in both orders
and both compression formats; valid hard links preceding their targets still
extract successfully. No additional concrete defect was found in the resolver,
legacy package acceptance, complete override provenance, cache identity or
preparation cleanup. The reviewer used only managed temporary fixtures.

## Preserved inputs and admission boundary

The integration adds no manifest profile and changes no kernel, DT, configuration
or patch-series input. The supplied oracle reports all 189 existing profile
inputs preserved and no added profiles. The canonical V4 selection is untouched.
The [profile and source admission contract](SOURCE_INTEGRATION.md) still governs
the later canonical-series freeze and upstream topic selection.

Production tooling now resolves complete profile sources and validates extraction
and package provenance. This does not establish that the upstream reset topic
has compiled, passed KUnit/schema checks, or become submission-ready. No device
candidate, physical readiness or support claim changes. The existing
[Linux receipt](results/source-wiring-linux.json) covers its exact earlier source;
the traversal correction and integration are recorded separately.

## Integration validation

The common publication gate passed for all 27 changed files, including shell
syntax/ShellCheck, Python syntax, local links and bounded sensitive-data checks.
Its production source/archive/builder suites passed 7, 7 and 4 groups respectively;
the original experiment source contract passed 15 groups and the acquisition
scanner passed 5. The separate input oracle preserved all 189 baseline profiles.

The worker also reported corrected revision `e1bfec0e` passing 7 archive and 4
actual-builder groups on Linux. The retained snapshot still matches its published
digest and all 102,310 members pass the corrected inventory without extraction.
Linux package validation at integration remains a CI gate. No kernel build,
KUnit/schema execution, source extraction or device test was performed by this
integration. Durable build documentation now describes the complete source tuple,
cache identity and provenance rules; kernel profile admission remains separate.
