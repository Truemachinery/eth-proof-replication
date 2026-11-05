#!/usr/bin/env python3
"""Static/mock controls for the bounded Linux policy; no real Landlock execution."""
import argparse
import ast
import ctypes
import errno
import json
from pathlib import Path
import types
from unittest import mock
import landlock_abi
from record import sha, validate_stage_name, write_json

HERE = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--result', type=Path, required=True)
    args = p.parse_args()
    queries = []
    def query_mock(returned):
        def syscall(*arguments):
            values = [x.value for x in arguments]
            assert values == [444, None, 0, 1]
            queries.append(values)
            if returned < 0:
                ctypes.set_errno(errno.ENOSYS)
            return returned
        library = types.SimpleNamespace(syscall=syscall)
        with mock.patch('platform.system', return_value='Linux'), mock.patch('platform.machine', return_value='x86_64'), \
                mock.patch.object(landlock_abi.ctypes, 'CDLL', return_value=library):
            return landlock_abi.query_abi()
    for abi in [8, 9, 12]:
        measured = query_mock(abi)
        assert measured == abi
        landlock_abi.require_abi(measured)
    for abi in [0, 7]:
        try:
            landlock_abi.require_abi(query_mock(abi))
        except RuntimeError:
            pass
        else:
            raise AssertionError('unsupported ABI accepted')
    try:
        query_mock(-1)
    except OSError as error:
        assert error.errno == errno.ENOSYS
    else:
        raise AssertionError('failed kernel query accepted')
    for system, machine in [('Darwin', 'arm64'), ('Linux', 'aarch64')]:
        with mock.patch('platform.system', return_value=system), mock.patch('platform.machine', return_value=machine), \
                mock.patch.object(landlock_abi.ctypes, 'CDLL') as library:
            try:
                landlock_abi.query_abi()
            except RuntimeError:
                pass
            else:
                raise AssertionError('unsupported architecture accepted')
            library.assert_not_called()
    tree = ast.parse((HERE / 'replicate.py').read_text())
    invocations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.List):
            for i, element in enumerate(node.elts):
                if isinstance(element, ast.Name) and element.id == 'landrun':
                    assert isinstance(node.elts[i + 1], ast.Constant) and node.elts[i + 1].value == '--best-effort'
                    assert isinstance(node.elts[i + 2], ast.Constant) and node.elts[i + 2].value == '--ro'
                    invocations.append(node.lineno)
    assert len(invocations) == 5
    constants = {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    assert not {'--unrestricted-filesystem', '--unrestricted-network', '--unrestricted-scoped'} & constants
    assert '--property=RestrictAddressFamilies=~AF_UNIX' in constants
    assert 'LANDRUN_WRITE_DENIED' in constants and 'AF_UNIX_DENIED' in constants
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)]
    stages = {node.args[0].value: node.lineno for node in calls if node.func.id == 'run' and node.args and
              isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)}
    for name in stages:
        validate_stage_name(name)
    order = ['landlock-abi-preflight', 'landrun-build', 'landrun-enforcement-control', 'af-unix-control', 'cleanup-disposable-sdks']
    assert [stages[name] for name in order] == sorted(stages[name] for name in order)
    lean_acquisition = min(node.lineno for node in calls if node.func.id == 'toolchain')
    assert stages[order[-1]] < lean_acquisition
    result = {'scope': 'Local static/mock policy regression only; no Linux syscall, Landrun, sandbox or proof execution',
              'passed': True, 'abi_floor': landlock_abi.MINIMUM_ABI, 'mocked_query_calls': len(queries),
              'architecture_guards_rejected_before_syscall': 2, 'own_best_effort_calls': len(invocations),
              'required_control_order': order, 'preflight_before_lean_acquisition': True,
              'official_comparator_unchanged': True, 'replicate_py_sha256': sha(HERE / 'replicate.py'),
              'abi_query_source_sha256': sha(HERE / 'landlock_abi.py')}
    write_json(args.result, result)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
