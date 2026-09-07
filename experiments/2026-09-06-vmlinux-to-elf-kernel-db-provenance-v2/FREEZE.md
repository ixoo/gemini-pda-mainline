# Frozen database-provenance evidence

Frozen before verifier construction at 2026-09-07T00:23:37Z.

review_ready_utc = 2026-09-07T00:26:45Z

| Record | SHA-256 |
| --- | --- |
| inputs.json | `bb64c330fca2c2b3d48742d7897944d64a0f547d76d95ebc3e823f59411a914e` |
| inventory.json | `1f8da3d3ecb20a5c36e8a7deade2b12adeb4994793e2c46ce6daf9bf430862a3` |
| analysis.json | `deb75e89391a4e8c84e16d517975cea6dea3e73963c4e4e4c7be20a5fd2e44fa` |
| Private inventory-before log | `de8e546c5f1b26b2864077566e456c8608758ed4187b2b6cde8011db0afa2d5b` |
| Private immutable SQLite audit | `77766fe6d9966013f44113b163cf66eea3de465aae7d0902ae23e2ad57666125` |

Inputs freeze the repository/predecessor/distribution tuple. The inventory
freezes the exact four-entry partition, source/data identities and verified
unchanged state. The analysis freezes source/model/query semantics, bounded
schema/counts, source-forcing requirements and conditional eligibility only.
No fixed digest may be replaced by a record's self-reported expected hash.

The excluded generated cache contributes its name and absent RECORD fields
only. It contributes no hash, size, contents, execution or evidence identity.
