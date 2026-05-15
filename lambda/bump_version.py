#!/usr/bin/env python3

import pathlib
import re
import sys


VERSION_PATTERN = re.compile(
    r'^__version__\s*=\s*"(\d+)\.(\d+)\.(\d+)"\s*$',
    re.MULTILINE,
)


def usage() -> None:
    print("Usage: bump_version.py <version.py>", file=sys.stderr)


def bump_patch(version_path: pathlib.Path) -> str:
    version_text = version_path.read_text(encoding="utf-8") if version_path.exists() else ""
    version_match = VERSION_PATTERN.search(version_text)

    if version_match:
        major, minor, patch = map(int, version_match.groups())
    else:
        major, minor, patch = 0, 0, -1

    new_version = f"{major}.{minor}.{patch + 1}"
    version_path.write_text(
        f'"""CloudLaunch Lambda package version."""\n\n__version__ = "{new_version}"\nVERSION = __version__\n',
        encoding="utf-8",
    )
    return new_version


def main() -> int:
    if len(sys.argv) != 2:
        usage()
        return 1

    print(bump_patch(pathlib.Path(sys.argv[1])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
