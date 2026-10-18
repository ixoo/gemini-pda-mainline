#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""ROOT-only REAL GTK8 receipt/predecessor binding; unchanged reviewed boot2 guard."""

import importlib.util
import json
import os
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / '2026-10-01-mt6797-port0-header/install-passive.py'
SPEC = importlib.util.spec_from_file_location('port0_header_installer', SOURCE)
ADAPTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ADAPTER)
ADAPTER = ADAPTER.ADAPTER
INSTALLER = ADAPTER.INSTALLER
RELEASE = '7.1.3-gemini-a53-wifi-ccmp-stable-monitor'
# Expected last-installed GTK7, freshly verified by ROOT/GPT guard before write.
# Historical Gemian identity is not current identity or a deployment receipt.
PREDECESSOR_SHA = 'd9f0d3407b186b2d314c281af08dd7fcee0660e2a50863dd0e36eb8102c6536f'
MANIFEST_SHA = 'dd6fff6ee66b68bc0b77daca07e77df29de4f2dbf6189ad272a36b72de6c9273'
ADAPTER.HERE = HERE
ADAPTER.PREDECESSOR_SHA = PREDECESSOR_SHA
ADAPTER.INSTALLER.HERE = HERE
ADAPTER.INSTALLER.TOOL_NAME = 'install-ccmp-gtk8.py'
ADAPTER.INSTALLER.CANDIDATE_RECEIPT = 'results/ccmp-stable-monitor-candidate-gtk8.json'
ADAPTER.INSTALLER.EXPERIMENT = 'mt6797-wifi-ccmp-stable-monitor'
ADAPTER.INSTALLER.RECEIPT_NAME = 'mt6797-wifi-ccmp-stable-monitor-deployment-gtk8'
ADAPTER.INSTALLER.MANIFEST_SHA = MANIFEST_SHA
ADAPTER.MANIFEST_SHA = MANIFEST_SHA
ORIGINAL_SOURCES = ADAPTER.INSTALLER.sources


def sources():
    """Separate optional historical source storage from the credential checkout.

    The public install-boot2.sh changed after its reviewed pin. All original
    hashes and derive checks remain mandatory; no current file substitutes for
    a historical pin, and credentials remain in GEMINI_PRIVATE_REPO.
    """
    installer, parser = ORIGINAL_SOURCES()
    private = Path(os.environ['GEMINI_PRIVATE_REPO']).resolve(strict=True)
    source_root = Path(os.environ.get('GEMINI_INSTALLER_SOURCE_ROOT', private)).resolve(strict=True)
    pinned = installer['pinned_sources']
    installer = dict(installer)
    installer['pinned_sources'] = lambda repo=source_root: pinned(repo)
    return installer, parser


ADAPTER.INSTALLER.sources = sources


def validate(candidate, previous):
    ADAPTER.INSTALLER.boot_uuid(previous)
    candidate = Path(os.path.abspath(candidate))
    published = HERE / 'results/ccmp-stable-monitor-candidate-gtk8.json'
    ADAPTER.INSTALLER.require(candidate.is_dir() and not candidate.is_symlink() and
                              ADAPTER.INSTALLER.digest(published.read_bytes()) ==
                              MANIFEST_SHA, 'candidate receipt changed')
    expected = json.loads(published.read_text())
    ADAPTER.INSTALLER.require(expected['kernel_release'] == RELEASE and
                              expected['physical_admission'] is False and
                               expected.get('native_delivery_diag') is False and
                               expected.get('ccmp_stable_epoch') is True and
                               expected.get('mask_control') is True and
                               expected.get('group_pn_observe') is False and
                               expected.get('initial_gtk') is True and
                               expected.get('gtk_rx') is True and
                               expected.get('observation_window_ms') == 60000 and
                               expected.get('connected_channel_release') is True and
                               expected.get('join_grant_request_ms') == 9000 and
                               expected.get('connected_release_tail_ms') == 2500 and
                               expected.get('data_window_inside_grant') is False and
                               expected.get('post_release_traffic_required') is True and
                               expected.get('grant_horizon_decoupled') is True and
                               expected.get('early_grant_minimum_ms') == 9000 and
                               expected.get('checked_ccmp_max') == 1024 and
                               expected.get('total_rx_max') == 4096 and
                               expected.get('rx_bytes_max') == 2097152 and
                               expected.get('pid_reuse') is False and
                               expected.get('low_traffic_only') is True and
                               expected.get('gtk_arp_handoff_counter') is True and
                               expected.get('bss_timeout_observe') is True and
                               expected.get('owned_beacon_recency') is True and
                               expected.get('conditional_bss_timeout') is False and
                               expected.get('timeout_policy') == 'observe-count-and-refuse' and
                               expected.get('pm_connected_before_keys') is True and
                               expected.get('pm_abort_before_removals') is True and
                               expected.get('connection_monitor') is True and
                               expected.get('reconnect') is False and
                               expected.get('deauth_timeout_retirement') is True and
                               expected.get('deauth_timeout_bound_ms') == 750 and
                               expected.get('deauth_debt_limit_pages') == 1 and
                               expected.get('abort_waits_full_ledger') is True and
                               expected.get('late_retired_pid_only') is True and
                               expected.get('cleanup_waits_full_ledger') is False and
                               expected.get('cleanup_uses_latched_debt_floor') is True and
                               expected.get('bounded_page_debt_terminal') is True and
                               expected.get('healthy_stage_requires_whole_ledger') is True and
                               expected.get('pm_abort_before_deauth') is True and
                               expected.get('pm_relative_timing') is True and
                               expected.get('owned_beacons_at_data_end') is True and
                               expected.get('periodic_ping_offsets_s') == [10, 20, 30, 40, 50] and
                               expected.get('periodic_before_ssh_ack') is True and
                               expected.get('periodic_clock_resolution_ns') == 10000000 and
                               expected.get('periodic_leaf_sha256') == '55d15ff3499ed23eb41d10853955ce7634836b5040484c714126d31d558bd87f' and
                               ADAPTER.INSTALLER.digest((HERE / 'join-ccmp-gtk7.sh').read_bytes()) == '55d15ff3499ed23eb41d10853955ce7634836b5040484c714126d31d558bd87f' and
                               expected.get('beacon_clock_scope') ==
                               'existing owned-beacon queue admission; includes pre-data' and
                               expected.get('last_rx_clock_scope') ==
                               'strict PTK/GTK queue admission only' and
                               expected.get('kernel_profile') == 'mt6797-a53-wifi-ccmp-channel-release' and
                               expected.get('bootstrap') == 'normal-dhcp-only' and
                               expected.get('integration_source_commit') ==
                               'f7ae3f2efe0916081397ae4476cc1887a8f869c1' and
                              candidate.name == 'candidate-' +
                              expected['files']['boot.img']['sha256'],
                              'candidate scope or path changed')
    ADAPTER.INSTALLER.require({p.name for p in candidate.iterdir()} ==
                              set(expected['files']) | {'candidate.json'} and
                              (candidate / 'candidate.json').is_file() and
                              not (candidate / 'candidate.json').is_symlink() and
                              ADAPTER.INSTALLER.digest((candidate / 'candidate.json').read_bytes()) ==
                              MANIFEST_SHA, 'candidate inventory changed')
    for name, identity in expected['files'].items():
        path = candidate / name
        ADAPTER.INSTALLER.require(path.is_file() and not path.is_symlink() and
                                  path.stat().st_size == identity['bytes'] and
                                  ADAPTER.INSTALLER.digest(path.read_bytes()) ==
                                  identity['sha256'], 'candidate file changed: ' + name)
    raw = (candidate / 'boot.img').read_bytes()
    padded = (candidate / 'boot2-padded.img').read_bytes()
    ADAPTER.INSTALLER.require(len(padded) == 16777216 and
                              padded == raw + bytes(16777216 - len(raw)),
                              'full boot2 padding changed')
    return expected, candidate


ADAPTER.INSTALLER.validate = validate
ADAPTER.validate = validate
receipt = ADAPTER.INSTALLER.receipt


if __name__ == '__main__':
    ADAPTER.INSTALLER.main()
