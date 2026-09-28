#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind the reviewed boot2 installer to the gated Wi-Fi HIF candidate."""

import importlib.util
import json
import os
import shlex
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / '2026-09-27-mt6797-consys-rails-passive/install-passive.py'
SPEC = importlib.util.spec_from_file_location('passive_wlan_installer', SOURCE)
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)
INSTALLER.HERE = HERE
INSTALLER.EXPERIMENT = 'mt6797-wifi-hif-probe'
INSTALLER.RECEIPT_NAME = 'mt6797-wifi-hif-probe-deployment-1'
INSTALLER.MANIFEST_SHA = '64157d0eecee2addc7a3b7e47efe24aee6d962ba7cc1b1641194fa6bc94c2ef1'
PREDECESSOR_SHA = '4483a35bc23dc5d0bfca856848a70ca512e071caa89741098e0f461b65a9e141'
ORIGINAL_ADAPT = INSTALLER.adapt


def validate(candidate, previous):
    INSTALLER.boot_uuid(previous)
    candidate = Path(os.path.abspath(candidate))
    INSTALLER.require(candidate.is_dir() and not candidate.is_symlink(),
                      'candidate directory missing')
    published = HERE / 'results/candidate.json'
    INSTALLER.require(INSTALLER.digest(published.read_bytes()) == INSTALLER.MANIFEST_SHA,
                      'published candidate changed')
    expected = json.loads(published.read_text())
    INSTALLER.require(expected['kernel_release'] ==
                      '7.1.3-gemini-a53-wifi-hif-probe' and
                      expected['physical_admission'] is False,
                      'candidate scope changed')
    INSTALLER.require(candidate.name == 'candidate-' + expected['files']['boot.img']['sha256'],
                      'candidate path does not name its boot image')
    INSTALLER.require({p.name for p in candidate.iterdir()} ==
                      set(expected['files']) | {'candidate.json'} and
                      INSTALLER.digest((candidate / 'candidate.json').read_bytes()) ==
                      INSTALLER.MANIFEST_SHA,
                      'private candidate inventory changed')
    for name, identity in expected['files'].items():
        path = candidate / name
        INSTALLER.require(path.is_file() and not path.is_symlink() and
                          path.stat().st_size == identity['bytes'] and
                          INSTALLER.digest(path.read_bytes()) == identity['sha256'],
                          'candidate file changed: ' + name)
    raw = (candidate / 'boot.img').read_bytes()
    padded = (candidate / 'boot2-padded.img').read_bytes()
    INSTALLER.require(len(padded) == 16777216 and
                      padded == raw + bytes(16777216 - len(raw)),
                      'full boot2 padding changed')
    return expected, candidate


def adapt(source, candidate, previous):
    source = ORIGINAL_ADAPT(source, candidate, previous)
    anchor = 'already_current="$(single_value already_current "$probe_output")" || die '\
             "'invalid current-state evidence'\n"
    if source.count(anchor) != 1:
        raise ValueError('predecessor-check anchor changed')
    source = source.replace(anchor,
                          '[[ "$predecessor_sha256" == ' + PREDECESSOR_SHA +
                          ' || "$predecessor_sha256" == "$CANDIDATE_SHA256" ]] || die '\
                          "'unexpected boot2 predecessor'\n" + anchor)
    private_repo = Path(os.environ['GEMINI_PRIVATE_REPO']).resolve(strict=True)
    INSTALLER.require(private_repo.is_dir() and
                      (private_repo / 'artifacts/credentials/gemini_ed25519').is_file() and
                      (private_repo / 'artifacts/credentials/a53-recovery-known_hosts').is_file(),
                      'private credential root missing')
    repo_root = 'repo_root=' + shlex.quote(str(INSTALLER.REPO))
    INSTALLER.require(source.count(repo_root) == 1, 'repository-root anchor changed')
    return source.replace(repo_root,
                          'repo_root=' + shlex.quote(str(private_repo)))


INSTALLER.validate = validate
INSTALLER.adapt = adapt
MANIFEST_SHA = INSTALLER.MANIFEST_SHA
receipt = INSTALLER.receipt


if __name__ == '__main__':
    INSTALLER.main()
