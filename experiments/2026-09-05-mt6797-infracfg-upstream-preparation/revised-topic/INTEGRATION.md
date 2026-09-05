# Accepted revised reset application series

The coordinator accepted [attempt 2](ATTEMPT_2.md) after independently checking
all 77 command outcomes and log hashes, six patch hashes, all eleven expected
source hashes, retained-input equality and exact full-tree replay. The original
collection result remains unchanged; this is the separate integration decision.

The new `mt6797-infracfg-revised-kunit` profile selects the header-only patch 3
and the five unchanged historical payloads in canonical order. It retains the
exact upstream archive/commit, allnoconfig base and configuration fragment.
Historical patches, series and profile remain available with their original
evidence. The default profile is unchanged.

The new profile has not been compiled under its new name or tested on hardware.
Its C, headers, DTS and configuration are identical to the previously tested
topic; the removed mandatory-schema delta is covered by the accepted focused
compatibility comparison. Full source comparison and replay establish this
limited reuse of evidence. No redundant kernel build or device boot was run
for the application-series integration.

Actual authorship and DCO certification, final maintainer routing and overlap
review remain submission requirements. Checkpatch's generic readiness wording
is not certification. No upstream submission has been sent.
