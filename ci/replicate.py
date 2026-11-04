#!/usr/bin/env python3
"""Public-only, token-free Linux replication harness. Never dispatches a workflow."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
from record import Recorder, sha, write_json, validate_stage_name
from owned_cache import snapshot, restore

HERE = Path(__file__).resolve().parent
PINS = json.loads((HERE / 'pins.json').read_text())


def public_runner_guard(event, environment):
    repo = event.get('repository', {})
    if repo.get('private') is not False or repo.get('visibility') != 'public':
        raise RuntimeError('requires a verified public repository')
    if environment.get('GITHUB_ACTIONS') != 'true' or environment.get('RUNNER_ENVIRONMENT') != 'github-hosted':
        raise RuntimeError('requires a disposable GitHub-hosted Actions VM')
    if environment.get('GITHUB_EVENT_NAME') != 'workflow_dispatch':
        raise RuntimeError('manual workflow_dispatch only')
    if platform.system() != 'Linux' or platform.machine() != 'x86_64' or os.getuid() == 0:
        raise RuntimeError('requires a non-root Linux x86_64 runner')
    if environment.get('GITHUB_REPOSITORY') != repo.get('full_name'):
        raise RuntimeError('event repository mismatch')


def clean_environment(home):
    # Deliberately do not copy GITHUB_*, ACTIONS_*, SSH_*, cloud credentials, or secrets.
    return {'PATH': '/usr/local/go/bin:/usr/share/rust/.cargo/bin:' + os.environ.get('PATH', '/usr/bin:/bin'),
            'HOME': str(home), 'TMPDIR': str(home / 'tmp'), 'LANG': 'C.UTF-8',
            'LC_ALL': 'C.UTF-8', 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_TERMINAL_PROMPT': '0',
            'RUSTUP_HOME': os.environ.get('RUSTUP_HOME', str(Path.home() / '.rustup')),
            'CARGO_HOME': str(home / '.cargo'), 'LEAN_ABORT_ON_PANIC': '1', 'LEAN_NUM_THREADS': '2', 'CARGO_BUILD_JOBS': '2'}


def tree_identity(root, paths):
    rows = []
    for name in sorted(paths):
        p = root / name
        if p.is_symlink() or not p.is_file():
            raise RuntimeError('invalid regular source: ' + str(p))
        rows.append({'path': name, 'sha256': sha(p), 'size_bytes': p.stat().st_size})
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument('proof', choices=['openai', 'anthropic'])
    p.add_argument('--cleanup-disposable-sdks', action='store_true')
    p.add_argument('--mode', choices=['all', 'build', 'verify'], default='all')
    p.add_argument('--cache-directory', type=Path, required=True)
    args = p.parse_args()
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    public_runner_guard(event, os.environ)
    work = Path(os.environ['RUNNER_TEMP']).resolve() / ('eth-replication-' + args.proof)
    work.mkdir(exist_ok=False)
    home = work / 'home'
    (home / 'tmp').mkdir(parents=True)
    env = clean_environment(home)
    rec = Recorder(work / 'records', deadline=time.monotonic() + 330 * 60)
    project = None
    cache_context = None
    spec = PINS[args.proof]
    summary = {'schema': 'eth-ci-run/1', 'proof': args.proof, 'pins': spec,
               'host': {'platform': platform.platform(), 'uname': list(platform.uname()),
                        'cpu_count': os.cpu_count(), 'uid': os.getuid()},
               'harness': tree_identity(HERE, [x.name for x in HERE.iterdir() if x.is_file()]),
               'repository': event['repository']['full_name'],
               'status': 'incomplete', 'mode': args.mode, 'artifact_uploads': False,
               'actions_cache': 'Project-owned completed outputs only,2GiB/proof,4GiB retained total.',
               'export_retention': 'Ephemeral VM only; hashes and receipts remain in Actions logs.'}
    write_json(work / 'started.json', summary)
    print('RUN_START ' + json.dumps(summary, sort_keys=True), flush=True)

    def run(name, argv, cwd=work, environment=None, **kwargs):
        return rec.run(name, argv, cwd, environment or env, **kwargs)

    def checkout(name, url, commit, sparse=None):
        dest = work / name
        run(name + '-init', ['git', 'init', str(dest)])
        run(name + '-remote', ['git', '-C', str(dest), 'remote', 'add', 'origin', url])
        if sparse:
            run(name + '-sparse-init', ['git', '-C', str(dest), 'sparse-checkout', 'init', '--cone'])
            run(name + '-sparse-set', ['git', '-C', str(dest), 'sparse-checkout', 'set', *sparse])
        run(name + '-fetch', ['git', '-C', str(dest), 'fetch', '--depth=1', '--filter=blob:none', 'origin', commit])
        run(name + '-checkout', ['git', '-C', str(dest), 'checkout', '--detach', 'FETCH_HEAD'])
        actual = subprocess.check_output(['git', '-C', str(dest), 'rev-parse', 'HEAD'], env=env, text=True).strip()
        if actual != commit:
            raise RuntimeError('commit mismatch: ' + name)
        return dest

    def toolchain(version):
        folder = work / ('lean-' + version + '-linux')
        archive = work / ('lean-' + version + '-linux.tar.zst')
        url = 'https://github.com/leanprover/lean4/releases/download/v' + version + '/' + archive.name
        run('lean-' + version + '-download', ['curl', '--fail', '--location', '--retry', '3', '--output', str(archive), url])
        print('DOWNLOAD_IDENTITY ' + json.dumps({'url': url, 'sha256': sha(archive), 'bytes': archive.stat().st_size}), flush=True)
        run('lean-' + version + '-extract', ['tar', '--zstd', '-xf', str(archive), '-C', str(work)])
        archive.unlink()  # Ephemeral compressed duplicate only, never source/build evidence.
        if not (folder / 'bin/lean').is_file():
            raise RuntimeError('unexpected Lean release layout')
        return folder

    def proof_env(prefix):
        return dict(env, PATH=str(prefix / 'bin') + ':' + env['PATH'], LEAN_SYSROOT=str(prefix))

    def isolated(argv, cwd, environment, runtime_seconds=None):
        # The system manager sets uid before exec; proof/checker runs never have root privilege.
        runtime_seconds = min(runtime_seconds or 120 * 60, max(1, rec.deadline - time.monotonic() - 5))
        command = ['sudo', '-n', 'systemd-run', '--wait', '--pipe', '--collect',
                   '--service-type=exec', '--uid=' + str(os.getuid()), '--gid=' + str(os.getgid()),
                   '--property=CPUAccounting=yes', '--property=MemoryAccounting=yes',
                   '--property=RestrictAddressFamilies=~AF_UNIX', '--property=NoNewPrivileges=yes',
                   '--property=RuntimeMaxSec=' + str(max(1, int(runtime_seconds) - 5)),
                   '--property=TimeoutStopSec=5s', '--property=KillMode=control-group', '--property=MemoryMax=14G',
                   '--working-directory=' + str(cwd), '/usr/bin/env', '-i']
        return command + [k + '=' + v for k, v in sorted(environment.items())] + list(map(str, argv))

    try:
        # Exercise every version-derived stage label before SDK cleanup or any acquisition.
        for version in [spec['lean'], spec['comparator_lean']]:
            for suffix in ['download', 'extract']:
                validate_stage_name('lean-' + version + '-' + suffix)
        for exe in ['git', 'curl', 'tar', 'zstd', 'cc', 'go', 'cargo', 'sudo', 'systemd-run']:
            if not shutil.which(exe, path=env['PATH']):
                raise RuntimeError('missing runner dependency: ' + exe)
        run('landlock-abi-preflight', [sys.executable, HERE / 'landlock_abi.py'], timeout=30, required_text='LANDLOCK_ABI_ACCEPTED')
        tools_bin = work / 'tools-bin'
        tools_bin.mkdir()
        run('landrun-build', ['go', 'install', 'github.com/zouuup/landrun/cmd/landrun@' + PINS['tools']['landrun']],
            environment=dict(env, GOBIN=str(tools_bin), CGO_ENABLED='0'), timeout=1200)
        landrun = tools_bin / 'landrun'
        print('PREFLIGHT_LANDRUN_IDENTITY ' + json.dumps({'sha256': sha(landrun), 'size_bytes': landrun.stat().st_size}), flush=True)
        # Require actual write denial and separately tested AF_UNIX socket creation denial.
        denied = work / 'landrun-denied'
        denied.mkdir()
        probe = [sys.executable, '-c', 'from pathlib import Path\nimport sys\ntry: Path(sys.argv[1]).write_text("forbidden")\nexcept PermissionError: print("LANDRUN_WRITE_DENIED")\nelse: raise SystemExit(92)', str(denied / 'forbidden')]
        run('landrun-enforcement-control', isolated([landrun, '--best-effort', '--ro', '/', '--rw', '/dev', '-ldd', '-add-exec', '--', *probe], work, env),
            required_text='LANDRUN_WRITE_DENIED')
        if (denied / 'forbidden').exists():
            raise RuntimeError('Landrun write isolation failed')
        run('af-unix-control', isolated([sys.executable, '-c',
            'import socket\ntry: socket.socket(socket.AF_UNIX)\nexcept OSError: print("AF_UNIX_DENIED")\nelse: raise SystemExit(93)'], work, env),
            required_text='AF_UNIX_DENIED')
        if args.cleanup_disposable_sdks:
            # Guard above is mandatory before even constructing this fixed disposable-VM cleanup.
            run('cleanup-disposable-sdks', ['sudo', '-n', 'rm', '-rf', '--',
                '/usr/local/lib/android', '/usr/share/dotnet', '/opt/ghc', '/opt/hostedtoolcache/CodeQL'])
        free = shutil.disk_usage(work).free
        print('DISK_PREFLIGHT ' + json.dumps({'free_bytes': free, 'required_bytes': 26 * 1024**3}), flush=True)
        if free < 26 * 1024**3:
            raise RuntimeError('insufficient free disk: need26GiB after optional disposable SDK cleanup')
        run('host-inventory', ['bash', '-c', 'uname -a; lscpu; free -b; df -B1 .; go version; cargo --version; rustc --version; cc --version'])
        proof_prefix = toolchain(spec['lean'])
        tool_prefix = toolchain(spec['comparator_lean'])
        penv, tenv = proof_env(proof_prefix), proof_env(tool_prefix)
        run('proof-compiler-version', [proof_prefix / 'bin/lean', '--version'], environment=penv)
        run('tool-compiler-version', [tool_prefix / 'bin/lean', '--version'], environment=tenv)
        runtime = []
        for prefix in [proof_prefix, tool_prefix]:
            names = [str(x.relative_to(prefix)) for pattern in ['bin/lean', 'bin/lake', 'bin/leanchecker', 'lib/lean/*.so*']
                     for x in prefix.glob(pattern) if x.is_file() and not x.is_symlink()]
            runtime.append({'version_prefix': prefix.name, 'files': tree_identity(prefix, names)})
        write_json(work / 'runtime-identities.json', runtime)
        print('RUNTIME_IDENTITIES ' + json.dumps(runtime, sort_keys=True), flush=True)
        source = checkout('source', spec['repository'], spec['commit'], ['lean'] if args.proof == 'openai' else ['eth', '.github'])
        if args.proof == 'openai':
            run('prepare-byte-identical-workspace', [sys.executable, HERE / 'prepare_openai.py', '--base', work])
            project = work / 'workspace'
            manifest = json.loads((work / 'source-manifest.json').read_text())
            rows = sorted((x['path'], x['sha256'], x['size_bytes']) for x in manifest['files'])
            digest = hashlib.sha256(json.dumps(rows, separators=(',', ':')).encode()).hexdigest()
            if len(rows) != spec['closure_files'] or digest != spec['closure_sha256']:
                raise RuntimeError('pinned OpenAI source closure mismatch')
            original_config = source / 'lean/ComparatorChallenges/SubexponentialSAT.json'
        else:
            project = source / 'eth'
            original_config = project / 'comparator.json'
        tracked = subprocess.check_output(['git', '-C', str(source), 'ls-files', '-z'], env=env).decode().split('\0')
        source_rows = tree_identity(source, [x for x in tracked if x and (source / x).is_file()])
        write_json(work / 'source-identities.json', source_rows)
        print('SOURCE_IDENTITIES ' + json.dumps({'files': len(source_rows), 'manifest_sha256': sha(work / 'source-identities.json'),
              'proof_commit': spec['commit']}), flush=True)
        if (project / 'lean-toolchain').read_text().strip() != 'leanprover/lean4:v' + spec['lean']:
            raise RuntimeError('proof toolchain mismatch')
        lock_before = sha(project / 'lake-manifest.json') if args.proof == 'anthropic' else None
        if args.proof == 'openai':
            run('dependency-update', [proof_prefix / 'bin/lake', 'update'], project, penv)
        locked = json.loads((project / 'lake-manifest.json').read_text())
        if next(x for x in locked['packages'] if x['name'] == 'mathlib')['rev'] != spec['mathlib']:
            raise RuntimeError('mathlib pin mismatch')
        if args.proof == 'anthropic' and sha(project / 'lake-manifest.json') != lock_before:
            raise RuntimeError('Anthropic lockfile drift')
        write_json(work / 'dependency-lock.json', locked)
        print('DEPENDENCY_LOCK ' + json.dumps(locked, sort_keys=True), flush=True)
        project_sources = sorted(str(p.relative_to(project)) for p in project.rglob('*.lean') if '.lake' not in p.relative_to(project).parts and '.git' not in p.relative_to(project).parts)
        config_names = ['lean-toolchain', 'lakefile.lean' if args.proof == 'openai' else 'lakefile.toml', 'lake-manifest.json']
        project_identity = tree_identity(project, project_sources + config_names)
        cache_context = {'project_identity': project_identity, 'proof_runtime': runtime[0]}
        restore(project, args.proof, args.cache_directory, HERE, cache_context)
        run('mathlib-official-cache', [proof_prefix / 'bin/lake', 'exe', 'cache', 'get'], project, penv, timeout=2400)
        # Cache is a disclosed dependency trust assumption, then fresh kernel replay covers solution closure.
        comparator = checkout('comparator', PINS['tools']['comparator_repository'], spec['comparator'])
        exporter = checkout('exporter', PINS['tools']['exporter_repository'], spec['exporter'])
        nanoda = checkout('nanoda', PINS['tools']['nanoda_repository'], PINS['tools']['nanoda'])
        run('comparator-build', [tool_prefix / 'bin/lake', 'build', 'comparator'], comparator, tenv, timeout=1800)
        run('exporter-build-exact-proof-compiler', [proof_prefix / 'bin/lake', 'build', 'lean4export'], exporter, penv, timeout=1800)
        run('nanoda-build', ['cargo', 'build', '--release', '--locked', '--jobs', '2'], nanoda, env, timeout=1800)
        compbin, expbin, nanobin = (comparator / '.lake/build/bin/comparator', exporter / '.lake/build/bin/lean4export',
                                  nanoda / 'target/release/nanoda_bin')
        identities = [{'tool': n, 'sha256': sha(x), 'size_bytes': x.stat().st_size}
                      for n, x in [('comparator', compbin), ('exporter', expbin), ('nanoda', nanobin), ('landrun', landrun)]]
        write_json(work / 'tool-identities.json', identities)
        print('TOOL_IDENTITIES ' + json.dumps(identities), flush=True)
        run('create-two-slot-compiler-prefix', [sys.executable, HERE / 'create_gate.py', '--real-prefix', proof_prefix, '--output', work / 'compiler-gate'])
        genv = dict(penv, LEAN_SYSROOT=str(work / 'compiler-gate/prefix'), LAKE_OVERRIDE_LEAN='true',
                    ETH_LEAN_SLOTS='2', PATH=str(work / 'compiler-gate/prefix/bin') + ':' + env['PATH'])
        targets = ['+OAI.Algorithms.SubexponentialSAT.Main', '+ComparatorChallenges.SubexponentialSAT'] if args.proof == 'openai' else []
        if args.mode != 'verify':
            build_command = [landrun, '--best-effort', '--ro', '/', '--rw', '/dev', '--rwx', str(project / '.lake'),
                             '--rwx', str(work / 'compiler-gate'), '--rox', str(proof_prefix),
                             '--rox', str(Path(shutil.which('git', path=env['PATH'])).resolve()), '-ldd', '-add-exec']
            for key in ['PATH', 'HOME', 'LEAN_SYSROOT', 'LAKE_OVERRIDE_LEAN', 'ETH_LEAN_SLOTS', 'LEAN_NUM_THREADS', 'LEAN_ABORT_ON_PANIC']:
                build_command.extend(['--env', key])
            build_command.extend(['--', str(proof_prefix / 'bin/lake'), 'build', *targets])
            build_budget = max(10, rec.deadline - time.monotonic() - 15 * 60)
            run('source-build', isolated(build_command, project, genv, build_budget), project, env, timeout=build_budget)
        run('normal-real-prefix-trace-check', [proof_prefix / 'bin/lake', '--no-build', 'build', *targets], project, penv)
        if tree_identity(project, project_sources + config_names) != project_identity:
            raise RuntimeError('proof workspace source/config drift')
        if args.mode == 'build':
            summary['status'] = 'source-built-checks-pending'
            return
        fresh_command = [proof_prefix / 'bin/lake', 'env', landrun, '--best-effort', '--ro', '/', '--rw', '/dev', '-ldd', '-add-exec']
        for key in ['PATH', 'HOME', 'LEAN_PATH', 'LEAN_SYSROOT']:
            fresh_command.extend(['--env', key])
        fresh_command.extend(['--', proof_prefix / 'bin/leanchecker', '--fresh', spec['module']])
        run('fresh-original-version-leanchecker', isolated(fresh_command, project, penv),
            project, penv, timeout=120 * 60)
        config = json.loads(original_config.read_text())
        if config['permitted_axioms'] != PINS['allowed_axioms'] or config['theorem_names'] != spec['theorems'] or config.get('definition_names', []) != []:
            raise RuntimeError('unexpected upstream comparator target/axiom configuration')
        if config['solution_module'] != spec['module'] or config['challenge_module'] != spec['challenge']:
            raise RuntimeError('unexpected comparator modules')
        cenv = dict(penv, COMPARATOR_LANDRUN=str(landrun), COMPARATOR_LEAN4EXPORT=str(expbin), COMPARATOR_NANODA=str(nanobin))
        run('comparator-original-config', isolated([proof_prefix / 'bin/lake', 'env', compbin, original_config], project, cenv),
            project, timeout=120 * 60, required_text='Your solution is okay!')
        if config.get('enable_nanoda', False) != (args.proof == 'anthropic'):
            raise RuntimeError('unexpected upstream independent-kernel setting')
        print('ORIGINAL_COMPARATOR_CONFIG ' + json.dumps({'sha256': sha(original_config), 'config': config}), flush=True)
        export = work / 'selected-solution.ndjson'
        export_command = [landrun, '--best-effort', '--ro', '/', '--rw', '/dev', '-ldd', '-add-exec', '--env', 'PATH', '--env', 'HOME', '--env', 'LEAN_PATH',
                          '--', str(expbin), spec['module'], '--', *spec['theorems']]
        run('retained-target-export', isolated([proof_prefix / 'bin/lake', 'env', *export_command], project, penv),
            project, timeout=1800, stdout_file=export)
        nconfig = work / 'retained-export-nanoda-config.json'
        write_json(nconfig, {'use_stdin': False, 'export_file_path': str(export), 'permitted_axioms': PINS['allowed_axioms'],
                            'unpermitted_axiom_hard_error': True, 'num_threads': 2, 'nat_extension': True, 'string_extension': True})
        print('RETAINED_NANODA_CONFIG ' + json.dumps({'sha256': sha(nconfig), 'config': json.loads(nconfig.read_text())}), flush=True)
        if args.proof == 'openai':
            run('additional-retained-export-nanoda', isolated([landrun, '--best-effort', '--ro', '/', '--rw', '/dev', '-ldd', '-add-exec', '--', nanobin, nconfig], project, env),
                project, timeout=120 * 60)
            summary['independent_kernel'] = 'Pinned Nanoda on separately retained selected-target export; original Comparator config disables Nanoda.'
        else:
            summary['independent_kernel'] = 'Pinned Nanoda invoked by exact upstream Comparator config; separately retained export is additional provenance only.'
        if tree_identity(project, project_sources + config_names) != project_identity:
            raise RuntimeError('proof workspace source/config drift after checking')
        after = tree_identity(source, [x['path'] for x in source_rows])
        if after != source_rows:
            raise RuntimeError('upstream sources changed during checking')
        summary['status'] = 'all-required-stages-passed'
        summary['meaning'] = 'Named formal targets accepted by configured checks; mathematical/model interpretation requires separate review.'
    except BaseException as e:
        summary['error'] = repr(e)
        raise
    finally:
        if project is not None and cache_context is not None:
            try:
                summary['owned_cache'] = {k: v for k, v in snapshot(project, args.proof, args.cache_directory, HERE, cache_context).items() if k != 'files'}
            except BaseException as cache_error:
                summary['owned_cache_error'] = repr(cache_error)
        summary['stages'] = [{'name': x['name'], 'exit_code': x['exit_code'], 'wall_seconds': x['wall_seconds'],
                              'child_cpu_seconds': x['child_cpu_seconds'], 'raw_log_sha256': x['raw_log_sha256']} for x in rec.receipts]
        write_json(work / 'finished.json', summary)
        print('RUN_RECEIPT ' + json.dumps(summary, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
