# Frozen provisional metadata and scope escalation

Frozen before verifier construction, after the 2026-09-06T23:37:40Z stop.

review_ready_utc = 2026-09-06T23:41:14Z

| Record | SHA-256 |
| --- | --- |
| inputs.json | `cc93d3e9627e31a60d66ebcea8211104a47663313b0015a5390612624f50bf4b` |
| analysis.json | `18c4bf0b55a4cd00450b1eead755edf610e4050612191a3b7fdca968c4b36c12` |
| intervals.json | `30ab9bb53bff6c144ba75b390220f0c036e9cbe8730d2fcb7c562955a659f23d` |
| Private parser log | `4a2361f8b2a0304792b3c2f52cbdad2d62a30a3fcffce00a43045622f345cd2f` |
| Private bounded metadata | `916e6800f236ddfb4741eb35fbc12575aabc9321004dcc82a2647446b2388a9e` |

The frozen inputs include all original kernel/tool hashes, all four predecessor
hashes and both analysis/dispatch repository identities. The analysis freezes
source-field transformations and the discovered internal classification call.
The interval record freezes exactly four targets, each alias inventory and one
distinct predecessor/successor, with all admission flags false.

The verifier must reject promotion even when numeric interval conditions pass.
No future instruction-analysis permission or exact function extent follows.
