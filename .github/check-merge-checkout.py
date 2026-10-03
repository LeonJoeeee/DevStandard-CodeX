#!/usr/bin/env python3
"""Verify the actual checked-out integration object, not merely its check name."""
import argparse
from pathlib import Path
import re
import subprocess
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path.cwd())
    parser.add_argument('--base',required=True)
    parser.add_argument('--head',required=True)
    args=parser.parse_args()
    if not all(re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}',pin) for pin in (args.base,args.head)):
        raise ValueError('full immutable base/head SHAs are required')
    result=subprocess.run(['git','-C',str(args.root),'rev-list','--parents','-n','1','HEAD'],
                          text=True,capture_output=True,check=True)
    actual=result.stdout.strip().split()
    if len(actual)!=3 or actual[1:] != [args.base,args.head]:
        raise ValueError('checkout is not the two-parent integration of the declared base and head')
    print(f'checked integration {actual[0]} of {args.base} and {args.head}')


if __name__=='__main__':
    try:
        main()
    except (OSError,ValueError,subprocess.CalledProcessError) as error:
        print(f'integration gate refused: {error}',file=sys.stderr)
        sys.exit(1)
