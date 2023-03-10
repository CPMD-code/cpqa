#!/usr/bin/env python
# CPQA is a Quality Assurance framework for CP2K.
# Copyright (C) 2010 Toon Verstraelen <Toon.Verstraelen@UGent.be>.
#
# This file is part of CPQA.
#
# CPQA is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# CPQA is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>
#
# --


import sys, os, shutil, datetime, cPickle, traceback
from optparse import OptionParser

from cpqa import TestInput, TestResult, harvest_test, Timer, tail


usage = """Usage: %prog bin tstpath refdir [mpi_prefix] [mpi_suffix]

This script is called by cpqa-main.py to run a test job and validate the output.
It should not be used directly.
"""


def parse_args():
    parser = OptionParser(usage)
    (options, args) = parser.parse_args()
    if len(args) == 4:
        bin, path_inp, refdir, ppdir = args
        mpi_prefix = ''
        mpi_suffix = ''
    elif len(args) == 5:
        bin, path_inp, refdir, ppdir, mpi_prefix = args
        mpi_suffix = ''
    elif len(args) == 6:
        bin, path_inp, refdir, ppdir, mpi_prefix, mpi_suffix = args
    else:
        raise TypeError('Expecting four or five arguments.')
    return bin, path_inp, refdir, ppdir, mpi_prefix, mpi_suffix


def print_log_line(path_inp, flags, sec_bin, sec_all):
    print "CPQA-PREFIX",
    tag = ''
    for key, value in sorted(flags.iteritems()):
        if value:
            tag += key[0].upper()
        else:
            tag += "-"
    print tag,
    print '%6.2f' % sec_bin,
    print '%6.2f' % (sec_all-sec_bin),
    print path_inp


def run_test(bin, mpi_prefix, mpi_suffix, pp_dir, test_input):
    dirname, fn_inp = os.path.split(test_input.path_inp)
    fn_out = os.path.basename(test_input.path_out)
    fn_ppdir = pp_dir
    fn_stderr = os.path.basename(test_input.path_stderr)
    command = 'cd ./%s; %s %s %s %s %s > %s 2> %s' % (
        dirname, mpi_prefix, bin, fn_inp, fn_ppdir, mpi_suffix, fn_out, fn_stderr
    )
    timer_bin = Timer()
    retcode = os.system(command)
    timer_bin.stop()
    return retcode, timer_bin

def pre_run_command(test_input):
    dirname, fn_inp = os.path.split(test_input.path_inp)
    f = open(os.path.join(dirname,fn_inp))
    retcode=0
    for line in f:
        if line.startswith('#CPQA '):
            line = line[6:].strip()
            if line.startswith('PRERUN '):
                fn_extra = line[7:].strip()
                command = 'cd ./%s;"%s"' % (dirname, fn_extra)
                retcode = retcode+os.system(command)
    f.close()
    return retcode

def find_mem_leaks(fn_stderr):
    result = False
    f = open(fn_stderr)
    for line in f:
        if line.startswith('Remaining memory:'):
            result = True
            break
    f.close()
    return result


def main():
    timer_all = Timer()
    # Get command line arguments
    bin, path_inp, refdir, pp_dir, mpi_prefix, mpi_suffix = parse_args()
    test_input = TestInput('./', path_inp)
    refdir = os.path.join('..', refdir)
    # Flags to display the status of the test.
    flags = {}
    # To record error messages of this script:
    messages = []
    # Execute any PRE-RUN instruction (runtime dependencies)
    retcode = pre_run_command(test_input)
    # Run test job
    retcode, timer_bin = run_test(bin, mpi_prefix, mpi_suffix, pp_dir, test_input)
    flags['failed'] = (retcode != 0)
    # Get the last 20 lines
    last_out_lines = tail(test_input.path_out)
    last_stderr_lines = tail(test_input.path_stderr)
    flags['verbose'] = len(last_stderr_lines) > 0 
    # Detect memory leaks in teh stderr
    flags['leak'] = find_mem_leaks(test_input.path_stderr)
    # Check on refdir
    flags['new'] = not os.path.isfile(os.path.join(refdir, test_input.path_pp))
    # Extract the tests and count the number of resets
    if flags['new']:
        num_resets_ref = test_input.num_resets
    else:
        test_input_ref = TestInput(refdir, path_inp)
        num_resets_ref = test_input_ref.num_resets
    flags['reset'] = (test_input.num_resets > num_resets_ref)
    flags['error'] = False
    if test_input.num_resets < num_resets_ref:
        flags['error'] = True
        messages.append('Error: The number of reset directives decreased.')
    # Collect fragments from output for tests.
    flags['missing'] = False
    harvest_test(test_input, refdir, flags['new'], messages)
    # Do the actual tests.
    flags['wrong'] = False
    flags['different'] = False
    for test in test_input.tests:
        if not test.complete(flags['new']):
            flags['missing'] = True
        else:
            try:
                test.run(flags['new'])
            except Exception:
                messages.append(traceback.format_exc())
            if test.wrong is True:
                flags['wrong'] = True
            if test.different is True:
                flags['different'] = True
    # Determine error flag
    flags['error'] = len(messages) > 0
    # Determine the OK flag
    flags['ok'] = not (flags['wrong'] or (flags['different'] and not
                  flags['reset']) or flags['missing'] or flags['failed'] or
                  flags['error'] or flags['leak'])
    # Write the TestResult to a pickle file
    timer_all.stop()
    test_result = TestResult(
        path_inp, flags, timer_bin.seconds, timer_all.seconds,
        test_input.tests, messages, last_out_lines, 
        last_stderr_lines
    )
    f = open(test_input.path_pp, 'w')
    cPickle.dump(test_result, f, -1)
    f.close()
    # Copy the tests to the reference directory if needed.
    if (flags['new'] or flags['reset']) and flags['ok']:
        dstdir = os.path.join(refdir, os.path.dirname(test_input.path_pp))
        if not os.path.isdir(dstdir):
            os.makedirs(dstdir)
        shutil.copy(path_inp, dstdir)
        shutil.copy(test_input.path_out, dstdir)
        shutil.copy(test_input.path_pp, dstdir)
        shutil.copy(test_input.path_stderr, dstdir)
    # Print some screen output.
    print_log_line(path_inp, flags, timer_bin.seconds, timer_all.seconds)



if __name__ == '__main__':
    # Only run main when this script is executed as a program, i.e. not imported
    # as a module.
    main()
