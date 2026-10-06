"""Launch a fixture consumer without Windows executable lookup for GitHub.

This bootstrap belongs only to tests. Production consumers continue using gh.
"""
import os
from pathlib import Path
import runpy
import subprocess
import sys


def fixture_command(args, executable):
    """Replace only GitHub argv with the exact Python double, or fail closed."""
    if not isinstance(args, (list, tuple)) or not args:
        raise AssertionError('fixture subprocess requires explicit argv')
    if Path(str(args[0])).name.lower() not in ('gh', 'gh.exe'):
        return args
    expected = Path(os.environ['GH_FIXTURE_SCRIPT']).resolve()
    if expected != Path(executable).resolve() or not expected.is_file():
        raise AssertionError('GitHub fixture executable is missing or changed')
    return [sys.executable, '-X', 'utf8', str(expected), *args[1:]]


def install_boundary():
    """Also used by fixture-local sitecustomize for direct consumer subprocesses."""
    executable = Path(os.environ['GH_FIXTURE_SCRIPT']).resolve()
    if not executable.is_file():
        raise AssertionError('GitHub fixture executable is missing')
    original = subprocess.Popen

    class FixturePopen(original):
        def __init__(self, args, *rest, **kwargs):
            if kwargs.get('shell') or kwargs.get('executable'):
                raise AssertionError('fixture refuses shell/executable subprocess override')
            super().__init__(fixture_command(args, executable), *rest, **kwargs)

    subprocess.Popen = FixturePopen


def main():
    install_boundary()
    script, *arguments = sys.argv[1:]
    sys.path.insert(0, str(Path(script).resolve().parent))
    sys.argv = [script, *arguments]
    runpy.run_path(script, run_name='__main__')


if __name__ == '__main__':
    main()
