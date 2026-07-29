#!/usr/bin/env python3
"""Exercise Candidate Photon r2's source-pinned, storage-inert contracts."""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
import candidate_photon as cp


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
EXPERIMENT_DIR = SCRIPT_DIR.parent
R1_SOURCE = EXPERIMENT_DIR / "initramfs/photon-probe-r1.c"
R2_SOURCE = EXPERIMENT_DIR / "initramfs/photon-probe.c"
PROBE_VALIDATOR = SCRIPT_DIR / "validate-photon-probe.py"
INITRAMFS_VALIDATOR = SCRIPT_DIR / "validate-photon-initramfs.py"
DEFAULT_ARTIFACT = (
    pathlib.Path.home()
    / "artifacts/boot-candidates-photon-r2-calibrated"
    / f"{cp.ARTIFACT_PREFIX}{cp.RAW_SHA256[:8]}"
)
DEFAULT_CASSINI_ARTIFACT = (
    pathlib.Path.home()
    / "artifacts/boot-candidates"
    / cp.CASSINI_ARTIFACT_DIR
)

R1_REGISTERS = (0x05, 0x06, 0x47)
R1_PREFILLS = (0xA1, 0xB2, 0xC3, 0xD4, 0xE5, 0xF6)
REQUEST_CONTRACT_VERSION = "photon-i2c-rdwr-v1"
REQUEST_CONTRACT_SHA256 = (
    "70a4428290a01e2a5aa99741881dbe189c13b7f995d4c8cffeab61c434151d81"
)
R2_CLASSIFIER_CASES = (
    (
        "post-reference-tuple",
        (0xD9, 0xD0, 0xC0, 0xD9, 0xD0, 0xC0),
        0x3F,
    ),
    ("post-all-zero", (0x00, 0x00, 0x00, 0x00, 0x00, 0x00), 0x3F),
    (
        "post-pass-tuples-equal-other",
        (0x11, 0x22, 0x33, 0x11, 0x22, 0x33),
        0x3F,
    ),
    ("post-all-equal-pre", R1_PREFILLS, 0x00),
    (
        "post-mixed-equal-pre",
        (0xA1, 0x12, 0x23, 0x34, 0x45, 0x56),
        0x3E,
    ),
    (
        "post-none-equal-pre-pass-tuples-differ",
        (0x01, 0x02, 0x03, 0x04, 0x05, 0x06),
        0x3F,
    ),
)


class ContractError(RuntimeError):
    """A reproducibility or source-contract check failed."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def regular_bytes(path: pathlib.Path, label: str) -> bytes:
    try:
        info = path.lstat()
    except OSError as exc:
        raise ContractError(f"{label} is unavailable") from exc
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or info.st_size == 0:
        raise ContractError(f"{label} is missing, empty, or unsafe")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ContractError(f"{label} cannot be read") from exc


def safe_directory(path: pathlib.Path, label: str) -> pathlib.Path:
    try:
        info = path.lstat()
    except OSError as exc:
        raise ContractError(f"{label} is unavailable") from exc
    if path.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ContractError(f"{label} is missing or unsafe")
    return path.resolve()


def source_text(path: pathlib.Path, expected: str, label: str) -> str:
    data = regular_bytes(path, label)
    if digest(data) != expected:
        raise ContractError(f"{label} does not match its source pin")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContractError(f"{label} is not UTF-8") from exc


def braced_block(text: str, start_marker: str) -> str:
    start = text.find(start_marker)
    if start < 0:
        raise ContractError(f"source block is absent: {start_marker}")
    opening = text.find("{", start + len(start_marker))
    if opening < 0:
        raise ContractError(f"source block has no opening brace: {start_marker}")

    depth = 0
    index = opening
    state = "code"
    while index < len(text):
        char = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""
        if state == "code":
            if char == '"':
                state = "string"
            elif char == "'":
                state = "character"
            elif char == "/" and following == "*":
                state = "block-comment"
                index += 1
            elif char == "/" and following == "/":
                state = "line-comment"
                index += 1
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start : index + 1]
        elif state == "string":
            if char == "\\":
                index += 1
            elif char == '"':
                state = "code"
        elif state == "character":
            if char == "\\":
                index += 1
            elif char == "'":
                state = "code"
        elif state == "block-comment":
            if char == "*" and following == "/":
                state = "code"
                index += 1
        elif state == "line-comment" and char == "\n":
            state = "code"
        index += 1
    raise ContractError(f"source block is unterminated: {start_marker}")


def array_values(text: str, name: str) -> tuple[int, ...]:
    match = re.search(
        rf"static const uint8_t {re.escape(name)}\[[^\]]+\]\s*=\s*"
        r"\{(?P<body>.*?)\};",
        text,
        re.DOTALL,
    )
    if match is None:
        raise ContractError(f"source array is absent: {name}")
    body = match.group("body")
    values = tuple(int(value, 16) for value in re.findall(r"0x([0-9a-fA-F]+)U", body))
    residue = re.sub(r"0x[0-9a-fA-F]+U|[\s,]", "", body)
    if residue:
        raise ContractError(f"source array has an unexpected initializer: {name}")
    return values


def require_ordered(block: str, snippets: tuple[str, ...], label: str) -> None:
    cursor = 0
    for snippet in snippets:
        position = block.find(snippet, cursor)
        if position < 0:
            raise ContractError(f"{label} lacks ordered operation: {snippet}")
        cursor = position + len(snippet)


def validate_request_and_loop_contracts(r1_text: str, r2_text: str) -> None:
    r1_request = braced_block(r1_text, "static int read_one_register(")
    r2_request = braced_block(r2_text, "static int read_one_register(")
    if r1_request != r2_request:
        raise ContractError("r1/r2 read_one_register definitions differ")

    request = re.sub(r"\s+", " ", r2_request)
    require_ordered(
        request,
        (
            "uint8_t pointer = reg;",
            ".addr = PHOTON_I2C_ADDR, .flags = 0U, .len = 1U, .buf = &pointer,",
            ".addr = PHOTON_I2C_ADDR, .flags = PHOTON_I2C_M_RD, "
            ".len = 1U, .buf = value,",
            ".msgs = messages, .nmsgs = PHOTON_MESSAGE_COUNT,",
            "return ioctl(descriptor, PHOTON_I2C_RDWR, &request);",
        ),
        "read_one_register",
    )

    if array_values(r1_text, "photon_registers") != R1_REGISTERS:
        raise ContractError("r1 register array changed")
    if array_values(r2_text, "photon_registers") != R1_REGISTERS:
        raise ContractError("r2 register array changed")
    if array_values(r1_text, "photon_sentinels") != R1_PREFILLS:
        raise ContractError("r1 receive-prefill array changed")
    if array_values(r2_text, "photon_prefills") != R1_PREFILLS:
        raise ContractError("r2 receive-prefill array changed")

    contracts = (
        (
            r1_text,
            "sentinel",
            "photon_sentinels",
            "transfer_result",
            "attempted",
            "overwrite_mask",
        ),
        (
            r2_text,
            "prefill",
            "photon_prefills",
            "ioctl_result",
            "completed",
            "post_diff_mask",
        ),
    )
    normalized_traces: list[tuple[str, ...]] = []
    for text, prefill, prefills, result, completed, mask in contracts:
        loop = braced_block(
            text,
            "for (transaction = 0U; transaction < PHOTON_TRANSACTION_COUNT;",
        )
        operations = (
            "transaction = 0U",
            "transaction < PHOTON_TRANSACTION_COUNT",
            "transaction++",
            "index = transaction % PHOTON_REGISTER_COUNT",
            "pass = transaction / PHOTON_REGISTER_COUNT",
            f"{prefill} = {prefills}[transaction]",
            f"values[transaction] = {prefill}",
            "emit_marker(",
            "transaction + 1U",
            "photon_registers[index]",
            "errno = 0",
            f"{result} = read_one_register(",
            "descriptor, photon_registers[index], &values[transaction]",
            f"{result} != (int)PHOTON_MESSAGE_COUNT",
            "break;",
            f"{completed}++",
            f"values[transaction] != {prefill}",
            f"{mask} |= 1U << transaction",
            "emit_stdout(",
        )
        require_ordered(loop, operations, "transaction loop")
        if loop.count("read_one_register(") != 1:
            raise ContractError("transaction loop request count changed")
        normalized_traces.append(
            tuple(
                operation.replace(prefills, "prefills")
                .replace(prefill, "prefill")
                .replace(result, "request_result")
                .replace(completed, "completed")
                .replace(mask, "post_diff_mask")
                for operation in operations
            )
        )
    if normalized_traces[0] != normalized_traces[1]:
        raise ContractError("r1/r2 normalized transaction-loop order differs")


def validate_artifact(artifact: pathlib.Path) -> dict[str, pathlib.Path]:
    artifact = safe_directory(artifact, "calibrated Photon r2 artifact")
    expected_name = f"{cp.ARTIFACT_PREFIX}{cp.RAW_SHA256[:8]}"
    if artifact.name != expected_name:
        raise ContractError("calibrated Photon r2 artifact name changed")

    manifest_data = regular_bytes(artifact / "SHA256SUMS", "r2 artifact manifest")
    if digest(manifest_data) != cp.ARTIFACT_MANIFEST_SHA256:
        raise ContractError("calibrated Photon r2 artifact manifest changed")
    entries: dict[str, str] = {}
    for line in manifest_data.decode("ascii").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  \./([^/]+)", line)
        if match is None or match.group(2) in entries:
            raise ContractError("r2 artifact manifest is malformed")
        entries[match.group(2)] = match.group(1)
    inventory = {member.name for member in artifact.iterdir()}
    if inventory != set(entries) | {"SHA256SUMS"}:
        raise ContractError("r2 artifact inventory differs from its manifest")
    for name, expected in entries.items():
        member = regular_bytes(artifact / name, f"r2 artifact member {name}")
        if digest(member) != expected:
            raise ContractError(f"r2 artifact member changed: {name}")

    paths = {
        "source": artifact / "photon-probe.c",
        "probe": artifact / cp.PROBE_MEMBER,
        "initramfs": artifact / cp.INITRAMFS_MEMBER,
        "boot": artifact / cp.BOOT_MEMBER,
        "padded": artifact / "boot2-padded.img",
    }
    exact = {
        "source": cp.PROBE_SOURCE_SHA256,
        "probe": cp.PROBE_BINARY_SHA256,
        "initramfs": cp.INITRAMFS_SHA256,
        "boot": cp.RAW_SHA256,
        "padded": cp.PADDED_SHA256,
    }
    for name, expected in exact.items():
        if digest(regular_bytes(paths[name], f"calibrated r2 {name}")) != expected:
            raise ContractError(f"calibrated Photon r2 {name} identity changed")
    if paths["boot"].stat().st_size != int(cp.RAW_SIZE):
        raise ContractError("calibrated Photon r2 raw size changed")
    return paths


def run_checked(command: list[str], label: str) -> str:
    environment = dict(os.environ)
    environment.update(
        {
            "LC_ALL": "C",
            "PYTHONDONTWRITEBYTECODE": "1",
            "SOURCE_DATE_EPOCH": "0",
        }
    )
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    if result.returncode != 0:
        raise ContractError(f"{label} failed")
    return result.stdout


def validate_components(
    paths: dict[str, pathlib.Path], cassini_artifact: pathlib.Path
) -> None:
    cassini = safe_directory(cassini_artifact, "exact Cassini artifact")
    if cassini.name != cp.CASSINI_ARTIFACT_DIR:
        raise ContractError("exact Cassini artifact name changed")
    baseline = cassini / cp.CASSINI_INITRAMFS_MEMBER
    if digest(regular_bytes(baseline, "exact Cassini initramfs")) != (
        cp.CASSINI_INITRAMFS_SHA256
    ):
        raise ContractError("exact Cassini initramfs identity changed")

    probe_output = run_checked(
        [
            sys.executable,
            str(PROBE_VALIDATOR),
            "--source",
            str(R2_SOURCE),
            "--binary",
            str(paths["probe"]),
        ],
        "exact Photon probe validator",
    )
    if (
        "validation=photon-fixed-rx-sentinel-probe\n" not in probe_output
        or f"source_sha256={cp.PROBE_SOURCE_SHA256}\n" not in probe_output
        or f"binary_sha256={cp.PROBE_BINARY_SHA256}\n" not in probe_output
    ):
        raise ContractError("exact Photon probe validator output changed")

    initramfs_output = run_checked(
        [
            sys.executable,
            str(INITRAMFS_VALIDATOR),
            "--baseline",
            str(baseline),
            "--candidate",
            str(paths["initramfs"]),
            "--source",
            str(R2_SOURCE),
            "--helper",
            str(paths["probe"]),
        ],
        "exact Photon initramfs validator",
    )
    if (
        "validation=photon-exact-cassini-one-member-byte-delta\n"
        not in initramfs_output
        or f"candidate_sha256={cp.INITRAMFS_SHA256}\n" not in initramfs_output
    ):
        raise ContractError("exact Photon initramfs validator output changed")


def c_bytes(values: tuple[int, ...]) -> str:
    return ", ".join(f"0x{value:02x}U" for value in values)


def classifier_harness(source_name: str) -> str:
    case_lines = "\n".join(
        "    { "
        + f'"{name}", {{ {c_bytes(values)} }}, 0x{mask:02x}U'
        + " },"
        for name, values, mask in R2_CLASSIFIER_CASES
    )
    return f"""\
#define main photon_probe_program_main
#include "{source_name}"
#undef main

struct classifier_case {{
    const char *expected;
    uint8_t values[PHOTON_TRANSACTION_COUNT];
    unsigned int post_diff_mask;
}};

static const struct classifier_case cases[] = {{
{case_lines}
}};

int main(void)
{{
    size_t index;

    for (index = 0U; index < sizeof(cases) / sizeof(cases[0]); index++) {{
        const char *actual = classify_complete_post(
            cases[index].values, cases[index].post_diff_mask);

        if (strcmp(actual, cases[index].expected) != 0)
            return (int)index + 1;
    }}
    puts("classifier_cases=6");
    puts("classifier_result=passed");
    return 0;
}}
"""


def compile_include_harness(
    revision: str,
    source_data: bytes,
    program: str,
    purpose: str,
    temporary: pathlib.Path,
) -> str:
    source_name = f"photon-probe-{revision}.c"
    source_copy = temporary / source_name
    harness = temporary / f"{purpose}-harness-{revision}.c"
    executable = temporary / f"{purpose}-harness-{revision}"
    source_copy.write_bytes(source_data)
    harness.write_text(
        program,
        encoding="utf-8",
        newline="\n",
    )
    compiler = shutil.which("cc")
    if compiler is None:
        raise ContractError("C compiler is unavailable")
    run_checked(
        [
            compiler,
            "-std=c11",
            "-O2",
            "-Wall",
            "-Wextra",
            "-Werror",
            str(harness),
            "-o",
            str(executable),
        ],
        f"generated {revision} {purpose} harness compilation",
    )
    return run_checked(
        [str(executable)], f"generated {revision} {purpose} harness"
    )


def test_classifier(r2_data: bytes, temporary: pathlib.Path) -> None:
    source_name = "photon-probe-r2.c"
    output = compile_include_harness(
        "r2",
        r2_data,
        classifier_harness(source_name),
        "classifier",
        temporary,
    )
    if output != "classifier_cases=6\nclassifier_result=passed\n":
        raise ContractError("generated r2 classifier harness output changed")


def request_harness(source_name: str, prefills_name: str) -> str:
    return f"""\
#define _POSIX_C_SOURCE 200809L

#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/ioctl.h>

static int contract_ioctl(int descriptor, unsigned long request, ...);

#define ioctl contract_ioctl
#define main photon_probe_program_main
#include "{source_name}"
#undef main
#undef ioctl

struct request_record {{
    int descriptor;
    unsigned long request;
    uint32_t nmsgs;
    uint16_t write_addr;
    uint16_t write_flags;
    uint16_t write_len;
    uint8_t write_byte;
    uint16_t read_addr;
    uint16_t read_flags;
    uint16_t read_len;
    uint8_t read_prefill;
    uint8_t simulated_post;
}};

static struct request_record records[PHOTON_TRANSACTION_COUNT];
static unsigned int call_count;

static int contract_ioctl(int descriptor, unsigned long request, ...)
{{
    struct photon_i2c_rdwr_ioctl_data *data;
    struct photon_i2c_msg *messages;
    struct request_record *record;
    va_list arguments;

    va_start(arguments, request);
    data = va_arg(arguments, struct photon_i2c_rdwr_ioctl_data *);
    va_end(arguments);
    if (call_count >= PHOTON_TRANSACTION_COUNT || data == NULL ||
        data->nmsgs != PHOTON_MESSAGE_COUNT || data->msgs == NULL)
        return -1;
    messages = data->msgs;
    if (messages[0].buf == NULL || messages[1].buf == NULL)
        return -1;

    record = &records[call_count];
    record->descriptor = descriptor;
    record->request = request;
    record->nmsgs = data->nmsgs;
    record->write_addr = messages[0].addr;
    record->write_flags = messages[0].flags;
    record->write_len = messages[0].len;
    record->write_byte = messages[0].buf[0];
    record->read_addr = messages[1].addr;
    record->read_flags = messages[1].flags;
    record->read_len = messages[1].len;
    record->read_prefill = messages[1].buf[0];
    record->simulated_post = (uint8_t)(0x80U + call_count);
    messages[1].buf[0] = record->simulated_post;
    call_count++;
    return (int)PHOTON_MESSAGE_COUNT;
}}

int main(void)
{{
    unsigned int transaction;

    for (transaction = 0U; transaction < PHOTON_TRANSACTION_COUNT;
         transaction++) {{
        uint8_t value = {prefills_name}[transaction];
        unsigned int register_index =
            transaction % PHOTON_REGISTER_COUNT;

        if (read_one_register(17, photon_registers[register_index], &value) !=
            (int)PHOTON_MESSAGE_COUNT)
            return 1;
        if (value != (uint8_t)(0x80U + transaction))
            return 2;
    }}
    if (call_count != PHOTON_TRANSACTION_COUNT)
        return 3;

    puts("serialization={REQUEST_CONTRACT_VERSION}");
    for (transaction = 0U; transaction < PHOTON_TRANSACTION_COUNT;
         transaction++) {{
        const struct request_record *record = &records[transaction];

        printf(
            "transaction=%u;register=0x%02x;prefill=0x%02x;"
            "descriptor=%d;request=0x%04lx;nmsgs=%u;"
            "write_addr=0x%04x;write_flags=0x%04x;write_len=%u;"
            "write_byte=0x%02x;read_addr=0x%04x;"
            "read_flags=0x%04x;read_len=%u;simulated_post=0x%02x;"
            "return=%u\\n",
            transaction + 1U, record->write_byte, record->read_prefill,
            record->descriptor, record->request, record->nmsgs,
            record->write_addr, record->write_flags, record->write_len,
            record->write_byte, record->read_addr, record->read_flags,
            record->read_len, record->simulated_post,
            PHOTON_MESSAGE_COUNT);
    }}
    return 0;
}}
"""


def canonical_request_contract() -> str:
    lines = [f"serialization={REQUEST_CONTRACT_VERSION}\n"]
    for transaction, prefill in enumerate(R1_PREFILLS):
        register = R1_REGISTERS[transaction % len(R1_REGISTERS)]
        lines.append(
            f"transaction={transaction + 1};register=0x{register:02x};"
            f"prefill=0x{prefill:02x};descriptor=17;request=0x0707;nmsgs=2;"
            "write_addr=0x0069;write_flags=0x0000;write_len=1;"
            f"write_byte=0x{register:02x};read_addr=0x0069;"
            "read_flags=0x0001;read_len=1;"
            f"simulated_post=0x{0x80 + transaction:02x};return=2\n"
        )
    return "".join(lines)


def test_request_contracts(
    r1_data: bytes, r2_data: bytes, temporary: pathlib.Path
) -> str:
    expected = canonical_request_contract()
    outputs = []
    for revision, source_data, prefills in (
        ("r1", r1_data, "photon_sentinels"),
        ("r2", r2_data, "photon_prefills"),
    ):
        source_name = f"photon-probe-{revision}.c"
        output = compile_include_harness(
            revision,
            source_data,
            request_harness(source_name, prefills),
            "request",
            temporary,
        )
        if output != expected:
            raise ContractError(
                f"generated {revision} request harness output changed"
            )
        outputs.append(output)
    if outputs[0] != outputs[1]:
        raise ContractError("r1/r2 generated request traces differ")
    contract_sha256 = digest(expected.encode("ascii"))
    if contract_sha256 != REQUEST_CONTRACT_SHA256:
        raise ContractError("canonical request-contract digest changed")
    return contract_sha256


def test_mutation_rejection(
    paths: dict[str, pathlib.Path], temporary: pathlib.Path
) -> None:
    mutated = temporary / "photon-probe.mutated"
    data = bytearray(regular_bytes(paths["probe"], "calibrated r2 probe"))
    data[-1] ^= 0x01
    mutated.write_bytes(data)
    environment = dict(os.environ)
    environment.update({"LC_ALL": "C", "PYTHONDONTWRITEBYTECODE": "1"})
    result = subprocess.run(
        [
            sys.executable,
            str(PROBE_VALIDATOR),
            "--source",
            str(R2_SOURCE),
            "--binary",
            str(mutated),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    if (
        result.returncode != 2
        or "error: calibrated Photon probe binary changed\n" != result.stderr
        or result.stdout
    ):
        raise ContractError("exact Photon probe validator accepted a mutation")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifact",
        type=pathlib.Path,
        default=DEFAULT_ARTIFACT,
        help="exact calibrated Photon r2 artifact",
    )
    parser.add_argument(
        "--cassini-artifact",
        type=pathlib.Path,
        default=DEFAULT_CASSINI_ARTIFACT,
        help="exact Candidate Cassini foundation artifact",
    )
    args = parser.parse_args()

    try:
        if platform.system() != "Linux" or platform.machine() != "aarch64":
            raise ContractError("run this harness in the Linux AArch64 recovery VM")
        r1_text = source_text(
            R1_SOURCE, cp.PHOTON_R1_SOURCE_SHA256, "source-pinned Photon r1"
        )
        r2_text = source_text(
            R2_SOURCE, cp.PROBE_SOURCE_SHA256, "source-pinned Photon r2"
        )
        validate_request_and_loop_contracts(r1_text, r2_text)
        paths = validate_artifact(args.artifact)
        validate_components(paths, args.cassini_artifact)
        with tempfile.TemporaryDirectory(prefix="photon-contracts-") as directory:
            temporary = pathlib.Path(directory)
            request_contract_sha256 = test_request_contracts(
                R1_SOURCE.read_bytes(),
                R2_SOURCE.read_bytes(),
                temporary,
            )
            test_classifier(R2_SOURCE.read_bytes(), temporary)
            test_mutation_rejection(paths, temporary)
    except (ContractError, OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("validation=photon-r2-contract-harness")
    print("revision=r2")
    print(f"r1_source_sha256={cp.PHOTON_R1_SOURCE_SHA256}")
    print(f"r2_source_sha256={cp.PROBE_SOURCE_SHA256}")
    print("read_one_register_request_structure=exact-r1-r2")
    print("register_order=05,06,47,05,06,47")
    print("receive_prefill_order=a1,b2,c3,d4,e5,f6")
    print("successful_loop_order=exact-r1-r2")
    print(f"request_contract_version={REQUEST_CONTRACT_VERSION}")
    print(f"ioctl_request_contract_sha256={request_contract_sha256}")
    print("generated_r1_request_include_compile_execute=passed")
    print("generated_r2_request_include_compile_execute=passed")
    print("r1_r2_request_contract=byte-identical")
    print("r2_classifier_branches=6-passed")
    print("probe_component_validator=passed")
    print("initramfs_component_validator=passed")
    print("calibrated_r2_artifact=passed")
    print("probe_binary_mutation=rejected")
    print("temporary_writes=tempdir-only")
    print("persistent_writes=none")
    print("device_access=none")
    print("device_storage_access=none")
    print("physical_bus_behavior=not-observed")
    print("result=passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
