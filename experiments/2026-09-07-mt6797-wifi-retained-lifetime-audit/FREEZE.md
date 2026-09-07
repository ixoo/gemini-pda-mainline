# Independent-review freeze

Parent: `2af9532b3b1c1850cfa071a0f279154127a04db1`.

The reviewer must inspect semantics separately from receipt integrity.
The assert-free verifier pins these exact JSON bytes and all 15 input files:

| Record | SHA-256 |
| --- | --- |
| inputs.json | `32ac9645738278127ea0cc033a665476cc022fa313e2813d05a45bd8e0eed2c4` |
| inventory.json | `5fa2662168923535e4a82ca80c2801c18d65aeb6d99152558231ac29a2ac0d77` |
| evidence-matrix.json | `ba88273115fdd967d084c8a91a6ac75e4fd0dd44a035607ecad69a9f2f1aad4b` |

Every JSON leaf is mutated in memory, including evidence classes, predicate
identity/verdict, null cycle/success joins, limits, bounds and effects.
Top-level omissions and same-size mutations of every external input are also
required to refuse. No original input is edited by those tests.

Changing a frozen receipt or verifier requires renewed independent review.
This file and the verifier are review anchors, not an external signature or
an oracle that can establish the truth of the underlying observations.
