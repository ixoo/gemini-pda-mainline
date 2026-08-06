# Experiment: A72 provider release refusal boundary

## Record

| Field | Value |
| --- | --- |
| ID | 2026-08-06-a72-provider-release-boundary |
| Status | source-complete; Buildbox pending |
| Subsystem | MT6797 A72 provider-owner lifecycle |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Claim | PARTIAL_PROVIDER_RELEASE_REFUSAL |

## Question

Can the private provider registry require a paired release callback and
classify the current DA921x provider's refusal without inferring a rollback
owner from the read-only I2C transcript?

## Result so far

Patch 0173 adds a paired provider release callback and a registry entry point.
The legacy provider registers the callback only with the existing explicit
provider-owner profile and returns a structured -EOPNOTSUPP. No register
data is written and no inverse operation is claimed.

The source review deliberately stops here because the repository has not yet
proved DA921x page ownership/selector semantics or a write/readback/rollback
transaction. The existing direct-address reads are not sufficient evidence for
an arbitrary write.

## Provenance

- Patch: [0173](../../patches/v7.1.3/0173-arm64-add-provider-release-refusal-boundary.patch)
- Series: [canonical series](../../patches/series)
- Profile: a72-p24-provider-owner-refusal
- Device action: none
- Boot candidate: none

## Evidence contract

- the registry rejects an owner that does not provide both callbacks;
- acquire remains the existing structured pre-vote refusal;
- release returns a structured refusal before any write;
- no regulator consumer, CPU_ON path, or hardware action is introduced.

## Follow-up

The next gate is not a device boot. It is a source-only page/ownership review
that must identify the exact owner, page state, write transport, readback
fields, and inverse decision for one bounded BUCKB operation. Until that review
closes, the provider remains read-only.
