#!/usr/bin/env python3
"""Both actual release descriptors agree, and on release they agree with the tag."""
import argparse
import json
from pathlib import Path
import re
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--tag')
    args=parser.parse_args()
    versions=[json.loads((args.root/path).read_text())['version']
              for path in ('codex-method.json','.codex-plugin/plugin.json')]
    if not all(isinstance(v,str) and re.fullmatch(r'\d+\.\d+\.\d+',v) for v in versions):
        raise ValueError('release versions must be semver strings')
    if len(set(versions)) != 1:
        raise ValueError('release descriptors differ')
    if args.tag is not None and args.tag != 'v'+versions[0]:
        raise ValueError('release tag differs from descriptors')
    print('release descriptors in lockstep',versions[0])


if __name__=='__main__':
    try:
        main()
    except (OSError,ValueError,KeyError) as error:
        print(f'release gate refused: {error}',file=sys.stderr)
        sys.exit(1)
