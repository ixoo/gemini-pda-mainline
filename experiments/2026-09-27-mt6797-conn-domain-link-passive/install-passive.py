#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind the reviewed boot2 installer to the passive CONN-domain-link image."""

import importlib.util
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / '2026-09-27-mt6797-consys-rails-passive/install-passive.py'
SPEC = importlib.util.spec_from_file_location('conn_provider_installer', SOURCE)
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)
INSTALLER.HERE = HERE
INSTALLER.EXPERIMENT = 'mt6797-conn-domain-link-passive'
INSTALLER.RECEIPT_NAME = 'mt6797-conn-domain-link-passive-deployment-1'
INSTALLER.MANIFEST_SHA = '0e87fb6ed95d2482c714c69455c1c6a6a6ee51fdbbc60111c9db183a3b3239b4'
PREDECESSOR_SHA = '99888ffbed5e3494377dbb7442e08ef20c2a7f6190922311ff8dc84bb05c4750'
ORIGINAL_ADAPT = INSTALLER.adapt


def adapt(source, candidate, previous):
    source = ORIGINAL_ADAPT(source, candidate, previous)
    anchor = 'already_current="$(single_value already_current "$probe_output")" || die '\
             "'invalid current-state evidence'\n"
    if source.count(anchor) != 1:
        raise ValueError('predecessor-check anchor changed')
    return source.replace(anchor,
                          '[[ "$predecessor_sha256" == ' + PREDECESSOR_SHA +
                          ' || "$predecessor_sha256" == "$CANDIDATE_SHA256" ]] || die '\
                          "'unexpected boot2 predecessor'\n" + anchor)


INSTALLER.adapt = adapt
MANIFEST_SHA = INSTALLER.MANIFEST_SHA
validate = INSTALLER.validate
receipt = INSTALLER.receipt


if __name__ == '__main__':
    INSTALLER.main()
