# Evidence freeze protocol

Identity: `wlan-drv-init-lifecycle-evidence-v1`. Declared before retrieval.
The complete drv_init/Makefile is the sole first-batch source. Its exact
identity and demonstrated object selection must be frozen before the second
batch. No source body or excerpt will be stored on disk.

Before verifier construction, record independent canonical digests here and as
literal verifier constants for complete source tuples, exact citation anchors
and immutable request evidence (including declarations, receipts, failures and
no-hits). Use sorted-key, ASCII-escaped, compact JSON encoded as UTF-8 without
newline; sort source tuples by source_id. Never derive expected values from
mutable evidence at verifier startup. Inherited tuples compare field-for-field
to independently pinned predecessor evidence. Final identities are pending.

## Mandatory first-input selection freeze

The complete 22-line, 590-byte drv_init/Makefile has Git blob identity
`bb84384b9a24f2a083a6caad9411765b75ee1047` and SHA-256
`5743b4c9764738ff5dd36bce2a8233434f4724e15145573b46ef5ceedcccd6ac`.
For CONFIG_MTK_COMBO=y and chip CONSYS_6797 it defines MTK_WCN_WLAN_GEN3 and
lists conn_drv_init.o, common_drv_init.o and wlan_drv_init.o as built-in objects,
alongside three out-of-scope component objects. These three demonstrated
lifecycle sources, not a filename-based guess, form the next body selection.
The exact object list/order and the separate literal ANT-line limitation are
recorded in search.json; object-list order is not runtime initialization order.

## Final independent freeze, before verifier construction

No more source request is allowed under this item. Expected values below are
fixed independently before verifier implementation, not derived from mutable
evidence at verifier startup.

| Canonical object | SHA-256 |
| --- | --- |
| All 10 source tuples, sorted by source_id | `071f5eea45e49947ff3dce0c68d60f5aa0d9d26f84822da0829758a96105fd65` |
| All 18 exact citation anchors | `f39c0cdd3eaf7e88cb6ea4e58487a45f230710373fdf5eacabbaf283e50f437c` |
| Complete immutable search.json object | `3c44201852f69b65b5fabcc2dc993888e334cfdc928fbedab79757f88cc3b745` |

Whole-file SHA-256 identities at declaration:

- inputs.json: `3e2b5c20a08cfd54d42a43587825aa65512cf012bb8b0b572a86e70cb5d4ef2b`.
- verdicts.json: `618af79a8edc68e733efe37440d4714fe30853663c8e8c19957d869179b3a171`.
- search.json: `c3097344aa612bdf14be3f9b75c946f65a36b813f8222fa09b99450d9ddae1bc`.

The request freeze includes budgets, predeclared batches, exact receipts,
clock samples/timestamps, object-selection freeze, all four no-hit records,
counts and stop boundary. Six inherited source tuples must additionally match
the predecessor inputs field-for-field, independently pinned at SHA-256
`c5e123769535553523f70ce0ad3bb15343bf6dfb9637d064059a896f43c5ae66`.
Changes require an explicit reviewed replacement freeze, not a regenerated
expected constant merely to make a failing test pass. This freeze records
evidence identity, not runtime, resource, firmware, radio or reuse authority.
