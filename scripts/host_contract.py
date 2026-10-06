"""Exact observed native V2 hosts admitted by installer, dispatcher and probes.

Admission lets a candidate be installed and tested; it does not manufacture runtime
qualification. Promote a candidate only after capturing its real native evidence.
"""
from hard_edges import require

QUALIFIED_HOST_VERSIONS = ('0.160.0', '0.160.1')
CANDIDATE_HOST_VERSIONS = ()
HOST_VERSIONS = QUALIFIED_HOST_VERSIONS + CANDIDATE_HOST_VERSIONS

HOST_HELP = ('explicit observed Codex version; qualified: '
             + ', '.join(QUALIFIED_HOST_VERSIONS)
             + ('; candidate pending native qualification: '
                + ', '.join(CANDIDATE_HOST_VERSIONS) if CANDIDATE_HOST_VERSIONS else ''))


def require_host_version(version):
    """Require an exact supplied observation; never default or normalize another host."""
    require(isinstance(version, str) and version in HOST_VERSIONS,
            'an observed known Codex V2 host version is required via --host-version; ' + HOST_HELP)
    return version


def host_qualification(version):
    require_host_version(version)
    return 'qualified' if version in QUALIFIED_HOST_VERSIONS else 'candidate'
