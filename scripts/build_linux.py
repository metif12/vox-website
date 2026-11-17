#!/usr/bin/env python3
"""Cross-compile, then link the real target libpq instead of linuxroot's stubs."""

import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import shutil


def system_link_command(output, library, binary):
    commands = []
    for line in output.splitlines():
        try:
            parts = shlex.split(line.strip().removeprefix('> '))
        except ValueError:
            continue
        if parts:
            commands.append(parts)
    stubs = set()
    for command in commands:
        if '-c' in command and '-o' in command and any('pgport_stubs.c' in part for part in command):
            stubs.add(command[command.index('-o') + 1])
    for command in reversed(commands):
        if Path(command[0]).name in ('ld.lld', 'ld.lld.exe') and '-lpq' in command:
            linker = [str(library) if part == '-lpq' else part for part in command
                      if 'pgport_stubs.c.' not in part and part not in stubs]
            linker[linker.index('-o') + 1] = str(binary)
            return [*linker, '--allow-shlib-undefined']
    raise RuntimeError('Could not locate the V cross-link command; see build/linux-build.log.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--v', default='v')
    parser.add_argument('--vflags', default='-b c -memory-limit 10G')
    parser.add_argument('--path', required=True)
    parser.add_argument('--libpq', required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    library = args.libpq.resolve()
    if not library.is_file():
        raise SystemExit('Missing Linux libpq.so.5. Run ./deploy.sh or set LINUX_LIBPQ to the target library.')
    if library.read_bytes()[:4] != b'\x7fELF':
        raise SystemExit('LINUX_LIBPQ must be a Linux ELF shared library.')
    (root / 'build').mkdir(exist_ok=True)
    (root / 'bin').mkdir(exist_ok=True)
    binary = root / 'bin/vox-website-linux-amd64'
    # C debug information keeps the current compiler's per-build object directory
    # alive until the system-libpq relink. -prod still optimizes the executable.
    command = [args.v, *shlex.split(args.vflags), '-cg', '-showcc', '-keepc', '-path', args.path,
               '-os', 'linux', '-arch', 'amd64', '-prod', '-cflags',
               '-fno-lto -DMBEDTLS_NO_UDBL_DIVISION', '-o', str(binary), '.']
    before = set((root / 'bin').glob('.vox-website-linux-amd64.v3cc.*'))
    compiled = subprocess.run(command, cwd=root, capture_output=True, text=True)
    output = compiled.stdout + compiled.stderr
    (root / 'build/linux-build.log').write_text(output)
    if compiled.returncode:
        raise SystemExit(output[-6000:])
    # This V cross-linker ignores -ldflags. Reuse its emitted link command,
    # substituting the system library and omitting the incomplete pgport stubs.
    retained = set((root / 'bin').glob('.vox-website-linux-amd64.v3cc.*')) - before
    try:
        linker = system_link_command(output, library, binary)
        relative_objects = [part for part in linker if part.endswith('.o') and not Path(part).is_absolute()]
        directory = root
        if relative_objects:
            candidates = [path for path in retained if all((path / obj).is_file() for obj in relative_objects)]
            if len(candidates) != 1:
                raise RuntimeError('Could not identify the retained Linux compiler objects')
            directory = candidates[0]
        linked = subprocess.run(linker, cwd=directory, capture_output=True, text=True)
    except RuntimeError as error:
        binary.unlink(missing_ok=True)
        raise SystemExit(str(error))
    finally:
        for path in retained:
            shutil.rmtree(path)
    with (root / 'build/linux-build.log').open('a') as log:
        log.write('\nSystem libpq link:\n' + linked.stdout + linked.stderr)
    if linked.returncode:
        binary.unlink(missing_ok=True)
        raise SystemExit(linked.stdout + linked.stderr)
    report = {'compiler_command': command, 'linker_command': linker,
              'libpq_sha256': hashlib.sha256(library.read_bytes()).hexdigest(),
              'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest()}
    (root / 'build/linux-build.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Built Linux x86-64 release with the target server libpq.so.5.')


if __name__ == '__main__':
    main()
