#!/usr/bin/env python3
"""Validate the frozen source-only A72 membership/admission contract."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections.abc import Iterable
from pathlib import Path


sys.dont_write_bytecode = True
EXPERIMENT = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
RESULTS = EXPERIMENT / "results"
PHASE = RESULTS / "phase-contract.tsv"
MEMBERSHIP = RESULTS / "membership-contract.tsv"
PROVIDER = RESULTS / "provider-contract.tsv"
ADMISSION = RESULTS / "admission-lock-contract.tsv"
README = EXPERIMENT / "README.md"
DESIGN = EXPERIMENT / "DESIGN.md"
TRANSCRIPT = RESULTS / "contract-validation-20260805.txt"
EXPECTED_NEGATIVE_MUTATIONS = 262

PHASE_FIELDS = (
    "id", "phase_from", "event", "phase_to", "token_rule", "members_rule",
    "provider_rule", "allowed_effect", "failure_route",
)
MEMBERSHIP_FIELDS = (
    "id", "operation", "pre_members", "target", "commit_gate",
    "post_members", "pre_provider", "provider_sequence",
    "private_big_on_rule", "independent_proofs", "query_rule",
    "failure_rule", "implementation_state",
)
PROVIDER_FIELDS = (
    "id", "from_state", "event", "to_state", "required_context", "proof",
    "failure_state", "member_commit", "implementation_state",
)
ADMISSION_FIELDS = (
    "id", "kind", "boundary", "owner", "required_context", "rule",
    "ordering", "lock_rule", "evidence", "failure", "implementation_state",
)

PHASE_IDS = tuple(f"P{number:02d}" for number in range(1, 33))
MEMBERSHIP_IDS = tuple(f"M{number:02d}" for number in range(1, 5))
PROVIDER_IDS = tuple(f"R{number:02d}" for number in range(1, 9))
ADMISSION_IDS = tuple(f"A{number:02d}" for number in range(1, 41))
LOCK_IDS = tuple(f"L{number:02d}" for number in range(1, 12))
ALL_PHASES = {
    "IDLE", "FROZEN", "ON_ISSUED", "OFF_COMMITTED", "QUERY_INFLIGHT",
    "OFF_PROVEN", "VERIFYING", "REJECTED", "FAULT", "CONSUMED",
}
PROVIDER_STATES = {
    "NONE", "ACQUIRE_INFLIGHT", "HELD", "RELEASE_INFLIGHT", "FAULT_UNKNOWN",
}

EXPECTED_PHASE_ROW_SHA256 = {
    "P01": "e33be2860eacbf6c903caf0833172d498b0390a7c380c4c69bfe8ce14fef0f47",
    "P02": "d7710ccf7351ea262c3dfcd71b8fe71c398db65f3692188736cf8aea73bd7ada",
    "P03": "d3efbc5ad6a8f3840b2f651c37770f63422076a87f0572486ce48114b3f31b0b",
    "P04": "9a923a85380b6ad49001b921b21e2aa5234e9123d13c9d2aca33c1fcd88fec1e",
    "P05": "e1f6206962d0638953036425fe355a6a64497056548af860f25af81ae4b29ad2",
    "P06": "b81e044cbdc0b90d22abe4a9e1ae59cac44f615ea7b9704f68675752e3c14ae0",
    "P07": "9f3c86f890af07a44b4a4a3d41362a195451f5ca9ed5166faf49943c0a8905d6",
    "P08": "2f3bf4eff244214889e8b2ff97b2f8a26556daeb20a1a8844311311a2c4f4f10",
    "P09": "c0bad222d3adf5a9b8b1766e4872e4482f065cddf596d56d883c975fc9683ee4",
    "P10": "56d3aaf47de24696291a9163ed091729a7f36d7f85825657a244f99d38704a52",
    "P11": "0a36eb06b82d0c30b5a640269e60920adbd33e5b0511fb809d61d9474493d703",
    "P12": "a1788532c55ae6b08e77d56a0978d81bb0be21737ea9d89af6b54e55d7dd181c",
    "P13": "b77e9163f763287e019dc87d832afaf3d1ed5bf57b47f6a76cd96c3f3bc94f88",
    "P14": "a9ae9e0ce70d380ab7425881a5fbdcc3f004d23190d7b7cfa8b8d24d0d42c0d4",
    "P15": "fb642cf23dd216d044cf346ff40d8797ea9d52424df1269ad43f23c1f900b76b",
    "P16": "6da84f0af5bc11b9ea3d3f2275272e20b0ec4f4a903c2b99f4bd2e0bafcb7a1f",
    "P17": "f75763a238f136f0ace9617350aab72dd8db1c8ab6939add14e828fcfc3b8a83",
    "P18": "0d1d1900b9317e5430a6abe93312bc0546858925dd32cc8c75115bf2d355f9ad",
    "P19": "3ce854ddf981e0bf33a1badbd97b5e5222e3ba8980e49eaf3bc8161d2a60f8af",
    "P20": "e599d7180f8ebb02859e90e22ed5ea98a5f75bf98c48b20a56bb6276ca2bb4ab",
    "P21": "56deb50be43792526faa1ebbbb3e7d0296b2ef5579848e0786abb24fd7eeae12",
    "P22": "ca88bd2d32126e78d3eba1c586c278162eec86cebc5a02458b9afec13118fe4e",
    "P23": "9e95aa73b6510c41be53429608f754076ea1231cdfb3e5d686a9c12db6a6c00c",
    "P24": "75bf24a0f351571784a2da24c71f3e6eef65760813b1678212ef9b915b24c1c8",
    "P25": "52a2631498bf44104655085913ea8325f5b8aaeda0aa13517c2384a3ee066691",
    "P26": "9b7e8a584adc447a8fb51c84c81f165ea0b114d147d2bf8ab88d4f5daf5567e1",
    "P27": "fc1f1c06f5f9ed2523eef74aa1fb529b0642e04089537f0686a15be224742e3c",
    "P28": "0f1ca633b917158ec8a66b57b0c2d96f0ea44e638f2136b2eb8e3c3b5d08ef8f",
    "P29": "75b280d3ec2e0e99e0d8f4b3861616d0a31958c276526872ed4bfc1ea46074c2",
    "P30": "d1ad30a9b8e4dda4bc1eec840cea9623c3b51bee4ca1d10984d05cbd196314f7",
    "P31": "d3bd0f989fd67c223de02ab217fa4240ef6386c5427e7c0a709ab7d72c7ab92e",
    "P32": "2ce47b825f54553e23232f08f7d38a938a4b9e537a87f6ea09e30e5f3d78e426",
}
EXPECTED_MEMBERSHIP_ROW_SHA256 = {
    "M01": "eaaa11b4e02468412420ac1e49c90573b7873b53ac1cd86090a8ef1643e00fda",
    "M02": "1404f4768ac73526b1d815aebf60c8c79d8604147a69c573a6d9462ee49ce453",
    "M03": "2798679e8e942b23a2e50980c3e6f79e3a877da5d2ee9068d1b47dd232798ac2",
    "M04": "fe13aee234cba70eb28bf85e569129e413bf474d412a23f7e9068bdbf3111adc",
}
EXPECTED_PROVIDER_ROW_SHA256 = {
    "R01": "695ae0371362ee62c9e7c40182c6c689fea3f9022a3c6a807c987a21a559ff66",
    "R02": "22e96161fcaeeccf0cda75685df2d3a677ea3493e2fbced13ec9ca67429840c1",
    "R03": "bd158d4f8ccdb3fbb314a723c1f151f3ee15f79837027b8ef71c174ccdc8d3ba",
    "R04": "691a1a90c28666f1c446176d50521bce2080426b87848ed5a08fa57b5c775423",
    "R05": "4259369cb445342da13fe5b16ff8ca7201b338faf8563b2041f06dcd574cad2a",
    "R06": "ccf1f0892f027520c94f053797db2aaa27c676e74466f3c89822d228a4d7c240",
    "R07": "a91ae93a3ddda29e3efa0970ef1abfab841038e99c072dc02bd83f3bb68c9297",
    "R08": "a8c8cb4109b2b977f15cdf9acfe93ab56f44ada20e33dd860dd12faede74d256",
}
EXPECTED_ADMISSION_ROW_SHA256 = {
    "A01": "8b997f13df6ee927ac9ae6f0a78fed2a5b61c23bdee5cdef0ecde5694f378673",
    "A02": "d470f17df90671ed5f0a26b97fbdb9075a4e35e931fef02f4b2f0126e30fa502",
    "A03": "1bcfbc7b40238baa787896d2b7f491bb6333c19c666dab52d4226f7e6ba2f8a0",
    "A04": "60fd200c7929808ba43b90de5e366bf60275c8284b1a9a01cca1f5d74dce052d",
    "A05": "2d962a45d7ac3ca0bdc2753c1417b3b5ee6ff433dcb59aa80e7b58cb49a2fab8",
    "A06": "5df904c0d93531358fc6c47892da53dd74705714d0385ad734840774dfe75374",
    "A07": "4c8e3f355b9cfc54e1404df9ed049cb90b79b1e52f9e043f73fedfada4654a41",
    "A08": "c2ec97ad733741fc8804cd0a27ff57c5ff8ac0cf22539467af2971c56789687e",
    "A09": "eb2b986e2ba873be0107738fc2e752aee194b022ecfba80e43638621f6365332",
    "A10": "9f5559cafaec91ac9b233172aa7be89f1452bf965f50fea9297e4e872095cbd8",
    "A11": "e65d35592602044a9e8a57f015888707a8d1d2804fecbfe09c77cbc0a5d54a41",
    "A12": "3ba15c01849292e2779c24424c3002e640c3fdf965a26a37d0991aaef5015f7f",
    "A13": "24f174bcaa73ccd397580431fc677bc10afa88a662d8a631b93c3daa16a58b3e",
    "A14": "e293b569edb9945594222e45edb4b876097ee55cdb3de7a2b7633d085a4f5300",
    "A15": "bfd8cd0e2ba9fccd0a5b832af005d4828b479046c38c1445f47609654e03dd76",
    "A16": "30e96e59f940e8930a8a8a7ab1696ac9bf0b743bd9f01049ccd31ee27e9487fa",
    "A17": "992226cff8d5209144b803bd19056da6830f2bac835afe55492ae0e36939623f",
    "A18": "0052827f86e2826dec896733a94b6dd311730a0d12a15f0b002a96f9328e2de9",
    "A19": "c470d6c28a668db55f5e50ceddc9b26ac5c03f923f46ce16bb0ea08add0204fc",
    "A20": "75559c1c237ce69b7879428874f2a8528f0cd4d819d3f93ebb9049ea323f909a",
    "A21": "66f53a421d0c6f910cef498710e1927998bd495f304cd12a1ad2d05b4f6ff5fa",
    "A22": "d163239fb4c8c84becf88718d88d015af7deda8a70bf8aad62a236300a8b45b1",
    "A23": "d50277654fd5d59b4d57da2fbce9eaf5c966fc64a45d350dd7d99c9f2223fbab",
    "A24": "48951f8287966a1b92f00c7237d74f9fd4739a3d139524ffd600933681b8014f",
    "A25": "e9be06d546f218ec8035ecc5aae7457355fac51bd415e68cc275109b298814c1",
    "A26": "d32ffbbd34469b6da54f9e82e84a27e23af9908b5ed5b8f29521d0267b173479",
    "A27": "9dc416421f5aed1b8a825035a10ee020a6219d099fd337db785a241a090660d3",
    "A28": "46619e8bfc281945921fc94485c1a9ab70b55da5a0bafc1b159811899a589063",
    "A29": "b2ca861fbc630290c9980fe23bad3288782eece2fc1f11d9b2378735180e3bef",
    "A30": "7c39582c0ca5a025f189e48a1c6935b70860c29ceee5809c5d69b272d03ff937",
    "A31": "c12644d4bae1f7359ad051e49492856ec4677e0ff4eee127f9ee553fd1b55fc1",
    "A32": "5a95d3095ae5d1c6f5c1139e58fa1366edbcd0138b668a998be480bb9140b1c7",
    "A33": "f124a5b8cf0f46d038f5cb39bafd84d43c32687e6ce8cc76466e8bfbeb92553f",
    "A34": "2edd2557d8066bf9979962b53c306a8d37584d8a912732e785677a602c049881",
    "A35": "aa2f7516dfadca19ff3c1139654e8f11a09f8c79e2de282318e345b036556159",
    "A36": "324931e7ff8442f41fa7d1a253b22eb94541fc5700d510c9af03490836b0c68a",
    "A37": "b60bb41bd2a2097205b9b783f0014039c65726a0d9f3bf7581d98309f3682834",
    "A38": "7f7ca89119e0f6f70dbc9e0ac67b2e20a5c569e9f7d0149a7d18675563e9651c",
    "A39": "e775291f4f7a0d95a9b4b329e34de66f988aba71d729d97b536b8ab0a5e35842",
    "A40": "3634f99901c7409ecbfc6486077f967885706e9d281637d5fb8987199b746d70",
    "L01": "c30f19e707b43d90611cf4a1bce2324d8538a291a38abb71f74c8cfa043dc67b",
    "L02": "023c2da6972d78c0643048b9a03692a84b00f17ce97b6051d1a334f8b2c3c0d0",
    "L03": "c1669b957200b6b0f8840aa19b6ccb260a9d1fde33477ba1d5dd5afd670ad6c1",
    "L04": "ad85eb06586c9d77b1abd2af35bf89fc9fbc6e6844bfa88280fbff4271c02e36",
    "L05": "515408678fb773bfe8cbd749ea6cb3d971e437ef13948284602fd3e1c3be6b07",
    "L06": "2c4a485c394abffc8eeacf6f5f75b32f18b65d486954e780f06ec4d5e3339962",
    "L07": "70266fb1a1949efab266b68d40f83b9ec16075707eb0f50f17e2743936654b3a",
    "L08": "72f7483d67240fc641ae37618a3709129c6b2e14051a3fdba1ae8036b1ae51a7",
    "L09": "c0c33d46ea5a94f21b86a86c1da20d079af90afa7c2eb278673e1cbe69d1eaf5",
    "L10": "3a866f583e1f0f5ea48d56d6ad3135a4a758af51773ec97d5daae457c268c90c",
    "L11": "883514538563b77d3737ed58983633c501936fd6a20847c8ceb1f16b3c2a5eaa",
}

EVIDENCE_SHA256 = {
    "experiments/2026-08-05-a72-membership-admission-contract/results/source-order-audit-20260805.txt":
        "2344676ee4fc5b889eba4d40aad1a00e1c5266935ee9a887ad8624b763f1077d",
    "experiments/2026-08-05-a72-secure-cpu-off-attribution/results/callgraph.tsv":
        "0007ba7868cbd68bb2a4ef6ad66240c7e00715e08934ca5d05ca482dfd464354",
    "experiments/2026-08-05-a72-secure-cpu-off-attribution/results/effect-inventory.tsv":
        "deaa6686582e6e3f2e3453ff626f14b2ec555d9be468ac2f67fb350e6eead8bc",
    "experiments/2026-08-05-a72-secure-cpu-off-attribution/results/audit-validation-20260805.txt":
        "6da8ad1883362b32fe7b8e2332f262ec8ebf195db09c91872a0ce59eda429af6",
    "experiments/2026-08-05-a72-safe-off-ownership-contract/results/safe-off-contract.tsv":
        "8451fbc2910a0d4776efe2d51b84f0bcb3e95ac77310ff425c506bbb59d6af26",
    "experiments/2026-08-05-a72-safe-off-ownership-contract/results/evidence-reconciliation.tsv":
        "6ee968f2f1286393d9552c23caf3ed0e9aef2647d07029b1651eebffdea5b046",
    "experiments/2026-08-05-a72-safe-off-ownership-contract/results/contract-validation-20260805.txt":
        "19a2674623722e54b0bb0599a2acd6504c0eca0e88b0fcc5dfe570352d34eb48",
    "experiments/2026-08-02-a72-cpu8-held-online/results/source-order-audit-20260802.txt":
        "ce530fb74fe520d1899f94f64a2c4e2a0029699cb6dd91f7eaccb6d5f5e01a34",
    "experiments/2026-08-02-a72-one-way-cpu8-boundary/DESIGN.md":
        "257217f6ea0d513162e2888259ee8a4a6b76a614ee8d3b2bb43f5b841a67321a",
    "experiments/2026-08-03-a72-cpu9-cluster-reuse/DESIGN.md":
        "9c75776937c4045dd4774546ec1985068eaf6c672f88f740757a146aeec45717",
    "configs/gemini.fragment":
        "aa2a138abe1449bc5204099af349d271c5eb5337d2d932a8d02ea02f0a0ee8b8",
    "configs/gemini-handoff.fragment":
        "cb786eb244637af11858cb0ca31c138be32bf0104582ec589fc0eb2d50933f5e",
    "kernel/manifest.json":
        "ea55ec7dd39ef96ed0d69f008405a8f5776bd3afe599ab4da9ea688d4c83687a",
    "patches/v7.1.3/0091-soc-mediatek-add-MT6797-A72-power-observer.patch":
        "ed46e44a7ba42a7084ab5fba59168f3d51fcfed40f50dee363e1d8f43e619e98",
    "patches/v7.1.3/0092-arm64-mediatek-gate-MT6797-A72-PSCI-boot.patch":
        "cbd54d048e2233ffcb268174037248ade9ab8716f9816481d926b20b4bd3bba5",
}
SOURCE_URL = "https://cdn.kernel.org/pub/linux/kernel/v7.x/linux-7.1.3.tar.xz"
SOURCE_SHA256 = "be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc"
README_PROVENANCE_SHA256 = (
    "0007ba7868cbd68bb2a4ef6ad66240c7e00715e08934ca5d05ca482dfd464354",
    "deaa6686582e6e3f2e3453ff626f14b2ec555d9be468ac2f67fb350e6eead8bc",
    "6da8ad1883362b32fe7b8e2332f262ec8ebf195db09c91872a0ce59eda429af6",
    "8451fbc2910a0d4776efe2d51b84f0bcb3e95ac77310ff425c506bbb59d6af26",
    "6ee968f2f1286393d9552c23caf3ed0e9aef2647d07029b1651eebffdea5b046",
    "19a2674623722e54b0bb0599a2acd6504c0eca0e88b0fcc5dfe570352d34eb48",
    "ce530fb74fe520d1899f94f64a2c4e2a0029699cb6dd91f7eaccb6d5f5e01a34",
    "ea55ec7dd39ef96ed0d69f008405a8f5776bd3afe599ab4da9ea688d4c83687a",
    "be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc",
    "cbd54d048e2233ffcb268174037248ade9ab8716f9816481d926b20b4bd3bba5",
    "ed46e44a7ba42a7084ab5fba59168f3d51fcfed40f50dee363e1d8f43e619e98",
    "2344676ee4fc5b889eba4d40aad1a00e1c5266935ee9a887ad8624b763f1077d",
    "257217f6ea0d513162e2888259ee8a4a6b76a614ee8d3b2bb43f5b841a67321a",
    "9c75776937c4045dd4774546ec1985068eaf6c672f88f740757a146aeec45717",
    "aa2a138abe1449bc5204099af349d271c5eb5337d2d932a8d02ea02f0a0ee8b8",
    "cb786eb244637af11858cb0ca31c138be32bf0104582ec589fc0eb2d50933f5e",
)
README_SOURCE_IDENTITIES = (
    SOURCE_URL,
    "59e00a9144d782e148332009a835b99c43382467",
)


class ContractError(ValueError):
    """The frozen contract or its evidence violates a safety invariant."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def load_tsv(path: Path, fields: tuple[str, ...]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        require(tuple(reader.fieldnames or ()) == fields, f"schema changed: {path}")
        rows: list[dict[str, str]] = []
        for line_number, row in enumerate(reader, start=2):
            require(None not in row, f"extra TSV cell at {path}:{line_number}")
            for field in fields:
                value = row.get(field)
                require(value is not None, f"missing {field} at {path}:{line_number}")
                require(value == value.strip(), f"untrimmed {field} at {path}:{line_number}")
                require(value != "", f"empty {field} at {path}:{line_number}")
                require(not any(char in value for char in "\t\r\n"),
                        f"embedded TSV control in {field} at {path}:{line_number}")
            rows.append(row)  # type: ignore[arg-type]
        return rows


def row_map(rows: Iterable[dict[str, str]]) -> dict[str, dict[str, str]]:
    mapped: dict[str, dict[str, str]] = {}
    for row in rows:
        require(row["id"] not in mapped, f"duplicate id: {row['id']}")
        mapped[row["id"]] = row
    return mapped


def require_tokens(value: str, tokens: tuple[str, ...], context: str) -> None:
    for token in tokens:
        require(token in value, f"{context} missing {token}")


def require_specs(
    by_id: dict[str, dict[str, str]],
    specs: dict[str, dict[str, tuple[str, ...]]],
) -> None:
    for identifier, fields in specs.items():
        for field, tokens in fields.items():
            require_tokens(by_id[identifier][field], tokens, f"{identifier}.{field}")


def canonical_row_sha256(row: dict[str, str], fields: tuple[str, ...]) -> str:
    value = "\t".join(row[field] for field in fields) + "\n"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def validate_row_hashes(
    rows: list[dict[str, str]], fields: tuple[str, ...], expected: dict[str, str]
) -> None:
    require(set(expected) == {row["id"] for row in rows},
            "canonical row-hash inventory changed")
    for row in rows:
        require(canonical_row_sha256(row, fields) == expected[row["id"]],
                f"canonical row changed: {row['id']}")


def validate_phase(rows: list[dict[str, str]]) -> None:
    require(tuple(row["id"] for row in rows) == PHASE_IDS, "phase inventory changed")
    by_id = row_map(rows)
    observed: set[str] = set()
    for row in rows:
        observed.update(row["phase_from"].split("|"))
        observed.add(row["phase_to"])
        require("big_on" not in row["members_rule"],
                f"private ledger entered members rule in {row['id']}")
    require(observed == ALL_PHASES, "phase vocabulary changed")

    exact_edges = {
        "P05": ("FROZEN", "REJECTED"), "P06": ("REJECTED", "CONSUMED"),
        "P07": ("FROZEN", "OFF_COMMITTED"),
        "P08": ("QUERY_INFLIGHT", "OFF_PROVEN"),
        "P09": ("OFF_PROVEN", "VERIFYING"),
        "P10": ("VERIFYING", "CONSUMED"), "P11": ("CONSUMED", "IDLE"),
        "P14": ("ON_ISSUED", "VERIFYING"),
        "P15": ("ON_ISSUED", "VERIFYING"), "P16": ("ON_ISSUED", "FAULT"),
        "P17": ("FROZEN", "ON_ISSUED"), "P18": ("FROZEN", "ON_ISSUED"),
        "P19": ("VERIFYING", "FAULT"),
        "P20": ("OFF_COMMITTED", "QUERY_INFLIGHT"),
        "P21": ("ON_ISSUED", "REJECTED"),
        "P22": ("OFF_COMMITTED", "FAULT"), "P23": ("FROZEN", "FAULT"),
        "P24": ("ON_ISSUED", "ON_ISSUED"),
        "P26": ("FROZEN", "FROZEN"), "P27": ("ON_ISSUED", "ON_ISSUED"),
        "P28": ("ON_ISSUED", "ON_ISSUED"),
        "P29": ("ON_ISSUED", "ON_ISSUED"), "P30": ("ON_ISSUED", "FAULT"),
        "P31": ("IDLE", "IDLE"), "P32": ("VERIFYING", "FAULT"),
    }
    for identifier, edge in exact_edges.items():
        require((by_id[identifier]["phase_from"], by_id[identifier]["phase_to"]) == edge,
                f"phase edge changed: {identifier}")
    require(set(by_id["P13"]["phase_from"].split("|")) == ALL_PHASES,
            "reset edge does not cover every phase")

    specs = {
        "P01": {"token_rule": ("P31-same-request-cpu8-up-attempt=consumed",
            "allocate-exact-owner-operation-cpu8-up-target-cpu8-generation-after-A28-pass",
            "CPUHP_ONLINE", "cpu_logical_map(cpu8)=0x200",
            "__pa_symbol(secondary_entry)", "cpu8-preparation-attempt=one-unconsumed",
            "cpu-on-attempt=one-unconsumed", "provider-acquire-attempt=one-unconsumed",
            "affinity-budget=none", "provider-release-attempt=none")},
        "P02": {"token_rule": ("P31-same-request-cpu9-up-attempt=consumed",
            "before-remaining-A28-prestate-checks", "after-A28-pass", "CPUHP_ONLINE",
            "cpu_logical_map(cpu9)=0x201", "__pa_symbol(secondary_entry)",
            "provider-acquire-attempt=none", "affinity-budget=none")},
        "P03": {"token_rule": ("P31-same-request-cpu9-off-attempt=consumed",
            "CPUHP_OFFLINE", "A31-private-entry-big_on=0x3", "cpu_logical_map(cpu9)=0x201",
            "affinity-budget=one-unconsumed-level-0", "provider-release-attempt=none")},
        "P04": {"token_rule": ("P31-same-request-last-cpu8-off-attempt=consumed",
            "CPUHP_OFFLINE", "A31-private-entry-big_on=0x1", "cpu_logical_map(cpu8)=0x200",
            "affinity-budget=one-unconsumed-level-0",
            "provider-release-attempt=one-unconsumed")},
        "P05": {"token_rule": ("A32-no-cpuhp-provider-or-hardware-effect=pass",),
            "allowed_effect": ("record-proven-no-effect-rejection-only",)},
        "P06": {"token_rule": ("A38-operation-attempt-remains-consumed-until-A34-reset",),
            "allowed_effect": ("release-transaction-owned-freeze-once",)},
        "P07": {"token_rule": ("off-operation", "CPUHP_OFFLINE", "target-side-owner",
            "P26-entry-snapshot-private-branch-attestation=pass"),
            "allowed_effect": ("publish-OFF_COMMITTED-immediately-before",
                               "exact-target-CPU_OFF-smc-entry", "no-software-commit")},
        "P08": {"token_rule": ("cpu_logical_map(target)", "affinity-level=0",
            "query-budget=consumed-before-call", "return=OFF"),
            "allowed_effect": ("no-new-affinity-query",)},
        "P09": {"token_rule": ("no-affinity-query-remains",),
            "allowed_effect": ("independent-callback", "resource-readbacks-only")},
        "P10": {"token_rule": ("exact-M01-M02-M03-or-M04",
            "A33-final-requested-cpuhp-state-and-online-mask", "rollback-window=pass"),
            "members_rule": ("members=exact-membership-table-edge",)},
        "P11": {"token_rule": ("A38-exact-operation-attempt-remains-consumed",),
            "allowed_effect": ("scalar-phase-cleanup-only", "freeze-already-released")},
        "P12": {"token_rule": ("query-budget=consumed-before-call", "retry=forbidden",
            "nonreturn-not-an-executed-edge"), "failure_route": ("reset-only",)},
        "P13": {"token_rule": ("A34-exact-zero-state-topology-mapping-bootstrap",
            "operation-attempt-reinitialization=pass"), "members_rule": ("present-possible-restored",
            "nonaliased-mpidr-0x200-0x201", "private-replay-zero-proof"),
            "allowed_effect": ("not-runtime-or-ordinary-linux-reboot-clear",),
            "failure_route": ("including-IDLE-with-consumed-P31-attempt",
                              "mapping-mismatch-remains-terminal")},
        "P14": {"token_rule": ("cpu8-up", "cpu_logical_map(cpu8)",
            "cpu-on-attempt=consumed-before-call", "same-cpu8-mpidr-secondary-completion")},
        "P15": {"token_rule": ("cpu9-up", "cpu_logical_map(cpu9)",
            "cpu-on-attempt=consumed-before-call", "same-cpu9-mpidr-secondary-completion")},
        "P16": {"token_rule": ("returned-error-or-uncertainty", "retry=forbidden",
            "nonreturn-not-an-executed-edge"), "failure_route": ("external-reset-only",)},
        "P17": {"token_rule": ("A36-cpu8-prestate-owner-and-call-shape-gate=pass",
            "cpu_logical_map(cpu8)=0x200", "cpu8-preparation-attempt=one-unconsumed-from-P01"),
            "provider_rule": ("provider=NONE-exact-before-first-effect",),
            "allowed_effect": ("no-provider-or-hardware-effect",)},
        "P18": {"token_rule": ("A36-cpu9-prestate-owner-and-call-shape-gate=pass",
            "cpu_logical_map(cpu9)=0x201"), "provider_rule": ("durable-reference-id-from-M01",),
            "allowed_effect": ("no-provider-or-hardware-effect",)},
        "P19": {"token_rule": ("A37-startup-auto-rollback-blocked",
            "every-M02-post-full-bringup-callback-IPI-identity-online-accounting-hit-count",
            "shared-resource-provider-A33-final-schedule-or-reschedule-failure-is-terminal",
            "no-off-query-budget", "retry=forbidden"),
            "provider_rule": ("HELD-unchanged-for-every-M02-post-full-bringup-failure",),
            "allowed_effect": ("P19-invalid-if-generic-auto-rollback-started",
                               "no-P10-before-all-M02-proofs-and-sample3")},
        "P20": {"token_rule": ("cpu_logical_map(target)", "affinity-level=0",
            "one-unconsumed-from-P03-or-P04-to-consumed-before-call",
            "A29-concurrency-or-entry-proof=pass", "A40-private-branch-proof-fresh"),
            "allowed_effect": ("publish-QUERY_INFLIGHT", "release-lock-before-smc"),
            "failure_route": ("nonreturn-remains-QUERY_INFLIGHT", "no-retry")},
        "P21": {"event": ("R03-provider-rejection",),
            "token_rule": ("P29-preprovider-effects-rollback=no-residual-effect",
                           "CPU_ON=not-issued")},
        "P22": {"token_rule": ("query-budget=unconsumed", "retry=forbidden")},
        "P23": {"token_rule": ("CPU_OFF=not-issued", "A32-clean-rollback-not-proven",
            "retry=forbidden")},
        "P24": {"token_rule": ("CPUHP_ONLINE", "P28-postprovider-preparation",
            "A36-cluster-reuse-gate=pass", "cpu_logical_map(target)=cpu8-0x200-or-cpu9-0x201",
            "__pa_symbol(secondary_entry)", "cpu-on-attempt=one-to-consumed-before-call"),
            "allowed_effect": ("two-argument-psci_ops.cpu_on",)},
        "P25": {"token_rule": ("CPU_OFF-returned", "retry=forbidden"),
            "failure_route": ("P08-success-cannot-override-return-FAULT",)},
        "P26": {"token_rule": ("A31-same-generation-C02-or-L02",
            "A40-private-writer-exclusion-or-serialized-revalidation-strategy=armed",)},
        "P27": {"token_rule": ("cpu8-preparation-attempt=one-to-consumed-before-first-mutation",),
            "allowed_effect": ("SPM-0x218", "BPLL", "PWRAP-assert", "no-provider-or-CPU_ON")},
        "P28": {"token_rule": ("R02-durable-provider-reference=HELD",),
            "allowed_effect": ("clear-external-isolation-exactly", "deassert-owned-PWRAP",
            "wait-240us", "1.1V-SRAM-LDO", "selector-calibration-readback", "no-CPU_ON")},
        "P29": {"token_rule": ("R03-clean-refusal", "CPU_ON=not-issued",
            "postprovider-preparation=not-started"),
            "allowed_effect": ("SPM-reset-restore", "PWRAP-deassert",
                               "software-guard-release", "no-residual-effect")},
        "P30": {"token_rule": ("CPU_KILL_ME-after-cpu_die_early-present-clear",
            "CPU_PANIC_KERNEL", "CPU_STUCK_IN_KERNEL", "52-bit-VA",
            "unsupported-page-granule", "unknown-default-timeout"),
            "allowed_effect": ("target-custom-cpu_die", "parks-without-CPU_OFF",
            "controller-custom-cpu_kill", "skips-affinity", "no-runtime-inverse")},
        "P31": {"token_rule": ("cpu8-up-only-owner-safe-observer-capture-window=open",
            "no-other-predecessor-state-check-before-consumption",
            "A38-exact-operation-attempt=available-to-consumed-atomically",
            "no-generation-or-token-allocated", "remaining-A28-generic-state-checks",
            "later-A36-operation-specific-predecessor-checks=pending"),
            "allowed_effect": ("consume-only-exact-operation-attempt", "read-only",
                               "no-token-cpuhp-provider-or-hardware-effect"),
            "failure_route": ("A28-mismatch-deny-IDLE-without-token",
                              "then-up-operations-run-A36-before-P17-P18")},
        "P32": {"token_rule": ("generic-post-CPU_ON-auto-rollback=begun",
            "target-cpu_die-up-token-guard=pass", "controller-cpu_kill-up-token-fault-guard=pass"),
            "allowed_effect": ("prevents-CPU_OFF", "prevents-affinity",
            "A30-cpuhp-online-mask-divergence", "no-runtime-inverse-query-or-membership-commit"),
            "failure_route": ("cpu_online_mask-may-diverge", "external-reset-only")},
    }
    require_specs(by_id, specs)
    require(by_id["P28"]["allowed_effect"].count("wait-240us") == 2,
            "P28 must retain both inherited 240us waits")
    release_rows = [row["id"] for row in rows
                    if "release-transaction-owned-freeze-once" in row["allowed_effect"]]
    require(release_rows == ["P06", "P10"], "freeze release edges changed")
    validate_row_hashes(rows, PHASE_FIELDS, EXPECTED_PHASE_ROW_SHA256)


def validate_membership(rows: list[dict[str, str]]) -> None:
    require(tuple(row["id"] for row in rows) == MEMBERSHIP_IDS,
            "membership inventory changed")
    by_id = row_map(rows)
    expected = {
        "M01": ("cpu8-up", "0x0", "cpu8", "0x1", "NONE"),
        "M02": ("cpu9-up", "0x1", "cpu9", "0x3", "HELD"),
        "M03": ("cpu9-off-retain-cpu8", "0x3", "cpu9", "0x1", "HELD"),
        "M04": ("last-cpu8-off", "0x1", "cpu8", "0x0", "HELD"),
    }
    for identifier, values in expected.items():
        row = by_id[identifier]
        actual = tuple(row[field] for field in
                       ("operation", "pre_members", "target", "post_members", "pre_provider"))
        require(actual == values, f"membership edge changed in {identifier}")
        require(row["implementation_state"] == "contract-only-blocked",
                f"membership implementation promoted in {identifier}")
        require_tokens(row["private_big_on_rule"],
                       ("separate-private-ledger", "not-linux-members"), identifier)
        require("big_on=members" not in row["private_big_on_rule"],
                f"private big_on conflated with members in {identifier}")
        require("exact-live-generation-bound-to-all-proofs" in row["independent_proofs"],
                f"{identifier} lost live-generation binding")
        require("A33-final" in row["commit_gate"], f"{identifier} lost final CPUHP attestation")
    require("0x2" not in ";".join(";".join(row.values()) for row in rows),
            "invalid CPU9-only membership state introduced")
    specs = {
        "M01": {"commit_gate": ("P27-preprovider", "P28-postprovider",
            "new-durable-reference-id", "cpu_logical_map(cpu8)",
            "cpu8-callback-complete", "dcm-and-resource-readbacks=pass"),
            "provider_sequence": ("NONE->ACQUIRE_INFLIGHT->HELD-before-commit",
                                  "origin-M01-generation"),
            "query_rule": ("affinity-info=none",)},
        "M02": {"commit_gate": ("P15-secondary-completion", "after-P15-full-generic-callbacks-complete",
            "cpu8-cpu9-online", "inherited-cluster-DCM-published",
            "then-initial-static-delayed-work-schedule=pass", "then-sample1-about-1s=pass",
            "then-reschedule1=pass", "then-sample2-about-6s=pass",
            "then-reschedule2=pass", "then-sample3-about-10s=pass",
            "callback-identity=8", "callback-identity=9", "equal-cumulative-hit-counts",
            "sample3-hits8=3-hits9=3", "P10-forbidden-before-sample3-and-all-M02-proofs",
            "durable-provider-reference-id-and-origin-from-M01=unchanged"),
            "independent_proofs": ("P15-secondary-completion-then-full-generic-callback-completion",
                "initial-schedule-then-sample1-then-reschedule1-then-sample2-then-reschedule2-then-sample3",
                "callback-IPI-identity-online-accounting", "final-requested-CPUHP-state-and-online-mask"),
            "provider_sequence": ("HELD->HELD", "origin-unchanged"),
            "query_rule": ("affinity-info=none",),
            "failure_rule": ("members-remain-0x1", "provider-remains-HELD",
                "every-post-full-bringup-callback-IPI-identity-online-accounting-hit-count",
                "provider-A33-final-schedule-or-reschedule-failure-enters-P19-FAULT",
                "no-runtime-inverse-or-retry", "external-reset-only",
                "no-P10-before-sample3-and-all-M02-proofs")},
        "M03": {"commit_gate": ("safe-off-C02", "big_on=0x3",
            "A40-private-branch-proof-fresh", "cpu_logical_map(cpu9)", "affinity-level-0",
            "PWR_CON-and-power-ack=OFF", "cpu8-callback-complete", "safe-off-C07",
            "durable-provider-reference-id-and-origin-from-M01=unchanged"),
            "provider_sequence": ("HELD->HELD",),
            "independent_proofs": ("A40-private-writer-caller-exclusion-or-immediate-serialized-revalidation",),
            "query_rule": ("cpu_logical_map(cpu9)", "level-0-once",
                           "fresh-A40-private_big_on-0x3", "nontarget-queries=forbidden"),
            "failure_rule": ("members-remain-0x3", "provider-remains-HELD",
                             "phase=FAULT", "reset-only")},
        "M04": {"commit_gate": ("safe-off-L02", "big_on=0x1",
            "A40-private-branch-proof-fresh", "cpu_logical_map(cpu8)", "affinity-level-0",
            "safe-off-L06-through-L13", "exact-durable-provider-reference-id-from-M01=consumed"),
            "provider_sequence": ("HELD->RELEASE_INFLIGHT->NONE-before-commit",
                                  "consume-exact-durable-reference-id"),
            "independent_proofs": ("A40-private-writer-caller-exclusion-or-immediate-serialized-revalidation",
                "safe-off-L06-through-L12", "safe-off-L13-release"),
            "query_rule": ("cpu_logical_map(cpu8)", "level-0-once",
                           "fresh-A40-private_big_on-0x1", "nontarget-queries=forbidden"),
            "failure_rule": ("members-remain-0x1", "provider=retain-or-FAULT_UNKNOWN",
                             "phase=FAULT", "reset-only")},
    }
    require_specs(by_id, specs)
    validate_row_hashes(rows, MEMBERSHIP_FIELDS, EXPECTED_MEMBERSHIP_ROW_SHA256)


def validate_provider(rows: list[dict[str, str]]) -> None:
    require(tuple(row["id"] for row in rows) == PROVIDER_IDS,
            "provider inventory changed")
    by_id = row_map(rows)
    states: set[str] = set()
    for row in rows:
        states.update(row["from_state"].split("|"))
        states.add(row["to_state"])
        require(row["implementation_state"] == "contract-only-blocked",
                f"provider implementation promoted in {row['id']}")
    require(states == PROVIDER_STATES, "provider state vocabulary changed")
    require([r["id"] for r in rows if r["from_state"] == "NONE" and
             r["to_state"] == "ACQUIRE_INFLIGHT"] == ["R01"],
            "duplicate or missing provider acquire")
    require([r["id"] for r in rows if r["from_state"] == "HELD" and
             r["to_state"] == "RELEASE_INFLIGHT"] == ["R05"],
            "duplicate or missing provider release")
    specs = {
        "R01": {"required_context": ("phase=ON_ISSUED", "operation=cpu8-up",
            "P17-published-before-first-effect", "P27-preprovider-preparation=complete",
            "provider-acquire-attempt=one-unconsumed-from-P01"),
            "proof": ("publish-ACQUIRE_INFLIGHT", "consume-provider-acquire-attempt-before",
                      "real-regulator-consumer-vote-requested-after-P27")},
        "R02": {"required_context": ("provider-acquire-attempt=consumed-before-call",
                                      "P27-preprovider-preparation=complete"),
            "proof": ("1ms-settle", "BUCKB-enabled-page=0x80", "inherited-VSEL-exact-readback",
                      "durable-held-reference-id", "origin-M01-generation", "before-P28")},
        "R03": {"required_context": ("P27-preprovider-effects-executed",
            "P28-postprovider-preparation-not-started", "CPU_ON-not-issued"),
            "proof": ("no-consumer-vote", "no-provider-mutation", "no-rail-mutation",
                      "P29-exact-preisolation-rollback-required-before-P21")},
        "R04": {"required_context": ("held-reference-id=published-durable-id",
            "origin-M01-generation=unchanged"),
            "proof": ("retained-across-transaction-generations",)},
        "R05": {"required_context": ("operation=last-cpu8-off",
            "target-affinity-result=OFF", "L06-through-L12", "idvfs-dcm-sram-sentinel",
            "held-reference-id=published-durable-id", "provider-release-attempt=one-unconsumed-from-P04"),
            "proof": ("publish-RELEASE_INFLIGHT", "consume-provider-release-attempt-before",
                      "release-exact-durable-real-regulator-consumer-reference")},
        "R06": {"required_context": ("released-reference-id=exact-published-durable-id",),
            "proof": ("no-consumer-reference", "final-rail-readback",
                      "consume-durable-reference-identity")},
        "R07": {"proof": ("regulator_is_enabled-is-not-reference-proof",),
            "failure_state": ("FAULT_UNKNOWN",), "member_commit": ("members-remain-conservative",)},
        "R08": {"required_context": ("phase=FAULT",),
            "proof": ("provider-state-not-cleared-at-runtime",),
            "member_commit": ("platform-or-external-reset",)},
    }
    require_specs(by_id, specs)
    require(by_id["R02"]["to_state"] == "HELD", "provider acquire did not establish HELD")
    require(by_id["R06"]["to_state"] == "NONE", "provider release did not establish NONE")
    require(by_id["R07"]["to_state"] == "FAULT_UNKNOWN", "ambiguous provider was assumed known")
    require(by_id["R08"]["to_state"] == "FAULT_UNKNOWN", "provider fault gained runtime clear")
    validate_row_hashes(rows, PROVIDER_FIELDS, EXPECTED_PROVIDER_ROW_SHA256)


def validate_admission(rows: list[dict[str, str]]) -> None:
    require(tuple(row["id"] for row in rows) == ADMISSION_IDS + LOCK_IDS,
            "admission/lock inventory changed")
    by_id = row_map(rows)
    for row in rows:
        require(row["implementation_state"] == "contract-only-blocked",
                f"implementation promoted in {row['id']}")
    specs = {
        "A01": {"required_context": ("phase=FROZEN", "CPUHP_OFFLINE",
            "P26-entry-snapshot-private-branch-attestation=pass"),
            "rule": ("allow-only-exact-operation-target-CPUHP_OFFLINE-token",
                     "deny-every-other-caller"), "ordering": ("before-cpu_maps_update_begin",)},
        "A02": {"required_context": ("CPUHP_OFFLINE", "tasks_frozen=0"),
            "rule": ("revalidate-exact-operation-target", "deny-tasks_frozen-not-zero"),
            "ordering": ("before-cpus_write_lock", "cpuhp_set_state", "all-cpuhp-callbacks")},
        "A03": {"required_context": ("tasks_frozen=1", "caller-may-hold-cpu_add_remove_lock"),
            "rule": ("always-deny", "leaf-state-snapshot", "never-acquire-a72_transition_lock")},
        "A04": {"required_context": ("members-nonzero", "provider-not-NONE", "phase-FAULT"),
            "rule": ("veto-suspend", "deny-transaction-begin"),
            "ordering": ("priority-strictly-above-gemian-vendor-priority-zero",),
            "evidence": ("no-vendor-import",)},
        "A05": {"required_context": ("already-holds-hps_ctxt.lock", "owner-operation-target-generation"),
            "rule": ("must-not-reacquire-hps_ctxt.lock", "public-cpu_up-or-cpu_down-only"),
            "ordering": ("M01-or-M02-commit-before-HPS-increment",
                "M03-or-M04-commit-before-HPS-decrement", "same-operation-and-generation-required")},
        "A06": {"rule": ("release-para_lock-before-public",),
            "ordering": ("not-held-into-cpu_add_remove_lock",)},
        "A07": {"required_context": ("every-admitted-a72-up-down-and-CPU_DOWN_FAILED-action",),
            "rule": ("validate-token-before-cpufreq_mutex", "all-CPUHVFS-actions-no-op",
                     "skip-cluster-off-and-cluster-on-hardware-writes"),
            "evidence": ("B-and-CCI-frequency-index-ARMPLL-PBM", "write-sets=empty"),
            "failure": ("CPU_DOWN_FAILED-remains-no-op",)},
        "A08": {"required_context": ("before-and-after-CPUHP_TEARDOWN_CPU",),
            "rule": ("CPUHP_BP_PREPARE_DYN-is-after-takedown_cpu", "too-late-for-admission"),
            "evidence": ("both-sides-of-CPUHP_TEARDOWN_CPU",)},
        "A09": {"required_context": ("phase=OFF_COMMITTED", "cpu_logical_map(target)",
            "affinity-level=0", "query-budget=one-unconsumed-from-P03-or-P04",
            "A29-concurrency-or-entry-discriminator-proof=pass", "A31-private-big_on=0x3",
            "0x1-for-last-cpu8-off", "A40-private-branch-proof-fresh-through-query=pass"),
            "rule": ("P20-QUERY_INFLIGHT", "consume-query-budget-before-call",
                "one-level-0-active-affinity-info", "exact-owner-validated-target-MPIDR-only",
                "outer-timer-does-not-bound-synchronous-smc", "block-on-stale-or-uninventoried")},
        "A10": {"rule": ("forbidden-retained-or-nontarget-query",)},
        "A11": {"rule": ("forbidden-already-off-or-nontarget-query", "no-repeat")},
        "A12": {"rule": ("reports-DEAD-inside-cpu_die-immediately-before",
            "controller-later-enters-cpuhp_bp_sync_dead-and-ops-cpu_kill"),
            "failure": ("DEAD-is-not-CPU_OFF-WFI-or-physical-off-proof",
                        "configuration-toggle-is-not-a-fix")},
        "A13": {"rule": ("msecs_to_jiffies-100", "do-affinity-info", "OFF-return",
                           "usleep_range-100-1000", "while-time_before"),
            "ordering": ("unbounded-first-smc",),
            "failure": ("generic-cpu_psci_ops-off-path-prohibited-for-a72",)},
        "A14": {"rule": ("cpu_can_disable=false", "cpu_disable=absent", "cpu_die=absent",
            "cpu_kill=absent", "audit-cpu_can_disable-optional-cpu_disable",
            "resident-TOS-check"),
            "ordering": ("must-not-enable-generic-cpu_psci_ops-off-as-is",
                "every-applicable-phase-membership-provider-admission-and-lock-row",
                "no-enumerated-subset-can-relax-veto"),
            "failure": ("cpu-disable-veto-required",)},
        "A15": {"rule": ("keep-source-classes-distinct",
                          "neither-substitutes-for-exact-active-gemian-revision")},
        "A16": {"rule": ("void-cleanup-only-warns-on-kill-error",
            "kill-result-not-propagated-to-_cpu_down", "clear-cpu_online_mask-and-return-success"),
            "ordering": ("A30-core-interface-propagation-change",)},
        "A17": {"rule": ("remove_cpu-device_offline-wrapper", "A01-exact-operation-token-admission",
                          "remove_cpu-does-not-mutate-present-topology")},
        "A18": {"required_context": ("live-token", "members-not-0x0", "provider-not-NONE",
            "phase-FAULT", "suspend-active"), "rule": ("veto-suspend", "deny-transaction-begin")},
        "A19": {"rule": ("void-10-second-sync-timeout", "failed-to-report-dead-state",
            "continues-without-arch-cleanup-or-cpu_kill"),
            "failure": ("phase=FAULT", "query-budget=unconsumed", "no-outer-success")},
        "A20": {"rule": ("exact-operation-token-gate-must-dominate-legacy-path",),
            "ordering": ("before-cpu-maps-lock", "CPU_DOWN_PREPARE")},
        "A21": {"rule": ("only-validate-published-token", "must-not-acquire-a72_transition_lock",
            "allocate-or-reuse-token", "call-cpu_up-or-cpu_down", "invoke-affinity",
            "change-members", "change-provider"),
            "lock_rule": ("bounded-a72_state_lock-leaf-snapshot-only",)},
        "A22": {"required_context": ("phase=ON_ISSUED", "provider=HELD", "CPUHP_ONLINE",
            "A36-exact-up-prestate-owner-and-call-shape-gate=pass"),
            "rule": ("exact-up-operation-target-CPUHP_ONLINE-token", "add_cpu-device_online-wrapper",
                     "public-up-preflight-attested"),
            "ordering": ("before-cpu_possible", "try_online_node", "cpu_maps_update_begin")},
        "A23": {"required_context": ("CPUHP_ONLINE", "public-up-preflight=attested",
            "tasks_frozen=0"), "rule": ("revalidate-exact-up-operation-target",
            "deny-tasks_frozen-not-zero"), "ordering": ("before-cpus_write_lock",
            "cpuhp_set_state", "all-startup-cpuhp-callbacks")},
        "A24": {"rule": ("always-deny-unowned-unattested-or-frozen", "leaf-state-snapshot",
                          "never-acquire-a72_transition_lock"),
            "ordering": ("earliest-_cpu_up-entry", "before-cpus_write_lock")},
        "A25": {"required_context": ("all-startup-callbacks", "every-can_rollback_cpu-teardown-branch"),
            "rule": ("every-startup-and-rollback-side-effect-owner", "A37-auto-rollback-hazard")},
        "A26": {"rule": ("cpu_boot-returns-EAGAIN",
            "every-applicable-phase-membership-provider-admission-and-lock-row",
            "no-enumerated-subset-can-relax-veto", "P32", "R07", "A39"),
            "ordering": ("before-any-PSCI-CPU_ON",)},
        "A27": {"rule": ("P07-OFF_COMMITTED-immediately-before-CPU_OFF-smc-entry",
            "bounded-non-SMC-wait", "timeout-CASes-P23-FAULT",
            "target-losing-P07-CAS-must-not-issue-CPU_OFF")},
        "A28": {"boundary": ("generic-entry-validation-after-P31",),
            "required_context": ("P31-same-request-operation-attempt=consumed", "target-present-possible",
                                "cpu_logical_map-MPIDR"),
            "rule": ("only-generic-entry-invariant", "matching-provider-and-CPUHP-state",
                "target-present-possible-and-nonaliased-MPIDR", "0x2-forbidden",
                "allocate-exact-P01-P04-token-only-after-generic-A28-pass",
                "operation-specific-predecessor-state-is-later-A36"),
            "ordering": ("P31-attempt-consumption-before-generic-A28",
                "A28-pass-before-P01-P04-token-and-freeze",
                "A36-operation-specific-up-predecessor-checks-after-P01-P02-before-P17-P18"),
            "failure": ("denies-in-IDLE-with-no-token", "P31-attempt-consumed",
                        "A36-mismatch-uses-P05-P06")},
        "A29": {"rule": ("block-P20-and-affinity", "concurrent-SMC-lock-deadlock-proof",
                          "CPU_OFF-entry-or-WFI-discriminator", "WFI-poll-alone-is-not")},
        "A30": {"required_context": ("P32-guarded-A37-rollback", "clear-cpu_online_mask"),
            "rule": ("terminal-divergent-state-through-P32", "never-rollback-or-reconcile"),
            "failure": ("P32-owns-guarded-up-rollback", "cpu_online-mask-may-diverge",
                        "external-reset-only")},
        "A31": {"rule": ("private-big_on-entry-exactly-0x3", "exactly-0x1",
            "publish-P26", "arm-A40-complete-writer-caller-exclusion-or-immediate-owner-safe-serialized-revalidation",
            "linux-members-cannot-substitute"),
            "ordering": ("before-A01-A02", "A40-proof-must-remain-fresh-through-P20")},
        "A32": {"rule": ("P05-REJECTED-only-if-no-cpuhp-provider-or-hardware-effect",
            "every-failure-after-any-executed-or-uncertain-effect-enters-P23-FAULT")},
        "A33": {"rule": ("final-requested-CPUHP-state-and-cpu_online_mask",
            "generic-return-alone-insufficient", "A30-divergence-forbids-commit"),
            "ordering": ("after-all-callbacks-generic-result-and-rollback-window-before-P10",)},
        "A34": {"required_context": ("known-good-platform-or-external-reset", "no-ordinary-linux-reboot"),
            "rule": ("members=0x0", "matching-CPUHP-and-online-mask", "present-and-possible-restored",
            "cpu_logical_map(cpu8)=0x200", "cpu_logical_map(cpu9)=0x201", "provider=NONE",
            "private-replay-ledger=0", "reinitialize-A38-four-operation-attempts=available"),
            "failure": ("remain-terminal-on-any-present-possible-mapping-or-other-mismatch",)},
        "A35": {"required_context": ("internal-early-secondary-present-clear-owned-separately-by-A39",),
            "rule": ("add_cpu-and-remove_cpu-are-online-offline-wrappers",
            "external-physical-probe-release-or-present-possible-mutation", "fail-closed",
            "do-not-claim-internal-present-mask-immutability")},
        "A36": {"rule": ("observer-capture-window-must-open-before-P31",
            "after-generic-A28-pass-and-P01-P02-token-freeze",
            "operation-specific-predecessor-state-before-P17-P18",
            "two-argument-psci_ops.cpu_on(exact-mpidr,exact-entry)",
            "P27-preprovider", "P28-postprovider", "empty-shared-write-set"),
            "ordering": ("P31-before-generic-A28", "A28-pass-before-P01-P02-token-and-FROZEN",
            "A36-operation-specific-predecessor-state-before-P17-P18", "P27-before-R01",
            "P28-after-R02"), "lock_rule": ("source-call-shape-proof",),
            "failure": ("A28-failure-is-IDLE-no-token-attempt-consumed",
            "A36-failure-before-P17-P18-uses-P05-P06", "P16-after-first-P27-mutation")},
        "A37": {"rule": ("generic-auto-rollback-crossing-CPUHP_TEARDOWN_CPU",
            "all-selected-post-CPU_ON-failure-paths-proven-nonfailing",
            "no-auto-teardown-propagation-interface", "route-P32-terminal-FAULT",
            "without-CPU_OFF-or-affinity", "A30-online-mask-divergence-reset-only"),
            "failure": ("guarded-path-is-P32-A30-FAULT", "no-CPU_OFF-or-affinity-under-up-token")},
        "A38": {"rule": ("P31-atomically-consumes", "before-generic-A28-state-mapping-checks",
            "P01-P04-require-the-same-request-P31-attestation", "do-not-consume-again",
            "A36-predecessor-checks-run-after-P01-P02-token-and-FROZEN-before-P17-P18",
            "P05-P06-P11-never-rearm", "only-A34-platform-or-external-reset"),
            "ordering": ("P31-before-generic-A28-before-P01-P04-token-and-FROZEN",
                         "then-A36-for-up-before-P17-P18"),
            "lock_rule": ("short-a72_state_lock", "never-held-across-A36-register-readback")},
        "A39": {"rule": ("bypasses-cpu_can_disable-and-optional-cpu_disable",
            "clears-cpu_present", "CPU_KILL_ME", "target-custom-cpu_die-up-token-guard",
            "controller-custom-cpu_kill-up-token-fault-guard", "CPU_PANIC_KERNEL",
            "CPU_STUCK_IN_KERNEL-for-52-bit-VA", "unsupported-page-granule",
            "unknown-default-timeout"), "failure": ("present-divergence-is-P30-terminal",
                                                    "no-runtime-retry-CPU_OFF-or-query")},
        "A40": {"rule": ("complete-source-and-runtime-private-big_on-writer-caller-inventory",
            "exclude-every-other-CPU_ON-CPU_OFF-AFFINITY_INFO-and-private-ledger-writer",
            "continuously-through-P20", "non-SMC-reader",
            "independent-A29-equivalent-concurrent-SMC-lock-deadlock-proof",
            "C02-L02-policy-writer-drain-alone-is-insufficient",
            "block-query-on-stale-uninventoried-or-concurrency-unsafe-proof"),
            "ordering": ("after-A31-before-A01", "through-A27-P07-to-atomic-P20",
                         "immediately-before-P20-budget-consumption"),
            "failure": ("P05-before-effects", "P23-after-any-executed-or-uncertain-pre-P07-effect",
                        "P22-after-OFF_COMMITTED", "no-affinity-call-or-membership-commit")},
    }
    require_specs(by_id, specs)
    for identifier in ("A04", "A05", "A06", "A07", "A20"):
        require("public-equivalent-gemian" in by_id[identifier]["boundary"],
                f"Gemian compatibility lane lost in {identifier}")
    gemian_boundaries = (
        "public-equivalent-gemian-hps_ctxt.lock",
        "public-equivalent-gemian-a72_transition_lock",
        "public-equivalent-gemian-cpu_add_remove_lock",
        "public-equivalent-gemian-cpu_hotplug.lock",
        "public-equivalent-gemian-cpufreq_mutex",
        "public-equivalent-gemian-dvfs_lock",
    )
    for order, (identifier, boundary) in enumerate(zip(LOCK_IDS[:6], gemian_boundaries), 1):
        require(by_id[identifier]["boundary"] == boundary,
                f"Gemian lock boundary changed in {identifier}")
        require(by_id[identifier]["ordering"] == f"gemian-order={order}",
                f"Gemian lock order changed in {identifier}")
    require(by_id["L07"]["boundary"] == "a72_state_lock" and
            "leaf-spinlock" in by_id["L07"]["rule"], "state lock is not a leaf")
    require_tokens(by_id["L07"]["rule"],
                   ("never-held-across-sleep", "callback", "notifier", "smc",
                    "regulator", "readback", "delay"), "L07.rule")
    require(not any(token in by_id["L07"]["rule"] for token in (
        "held-across-smc", "held-across-notifier", "held-across-regulator",
        "held-across-readback", "held-across-callback", "held-across-delay")),
        "state lock held across blocking or reentrant work")
    require(by_id["L08"]["ordering"] == "outside-linear-hotplug-chain" and
            "release-before-public-cpu_up-or-cpu_down" in by_id["L08"]["rule"],
            "para_lock entered linear hotplug chain")
    canonical_boundaries = (
        "base-v7.1.3-a72_transition_lock",
        "base-v7.1.3-cpu_add_remove_lock",
        "base-v7.1.3-cpu_hotplug_lock-via-cpus_write_lock",
    )
    for order, (identifier, boundary) in enumerate(zip(LOCK_IDS[8:], canonical_boundaries), 1):
        require(by_id[identifier]["boundary"] == boundary,
                f"canonical lock boundary changed in {identifier}")
        require(by_id[identifier]["ordering"] == f"canonical-order={order}",
                f"canonical lock order changed in {identifier}")
    validate_row_hashes(rows, ADMISSION_FIELDS, EXPECTED_ADMISSION_ROW_SHA256)


def validate_evidence() -> None:
    for relative, expected in EVIDENCE_SHA256.items():
        path = ROOT / relative
        require(path.is_file(), f"missing evidence: {relative}")
        require(hashlib.sha256(path.read_bytes()).hexdigest() == expected,
                f"evidence hash changed: {relative}")
    manifest = json.loads((ROOT / "kernel/manifest.json").read_text(encoding="utf-8"))
    kernel = manifest.get("kernel", {})
    require(kernel.get("version") == "7.1.3", "manifest kernel version changed")
    require(kernel.get("source_url") == SOURCE_URL, "manifest source URL changed")
    require(kernel.get("sha256") == SOURCE_SHA256, "manifest source hash changed")
    audit = (RESULTS / "source-order-audit-20260805.txt").read_text(encoding="utf-8")
    require_tokens(audit, (
        "1f4073e4b9370668d48bd7d85291190a66e17a5d47f869b5be0a6a869336dea4",
        "d0572642224a071b14de5fdd61243d2086016faf3c29765817fd459b503110d6",
        "1eb87f2754f7dd01393ef74429959dbc9fffa30b34dea6513045124c2ec8e031",
        "initial schedule and both reschedule checks must pass",
        "complete writer/caller", "cpu_die_early", "CPU_STUCK_IN_KERNEL",
    ), "source audit")


DOCUMENT_MARKERS = {
    "implementation_authorized": "no", "cpu_off_authorized": "no",
    "build_authorized": "no", "device_action_authorized": "no",
    "device_action": "none",
}


def validate_document_markers(text: str, label: str) -> None:
    lines = [line.strip() for line in text.splitlines()]
    for key, value in DOCUMENT_MARKERS.items():
        matches = [line for line in lines if line.startswith(f"{key}=")]
        require(matches == [f"{key}={value}"],
                f"{label} authorization marker changed or duplicated: {key}")
    normalized = " ".join(text.split()).lower()
    forbidden = (
        "implementation is authorized", "cpu_on is authorized", "cpu_off is authorized",
        "cpu_off candidate is authorized", "build is authorized", "deployment is authorized",
        "device action is authorized", "cpu-disable veto is optional",
        "cpu-up veto is optional", "ordinary reboot clears", "retry the same operation",
    )
    normalized = normalized.replace(
        "no implementation, cpu_on/cpu_off candidate, build, deployment, or device action is authorized.", ""
    )
    require(not any(token in normalized for token in forbidden),
            f"{label} grants contradictory authorization or recovery")


def validate_documents(readme_text: str | None = None, design_text: str | None = None) -> None:
    readme_text = README.read_text(encoding="utf-8") if readme_text is None else readme_text
    design_text = DESIGN.read_text(encoding="utf-8") if design_text is None else design_text
    validate_document_markers(readme_text, "README")
    validate_document_markers(design_text, "DESIGN")
    readme = " ".join(readme_text.split())
    design = " ".join(design_text.split())
    require_tokens(readme, README_PROVENANCE_SHA256 + README_SOURCE_IDENTITIES + (
        "This experiment is offline and read-only.", "No kernel was built.",
        "P31 consumes", "A28 then binds", "A36 then checks", "P32", "A40",
        "initial schedule, sample 1", "reschedule 1", "reschedule 2",
        "P10 is forbidden before sample 3 and all remaining M02 proofs",
        "No implementation, CPU_ON/CPU_OFF candidate, build, deployment, or device action is authorized.",
    ), "README")
    require_tokens(design, (
        "Firmware-private `big_on` is not an alias, mirror, cache, or readback for `members`.",
        "A28 then checks only the generic membership", "P01-P04 allocates the matching token",
        "A36 then checks remaining same-generation operation-specific predecessor state",
        "without the leaf held", "P32 owns the guarded A37 rollback terminal edge",
        "initial schedule, sample 1", "reschedule 1", "reschedule 2",
        "P10 cannot run before sample 3 and every remaining M02 proof",
        "A40 must prove that the branch value remains fresh",
        "every applicable phase, membership, provider, admission, and lock row",
        "This design defines invariants for later review. It contains no kernel patch",
        "grants no build or device authorization.",
    ), "DESIGN")


def validation_report(
    phase_rows: list[dict[str, str]], membership_rows: list[dict[str, str]],
    provider_rows: list[dict[str, str]], admission_rows: list[dict[str, str]],
) -> list[str]:
    return [
        "validation=a72-membership-admission-contract",
        f"phase_rows={len(phase_rows)}",
        f"membership_commits={len(membership_rows)}",
        f"provider_rows={len(provider_rows)}",
        f"admission_rows={sum(r['id'].startswith('A') for r in admission_rows)}",
        f"lock_rows={sum(r['id'].startswith('L') for r in admission_rows)}",
        "source_lanes=2-distinct",
        "members_sequence=0x0->0x1->0x3->0x1->0x0",
        "private_big_on=separate-non-linux-ledger",
        "provider_identity=durable-M01-through-M04",
        "public_internal_cpu_up_admission=REQUIRED",
        "public_internal_cpu_down_admission=REQUIRED",
        "direct_frozen_up_down=DENIED",
        "cpuhp_targets=CPUHP_ONLINE-or-CPUHP_OFFLINE-exact",
        "operation_attempts=4-boot-local-one-shot-P31-before-A28",
        "entry_order=P31->A28-generic->token-FROZEN->A36-up-predecessor",
        "cpu_on_call=two-argument-exact-MPIDR-and-secondary_entry",
        "cpu8_preparation=P27->R01/R02->P28->P24",
        "cpu9_delayed_evidence=initial-plus-two-reschedules-and-sample3-required",
        "off_phases=OFF_COMMITTED->QUERY_INFLIGHT->OFF_PROVEN",
        "target_affinity_queries=1-level-0-active-call-maximum",
        "private_branch_freshness=A40-REQUIRED",
        "early_secondary_status=P30-A39-BLOCKED",
        "startup_auto_rollback=P32-A37-BLOCKED",
        "generic_cpuhp_divergence=A30-TERMINAL",
        "reset_bootstrap=A34-exact-zero-topology-mapping-only",
        "all_applicable_contract_rows_for_veto_relaxation=REQUIRED",
        "current_cpu_boot_veto=REQUIRED",
        "current_cpu_disable_veto=REQUIRED",
        "implementation=BLOCKED",
        "implementation_authorized=no", "cpu_off_authorized=no",
        "build_authorized=no", "device_action_authorized=no", "device_action=none",
        "result=pass",
    ]


def mutation_report() -> list[str]:
    return [
        "validation=a72-membership-admission-contract-mutations",
        f"negative_mutations={EXPECTED_NEGATIVE_MUTATIONS}-rejected",
        "implementation_authorized=no", "cpu_off_authorized=no",
        "build_authorized=no", "device_action_authorized=no", "device_action=none",
        "result=pass",
    ]


def validate_transcript(report: list[str], transcript_text: str | None = None) -> None:
    transcript_text = TRANSCRIPT.read_text(encoding="utf-8") if transcript_text is None else transcript_text
    expected = "\n".join(report + mutation_report()) + "\n"
    require(transcript_text == expected, "validation transcript is stale or contradictory")


def validate_authorization(report: list[str]) -> None:
    exact = {
        "implementation": "BLOCKED", "implementation_authorized": "no",
        "cpu_off_authorized": "no", "build_authorized": "no",
        "device_action_authorized": "no", "device_action": "none",
        "all_applicable_contract_rows_for_veto_relaxation": "REQUIRED",
        "current_cpu_boot_veto": "REQUIRED", "current_cpu_disable_veto": "REQUIRED",
        "result": "pass",
    }
    for key, value in exact.items():
        matches = [line for line in report if line.startswith(f"{key}=")]
        require(matches == [f"{key}={value}"],
                f"authorization marker changed or duplicated: {key}")
    forbidden = ("authorized=true", "authorized=yes", "device_action=deploy",
                 "device_action=shutdown", "veto=OPTIONAL", "implementation=READY")
    require(not any(token in line for line in report for token in forbidden),
            "report grants forbidden authorization")


def main() -> int:
    phase_rows = load_tsv(PHASE, PHASE_FIELDS)
    membership_rows = load_tsv(MEMBERSHIP, MEMBERSHIP_FIELDS)
    provider_rows = load_tsv(PROVIDER, PROVIDER_FIELDS)
    admission_rows = load_tsv(ADMISSION, ADMISSION_FIELDS)
    validate_phase(phase_rows)
    validate_membership(membership_rows)
    validate_provider(provider_rows)
    validate_admission(admission_rows)
    validate_documents()
    validate_evidence()
    report = validation_report(phase_rows, membership_rows, provider_rows, admission_rows)
    validate_authorization(report)
    validate_transcript(report)
    print("\n".join(report))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, OSError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
