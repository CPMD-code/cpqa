CPQA 0.1
========

Introduction
~~~~~~~~~~~~

CPQA is a Quality Assurance framework developed for CP2K and customised for CPMD.
CPQA runs and compares regression tests.

All information below belong to the original development branch.

Features
~~~~~~~~

- Run regression tests and compare outputs with a set of reference outputs.
  Reference outputs are created when the regression tests are executed for the
  first time, or when a test is reset.

- Parallel execution of test jobs and execution of parallel tests runs.

- Interaction with g95 memcheck.

- Automatic update to latest CVS version.


Additional features:

- More fine-grained parallelization. Jobs within one directory can be executed
  in parallel. Some test jobs depend on the output of other test jobs. Such
  dependencies can be defined with comments in the test inputs.

- All information about a test is contained in the comments of the test input
  file. There is no need for the files TEST_FILES, TEST_FILES_RESET, and
  TEST_TYPES. This reduces the chance on patch collisions when multiple people
  are resetting tests at the same time. The CP2K test directory is converted
  automatically into the a form that is suitable for CPQA.

- The selection of test inputs can be provided on the command line of
  cpqa-main.py. One can specify individual inputs and/or entire directories. One
  can also specify fast:n to execute only those tests that ran faster than n
  seconds during the reference run. Alternatively one may specify slow:n.

- The order of the tests is determined by their timing in reference computation.
  The slowest tests are executed first. If a test is new it gets priority over
  the other tests.

- Multiple tests, i.e. comparison of more than just one value, for one input
  file.

- Different types of tests, mainly absolute tests for which no reference is
  required:
    - Comparison between scalars from two output files in the same test run.
    - Test of the output by an external script.
    - Comparison to a predefined value, e.g. for checksums.
  In practice most absolute tests also act as regression tests.

- Only the files needed for the selection of tests are copied to a new working
  directory.

- Detailed html output with colored diffstats of test outputs that do not match
  the reference outputs.

- A progress indicator.

- Separation between configuration file and test software. One can easily update
  to a newer version of CPQA.

- ...

Missing features compared to do_regtest:

- ...


Standard Installation
~~~~~~~~~~~~~~~~~~~~~

You need python 2.4. Some external test scripts may have other dependencies,
e.g. numpy.

If you want to use the stable version of CPQA included in the CP2K source,
then just go to that directory:

    $ cd tools/cpqa

If you want to use the latest development version of CPQA, then download
the latest version with git:

    $ git clone git://github.com/tovrstra/cpqa.git
    $ cd cpqa

To activate CPQA, load the environment variables in loadenv.sh:

    $ . loadenv.sh

The dot+space in front of loadenv.sh is mandatory. When opening a new
terminal, the environment variables have to be loaded again.


Alternative Installation
~~~~~~~~~~~~~~~~~~~~~~~~

You need python 2.4. Some external test scripts may have other dependencies,
e.g. numpy.

This procedure may not work on some broken Linux distributions, including
Suse Linux. One may uncomment the line prefix=/usr/local in the file
/usr/lib*/python*/distutils/distutils.cfg to fix this issue.

If you want to use the stable version of CPQA included in the CP2K source,
then just go to that directory:

    $ cd tools/cpqa

If you want to use the latest development version of CPQA, then download
the latest version with git:

    $ git clone git://github.com/tovrstra/cpqa.git
    $ cd cpqa

Then install CPQA in your home directory.

    $ cd cpqa
    $ ./setup.py install --home=~

Make sure the following two enviroment variables are set

    $ export PATH=$PATH:$HOME/bin
    $ export PYTHONPATH=$PYTHONPATH:$HOME/lib/python


Usage
~~~~~

1) Create an empty work directory and add a file config.py with the following
   settings:

        cp2k_root='../..'
        arch='Linux-x86-64-g95'
        version='sdbg'
        nproc=2
        bin='${root}/exe/${arch}/cp2k.${version}'
        testsrc='${root}/tests'
        make='make ARCH=${arch} VERSION=${version} -j${nproc}'
        makedir='${root}/makefiles'
        #cvs_update='cvs update -dP'
        #nproc_mpi=1
        #mpi_prefix='mpirun -np %i'

   Change the settings to suit your purposes.

2) Run the tests a first time with a version of CP2K you trust. This step
   generates the reference outputs. In the following example we limit the
   tests to the Fist directory. cpqa-main.py first tries to compile the
   source code.

        $ cpqa-main.py in/Fist

   The reference outputs are stored in a directory with the prefix 'ref--'. Each
   test run also creates a directory 'tst--...'. A symbolic link
   'tst--...--last' always points to the directory with the outputs of the last
   test run.

3) Add some feature or fix some bug. Then run the tests again.

        $ cpqa-main.py in/Fist

   If things go wrong, you will notice error messages in the output.


After the execution of a test, the status of the test is marked by a series of
flags. They have the following meaning:

 D - DIFFERENT
    Some of the numbers in the output are different from the reference outputs.

 E - ERROR
    The driver script encountered in internal error.

 F - FAILED
    The CP2K binary returned a non-zero exit code.

 L - LEAK
    A memory leak warning was detected in the standard error.

 M - MISSING
    The output file could not be found.

 N - NEW
    There is no reference output for this test.

 O - OK
    All the tests for this input went fine. In the case of regression tests
    without reference outputs, the status is also OK.

 R - RESET
    An additional RESET directive was found in the input. The new output is
    copied to the reference directory.

 V - VERBOSE
    The CP2K binary write some data to the standard output or standard error.
    This is not considered to be erroneous. However, when the test does not have
    the OK flag, the standard output and standard error is included in the final
    error report.

 W - WRONG
    Some value in the output differs from the coresponding expected value.


Writing tests
~~~~~~~~~~~~~

Writing proper tests is an essential aspect of writing reliable software. It may
seem a waste of time at first, but you will soon notice that it save a lot of
time when hunting down bugs, or when refactoring parts of the code.

Basically a test is a CP2K input file with some additional tags that indicate
how the output has to be validated. The following types of tests are currently
supported by CPQA:

#CPQA TEST SCALAR regex column [expected [precision]]

    This just compares a scalar from the output with the corresponding value in
    the reference output. One may also specify a fixed expected value, and
    optionally a precision.

#CPQA TEST COMPARE-SCALAR prefix regex column [precision]

    This test compares a scalar from the output with a corresponding scalar
    from another test job. This other test job is supposed to be executed in the
    same test run. Therefore one must also add a dependency (see below).
    Additionally the value is also compared with the reference output. The
    arguments regex, column and precision have the same meaning is in the
    SCALAR test (see above).

#CPQA TEST SCRIPT script [script arguments]

    Calls an external test script to validate the output.

There is no limitation on the number of test associated with one input.


Meaning of the arguments:

regex
    A regular expression (may be quoted it if contains spaces) to select a
    line from the output.  The number will be taken from the last line in the
    output that matches the regular expression.

column
    An integer to select the column containing the scalar that must be checked.
    Counting starts from zero. The line is split into columns using white space
    characters as delimiters. Multiples white spaces are considered as one
    delimiter.

precision
    The maximum allowed relative error when comparing the value with a
    predefined reference value.

prefix
    The part of the output file without '.out' that contains the value to
    compare with. One should also add a dependency directive as explained below
    to make sure that the other job is executed first.

script
    A script that will get the arguments specified after the name of the script.
    It must have a zero return code when the test succeeds. In case of error,
    the script must give a non-zero return code, and it should also print some
    output that will be picked up by CPQA to explain what went wrong.

script arguments
    Custom arguments to the external test script


One may also add additional tags to indicate dependencies between test files.
Consider two test files: a.inp and b.inp. If we want a.inp to be executed before
b.inp, one has to add a line to the input file b.inp:

#CPQA DEPENDS a.inp


When a change in the CP2K source code intentionally affects some of the tests
outputs, one should reset the test such that upon the next test run, the
reference data are reset to the new values. This can be done by including the
following command in the input.

#CPQA RESET some comments

Also check out the script cpqa-reset.py that automates the larger part of
resetting test files. It directly modifies the TEST_FILES_RESET in the CP2K
source tree, which will be picked up by the importer in cpqa-main.py. This
guarantees that the reseted tests are also picked up by the do_regtest script.


Some basic heuristics are used to detect additional files that are used by a
given input file. This is needed when importing the tests from the CP2K source
tree and when copying the test inputs to a work directory. However, not all
additional inputs can be detected properly for technical reasons. One may use
the following directive to indicate that a test input requires another file to
be present.

#CPQA INCLUDE FILENAME.file

The heuristic algorithm works as follows:

1) Every input line is split into words separated by white space.
2) The first word is ignored. The following words are considered to be potential
   additional inputs
3) For each potential additional inputs, surrounding accents are stripped and
   it is tested if the file actually exists. If it exists, it is added to the
   list of extra inputs.

#CPQA PRERUN "any shell command"

Allows to execute any shell command BEFORE test execution.
