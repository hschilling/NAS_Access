from __future__ import print_function

import unittest
import os

from six.moves import cStringIO

from openmdao.api import Problem, Group
from openmdao.components.nas_access import NasAccess

DIRECTORY = os.path.dirname((os.path.abspath(__file__)))

# For the full, non-mocked test to work the following setup needs to be done on NAS Pleiades:

    # In the directory ~/openmdao/nas_access_testing, the contents are:
    # .:
    # total 4
    # drwx------ 2 hschilli a1501  87 Feb 12 07:11 data
    # -rw------- 1 hschilli a1501 731 Feb 12 07:12 nas_access_testing.qsub

    # ./data:
    # total 12
    # -rw------- 1 hschilli a1501   8 Feb 12 06:10 input.dat
    # -rw------- 1 hschilli a1501 366 Feb 12 06:19 nas_access_test_script.py

# where nas_access_test_script.py is a script that reads an input file of numbers 
#   and writes to an output file the sum

# The file nas_access_testing.qsub contains:
    # #!/bin/bash
    # #PBS -S /bin/bash
    # #PBS -N nas_access
    # #PBS -l select=1:ncpus=1:mpiprocs=1
    # #PBS -l walltime=0:10:00
    # #PBS -j oe
    # #PBS -W group_list=a1607
    # #PBS -m e
    # #PBS -q devel

    # export JOBDIR=/u/hschilli/openmdao/nas_access_testing/data
    # cd $JOBDIR

    # python nas_access_test_script.py

# The nas_access_testing.qsub file needs to have permissions of 700

# This needs to be added to the ~/.meshrc file:

    # /u/hschilli/openmdao/nas_access_testing/data
    # +qsub /u/hschilli/openmdao/nas_access_testing/nas_access_testing.qsub



class TestNasAccess(unittest.TestCase):

    def setUp(self):
        # self.startdir = os.getcwd()
        # self.tempdir = tempfile.mkdtemp(prefix='test_extcode-')
        # os.chdir(self.tempdir)

        self.top = Problem()
        self.top.root = Group()

        self.nas_access = NasAccess()
        self.top.root.add('nas_access', self.nas_access)

        self.nas_access.options['external_input_files'] = ['input.dat',]
        self.nas_access.options['external_output_files'] = ['output.dat',]
        self.nas_access.options['nas_working_directory'] = '/u/hschilli/openmdao/nas_access_testing/data'
        self.nas_access.options['nas_username'] = 'hschilli'
        self.nas_access.options['nas_hostname'] = 'pfe20'
        self.nas_access.options['remote_copy_command'] = 'scp' # could also be bbscp
        self.nas_access.options['sup_verbose'] = False
        self.nas_access.options['qsub_filepath'] = '/u/hschilli/openmdao/nas_access_testing/nas_access_testing.qsub'
        self.nas_access.options['qsub_options'] = '-N nas_access -l select=1:ncpus=1:mpiprocs=1 -l walltime=0:10:00 -j oe -W group_list=a1607 -m e -q devel' # to override what is in the qsub file
        self.nas_access.options['job_status_poll_delay'] = 0.0

        self.setup_out_stream = open(os.devnull, 'w')

    def tearDown(self):
        pass

    def test_normal(self):

        self.top.setup(check=True, out_stream=self.setup_out_stream)
        self.top.run()

    def test_bad_job_submit_bad_qsub_filepath(self):

        self.nas_access.options['qsub_filepath'] = '/u/hschilli/bass/learning/learning_mpi/no_such_file.qsub'

        self.top.setup(check=True, out_stream=self.setup_out_stream)
        try:
            self.top.run()
        except Exception as err:
            self.assertEqual(str(err),
                             ( "PBS job not started by NasAccess. qsub command used is: qsub -N nas_access "
                                "-l select=1:ncpus=1:mpiprocs=1 -l walltime=0:10:00 -j oe -W group_list=a1607 "
                                "-m e -q devel /u/hschilli/bass/learning/learning_mpi/no_such_file.qsub"
                                )
                             )

    def test_check_setup(self):

        stream = cStringIO()
        self.nas_access.options['nas_working_directory'] = ''
        self.nas_access.options['nas_hostname'] = ''
        self.nas_access.options['qsub_filepath'] = ''

        self.top.setup(check=True, out_stream=stream)
        msg = ( "##############################################\n"
             "Setup: Checking for potential issues...\n\n"
            "No recorders have been specified, so no data will be saved.\n\n"
            "The following components have no unknowns:\n"
            "nas_access\n\n"
            "The following components have no connections:\n"
            "nas_access\n"
            "nas_access:\n"
            "The option 'nas_working_directory' cannot be empty\n"
            "The option 'nas_hostname' cannot be empty\n"
            "The option 'qsub_filepath' cannot be empty\n\n\n\nSetup: Check complete.\n##############################################\n\n" )

        self.assertEqual(msg, stream.getvalue())

    def test_missing_input_files(self):

        self.nas_access.options['external_input_files'] = ['file_does_not_exist.txt',]

        self.top.setup(check=True, out_stream=self.setup_out_stream)
        try:
            self.top.run()
        except Exception as err:
            self.assertEqual(str(err),
                             "The following input files are missing: file_does_not_exist.txt")

    def test_missing_qsub_filepath(self):

        self.nas_access.options['qsub_filepath'] = ''

        #self.top.setup(check=True, out_stream=self.setup_out_stream)
        try:
            self.top.run()
        except Exception as err:
            self.assertEqual(str(err),
                             "The option 'qsub_filepath' must be set")

    def test_missing_nas_hostname(self):

        self.nas_access.options['nas_hostname'] = ''

        self.top.setup(check=True, out_stream=self.setup_out_stream)
        try:
            self.top.run()
        except Exception as err:
            self.assertEqual(str(err),
                             "The option 'nas_hostname' must be set")

    def test_missing_nas_working_directory(self):

        self.nas_access.options['nas_working_directory'] = ''

        self.top.setup(check=True, out_stream=self.setup_out_stream)
        
        try:
            self.top.run()
        except Exception as err:
            self.assertEqual(str(err),
                             "The option 'nas_working_directory' must be set")

    def test_sufficient_job_completion_timeout(self):

        # This command this job runs takes 30 seconds
        self.nas_access.options['qsub_filepath'] = '/u/hschilli/openmdao/nas_access_testing/nas_access_testing_long_job.qsub'
        self.nas_access.options['job_completion_timeout'] = 80.
        self.nas_access.options['job_status_poll_delay'] = 10.

        self.top.setup(check=True, out_stream=self.setup_out_stream)
        self.top.run()

    def test_insufficient_job_completion_timeout(self):

        # This command this job runs takes 30 seconds
        self.nas_access.options['qsub_filepath'] = '/u/hschilli/openmdao/nas_access_testing/nas_access_testing_long_job.qsub'
        self.nas_access.options['job_completion_timeout'] = 20.
        self.nas_access.options['job_status_poll_delay'] = 10.

        self.top.setup(check=True, out_stream=self.setup_out_stream)
 
        try:
            self.top.run()
        except Exception as err:
            self.assertEqual(str(err),
                             "NasAccess job time took longer than job_completion_timeout")
        finally:
            # need to clean up after this since the job is still running
            #   The test just stops checking to see if it is alive
            self.nas_access.delete_job()
            job_status = "Not finished"
            while(job_status != "Finished"):
                job_status = self.nas_access.job_status()


if __name__ == "__main__":
    unittest.main()
