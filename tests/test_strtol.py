import nose
import angr
import subprocess
import sys

import logging
l = logging.getLogger('angr.tests.strtol')

import os
test_location = str(os.path.dirname(os.path.realpath(__file__)))


def run_strtol(threads):
    if not sys.platform.startswith('linux'):
        raise nose.SkipTest()

    test_bin = os.path.join(test_location, "../../binaries/tests/x86_64/strtol_test")
    b = angr.Project(test_bin)

    initial_state = b.factory.entry_state(remove_options={angr.options.LAZY_SOLVES})
    pg = b.factory.simulation_manager(thing=initial_state, threads=threads)

    # find the end of main
    expected_outputs = {b"base 8 worked\n", b"base +8 worked\n", b"0x worked\n", b"+0x worked\n", b"base +10 worked\n",
                        b"base 10 worked\n", b"base -8 worked\n", b"-0x worked\n", b"base -10 worked\n", b"Nope\n"}
    pg.explore(find=0x400804, num_find=len(expected_outputs))
    nose.tools.assert_equal(len(pg.found), len(expected_outputs))

    # check the outputs
    pipe = subprocess.PIPE
    for f in pg.found:
        test_input = f.posix.dumps(0)
        test_output = f.posix.dumps(1)
        expected_outputs.remove(test_output)

        # check the output works as expected
        p = subprocess.Popen(test_bin, stdout=pipe, stderr=pipe, stdin=pipe)
        ret = p.communicate(test_input)[0]
        nose.tools.assert_equal(ret, test_output)

    # check that all of the outputs were seen
    nose.tools.assert_equal(len(expected_outputs), 0)


def test_strtol():
    yield run_strtol, None
    # yield run_strtol, 8


def test_strtol_long_string():

    # convert a 11-digit long string to a number.
    # there was an off-by-one error before.

    b = angr.load_shellcode(b"\x90\x90", "AMD64")
    state = b.factory.blank_state()
    state.memory.store(0x500000, b"98831114236\x00")

    state.libc.max_strtol_len = 11

    strtol = angr.SIM_LIBRARIES['libc.so.6'].get('strtol', arch=b.arch)
    strtol.state = state.copy()
    ret = strtol.run(0x500000, 0, 0)

    nose.tools.assert_true(strtol.state.satisfiable())
    nose.tools.assert_equal(len(strtol.state.solver.eval_upto(ret, 2)), 1)
    nose.tools.assert_equal(strtol.state.solver.eval_one(ret), 98831114236)


if __name__ == "__main__":
    test_strtol_long_string()
    run_strtol(None)
