#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Reproduce a whitespace-only kernel-style header revision and review patch."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import urllib.request

HERE = Path(__file__).resolve().parents[1]
PROPOSAL = HERE.parent
ROOT = PROPOSAL.parents[1]
FORMAT_VERSION = "Homebrew clang-format version 22.1.8"
ORIGINAL_PATCH = "2d261d775dedf5ad96e4529a67323adbc52a53332e22e0808101875b184bf8be"
# Maximal C operators matter: '+ +' must not be mistaken for '++'. Include
# directives as tokens and compare directive lines separately below.
LEX = re.compile(r'/\*.*?\*/|//[^\n]*|(?:u8|[uUL])?"(?:\\.|[^"\\])*"|'
                 r"(?:[uUL])?'(?:\\.|[^'\\])*'|[A-Za-z_]\w*|"
                 r'0[xX][0-9a-fA-F]+[uUlL]*|[0-9]+[uUlL]*|'
                 r'>>=|<<=|\.\.\.|\+\+|--|->|&&|\|\||<<|>>|<=|>=|==|!=|'
                 r'\+=|-=|\*=|/=|%=|&=|\^=|\|=|##|[^\s]', re.S)


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def tokens(text):
    return [token for token in LEX.findall(text)
            if not token.startswith(("/*", "//"))]


def transform(data, name):
    output = subprocess.check_output([
        "clang-format", "--style=file:" + str(HERE / "clang-format.yaml"),
        "--assume-filename=" + name], input=data, timeout=30).decode()
    # clang-format does not insert Linux's declaration/statement separators.
    output = re.sub(r'(?m)^(\t(?:int|unsigned int)[^;\n]*;)\n(?=\tif\b)',
                    r'\1\n\n', output)
    output = re.sub(r'(?m)^(};?)\n(?=\S)', r'\1\n\n', output)
    # Two formatter line breaks are discouraged by Linux checkpatch. These
    # exact shape replacements still pass the complete C-token oracle.
    if name == "hif_init_transaction.h":
        old = ("\terror = mt6797_init_validate_result(\n"
               "\t\tpacket, logical_bytes, t->expected_sequence, firmware_status);")
        prefix = "\terror = mt6797_init_validate_result("
        column = len(prefix.expandtabs(8))
        indent = "\t" * (column // 8) + " " * (column % 8)
        require(output.count(old) == 1, "result-call shape changed")
        output = output.replace(old, prefix + "packet, logical_bytes,\n" +
                                indent + "t->expected_sequence, firmware_status);")
    if name == "hif_ordinary_section.h":
        old = ("static inline int mt6797_section_begin(\n"
               "\tstruct mt6797_ordinary_section *s, struct mt6797_init_transaction *t,\n"
               "\tconst struct mt6797_hif_pio_io *io, enum mt6797_section_kind kind,\n"
               "\tconst unsigned char *config, size_t config_bytes, unsigned int sequence,\n"
               "\tconst unsigned char *data, size_t length)")
        prefix = "mt6797_section_begin("
        column = len(prefix)
        indent = "\t" * (column // 8) + " " * (column % 8)
        arguments = ["struct mt6797_ordinary_section *s,",
                     "struct mt6797_init_transaction *t,",
                     "const struct mt6797_hif_pio_io *io,",
                     "enum mt6797_section_kind kind,",
                     "const unsigned char *config, size_t config_bytes,",
                     "unsigned int sequence, const unsigned char *data,",
                     "size_t length)"]
        require(output.count(old) == 1, "section signature shape changed")
        output = output.replace(old, "static inline int\n" + prefix +
                                ("\n" + indent).join(arguments))
    original = data.decode()
    require(tokens(original) == tokens(output), "C token change: " + name)
    directives = lambda text: [line.strip() for line in text.splitlines()
                               if line.lstrip().startswith("#")]
    require(directives(original) == directives(output), "directive change: " + name)
    return output.encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write this revision's outputs")
    args = parser.parse_args()
    require(subprocess.check_output(["clang-format", "--version"]).decode().strip()
            == FORMAT_VERSION, "formatter version differs")
    spec = json.loads((PROPOSAL / "inputs.json").read_text())
    original_patch = (PROPOSAL / "0001-lib-mt6797-hif-compile.patch").read_bytes()
    require(digest(original_patch) == ORIGINAL_PATCH, "historical proposal changed")
    outputs = {}
    mapping = {}
    for name, expected in spec["protocol_headers"].items():
        original = subprocess.check_output([
            "git", "show", spec["protocol_commit"] + ":" +
            spec["protocol_directory"] + "/" + name], cwd=ROOT)
        require(digest(original) == expected, "reference hash: " + name)
        styled = transform(original, name)
        outputs["headers/" + name] = styled
        mapping[name] = {"reference_sha256": expected, "styled_sha256": digest(styled),
                         "identical_c_tokens": True, "identical_directives": True,
                         "token_count": len(tokens(original.decode()))}
    managed = ROOT / "artifacts/wifi-kernel-style"
    managed.mkdir(parents=True, exist_ok=True)
    require(not managed.is_symlink(), "unsafe managed root")
    lock_path = managed / ".lock"
    require(not lock_path.is_symlink(), "unsafe lock")
    lock = lock_path.open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    marker = "mt6797-hif-style-text-v1\n"
    for stale in managed.glob("prepare-*"):
        stamp = stale / ".owner"
        require(stale.is_dir() and not stale.is_symlink() and stamp.is_file()
                and not stamp.is_symlink() and stamp.read_text() == marker,
                "unowned stale scratch")
        require(all(not p.is_symlink() for p in stale.rglob("*")), "unsafe scratch link")
        shutil.rmtree(stale)
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_AUTHOR_NAME="MT6797 compile experiment",
               GIT_AUTHOR_EMAIL="nobody@example.invalid",
               GIT_COMMITTER_NAME="MT6797 compile experiment",
               GIT_COMMITTER_EMAIL="nobody@example.invalid",
               GIT_AUTHOR_DATE="2026-09-05T00:00:00+0000",
               GIT_COMMITTER_DATE="2026-09-05T00:00:00+0000")
    with tempfile.TemporaryDirectory(prefix="prepare-", dir=managed) as directory:
        tree = Path(directory)
        (tree / ".owner").write_text(marker)

        def git(*arguments):
            return subprocess.check_output(["git", *arguments], cwd=tree,
                                           env=env, stderr=subprocess.PIPE, timeout=30)

        git("init", "--quiet")
        for path, expected in spec["upstream_files"].items():
            url = ("https://raw.githubusercontent.com/torvalds/linux/" +
                   spec["upstream_commit"] + "/" + path)
            with urllib.request.urlopen(url, timeout=20) as response:
                data = response.read(262145)
            require(len(data) <= 262144 and digest(data) == expected, "upstream hash")
            target = tree / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        git("add", "lib")
        git("commit", "--quiet", "--no-gpg-sign", "-m", "Pinned upstream text inputs")
        base = git("rev-parse", "HEAD").decode().strip()
        mail = tree / "original.patch"
        mail.write_bytes(original_patch)
        git("apply", "--index", str(mail))
        git("commit", "--quiet", "--no-gpg-sign", "-m", "Historical compile proposal")
        for name in mapping:
            (tree / "lib/mt6797-hif-compile" / name).write_bytes(outputs["headers/" + name])
        outputs["header-style.patch"] = git("diff", "--", "lib/mt6797-hif-compile")
        git("add", "lib")
        expected_tree = git("write-tree")
        git("reset", "--soft", base)
        git("diff", "--cached", "--check")
        git("commit", "--quiet", "--no-gpg-sign", "-m",
            "lib: compile MT6797 HIF protocol with ordered MMIO\n\n"
            "Compile the bounded PIO, INIT and ordinary-section code against\n"
            "real Linux types and ordered MMIO. Kernel-style formatting preserves\n"
            "the reference C token stream and passes the original host fixtures.\n"
            "No initcall, device registration, mapping acquisition or runtime\n"
            "caller is provided. Internal experiment, not an upstream submission.\n\n"
            "Synthetic non-certifying author; no DCO is asserted.\n"
            "Assisted-by: LLM")
        patch = git("format-patch", "--stdout", "--no-signature", "-1")
        git("reset", "--hard", "--quiet", base)
        mail.write_bytes(patch)
        git("apply", "--index", str(mail))
        require(git("write-tree") == expected_tree, "revised patch replay differs")
        outputs["0001-lib-mt6797-hif-compile.patch"] = patch
    record = {"reference_commit": spec["protocol_commit"],
              "historical_patch_sha256": ORIGINAL_PATCH, "formatter": FORMAT_VERSION,
              "format_config_sha256": digest((HERE / "clang-format.yaml").read_bytes()),
              "headers": mapping, "revised_patch_sha256": digest(patch),
              "exact_patch_replay": True}
    outputs["mapping.json"] = (json.dumps(record, indent=2) + "\n").encode()
    for name, data in outputs.items():
        path = HERE / name
        if args.write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        else:
            require(path.read_bytes() == data, "reproduction mismatch: " + name)
    print("style_reproduction=PASS headers=7 tokens_and_directives=identical patch_replay=PASS")


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: exit(143))
    main()
