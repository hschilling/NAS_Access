"""
.. _`nas_access.py`:
"""

import sys
import re
import time
import os

import subprocess

import numpy.distutils
from numpy.distutils.exec_command import find_executable

from openmdao.components.external_code import ExternalCode
from openmdao.util.shell_proc import STDOUT, DEV_NULL, ShellProc

class NasAccess(ExternalCode):
    """
    Run an external code on NAS as a component

    Default stdin is the 'null' device, default stdout is the console, and
    default stderr is ``error.out``.

    Options
    -------
    fd_options['force_fd'] :  bool(False)
        Set to True to finite difference this system.
    fd_options['form'] :  str('forward')
        Finite difference mode. (forward, backward, central) You can also set to 'complex_step' to peform the complex step method if your components support it.
    fd_options['step_size'] :  float(1e-06)
        Default finite difference stepsize
    fd_options['step_type'] :  str('absolute')
        Set to absolute, relative
    options['check_external_outputs'] :  bool(True)
        Check that all input or output external files exist
    options['command'] :  list([])
        command to be executed
    options['env_vars'] :  dict({})
        Environment variables required by the command
    options['external_input_files'] :  list([])
        (optional) list of input file names to check the pressence of before solve_nonlinear
    options['external_output_files'] :  list([])
        (optional) list of input file names to check the pressence of after solve_nonlinear
    options['poll_delay'] :  float(0.0)
        Delay between polling for command completion. A value of zero will use an internally computed default
    options['timeout'] :  float(0.0)
        Maximum time to wait for command completion. A value of zero implies an infinite wait

    The following are specific to the NasAccess Component:

    options['nas_username'] :  str('')
        Username on NAS
    options['nas_hostname'] :  str('')
        Name of host to transfer files from/to NAS
    options['nas_working_directory'] :  str('')
        Working directory on NAS where files will be transferred to/from
    options['remote_copy_command'] :  str('scp')
        Which remote copy command to use for file transfers: scp or bbscp
    options['sup_verbose'] :  bool(False)
        If True, use the -v option to sup to get more information about its progress
    options['job_status_poll_delay'] :  float(0.0)
        Delay between polling for job status command completion. Zero means no delay
    options['job_completion_timeout'] :  float(0.0)
        Maximum time to wait for job completion. A value of zero implies an infinite wait

    The following are specific to the qsub command. See the man page for qsub for more info:

    options['qsub_options'] :  str('')
        Use this string as options for the qsub command. This lets the user override the
        options set in the actual qsub file
    options['qsub_filepath'] :  str('')
        This is the path to the qsub file which will be submitted to the job scheduler
    """

    def __init__(self):
        super(NasAccess, self).__init__()

        self.DEV_NULL = DEV_NULL

        # Input options
        self.options.add_option('nas_username', '', 
                desc='Username on NAS')
        self.options.add_option('nas_hostname', '', 
                desc='Name of host to transfer files from/to NAS')
        self.options.add_option('nas_working_directory', '', 
                desc='The working directory on NAS where the command will be run from')

        self.options.add_option('remote_copy_command', 'scp', 
                desc='The command to use when copying files to/from NAS')
        self.options.add_option('sup_verbose', False, 
                desc='If True, use the -v option to sup to get more information about its progress')
        self.options.add_option('qsub_filepath', '', 
                desc='This is the path to the qsub file which will be submitted to the job scheduler')

        self.options.add_option('job_status_poll_delay', 0.0, lower=0.0,
            desc='Delay between polling for job status command completion. Zero means no delay')
        self.options.add_option('job_completion_timeout', 0.0, lower=0.0,
                                desc='Maximum time to wait for job completion. A value of zero implies an infinite wait')


        # Need to support all these PBS options
        #PBS -N sup_test
        #PBS -l select=1:ncpus=1:mpiprocs=1
        #PBS -l walltime=0:10:00
        #PBS -j oe
        #PBS -W group_list=a1607
        #PBS -m e
        #PBS -q devel

        # In the PBS file, there are these rules, BTW:
        # 1. You cannot use any of {-I, -S, -u, -V}
        # 2. You cannot use a remote host in -e or -o (i.e. via ":")
        # 3. You cannot use variables beginning with  LD_ or _RLD_ in -v
        # 4. You cannot request interactive or stage in -W
        # 5. If -e or -o is specified, the paths given must be writable via
        #    the SUP (i.e. you have authorized some higher level directory
        #    for writes in your ~/.meshrc)

        # e.g. -N sup_test -l select=1:ncpus=1:mpiprocs=1 -l walltime=0:10:00 -j oe -W group_list=a1607 -m e -q devel
        self.options.add_option('qsub_options', '', 
                desc='Use this string as options for the qsub command. This lets the user override '
                'the options set in the actual qsub file')

        self._sup = 'sup'
        # suppress message from find_executable function, we'll handle it
        numpy.distutils.log.set_verbosity(-1)
        self._sup_command_full_path = find_executable( self._sup )
        if not self._sup_command_full_path:
            raise RuntimeError( "The sup command, which is required to run the NasAccess Component, cannot be found" )

        self._job_id = None
        self._pbs_server = None
        self._scp_command = None
        self._nas_hostname = 'nas.nasa.gov'


    def check_setup(self, out_stream=sys.stdout):
        """Write a report to the given stream indicating any potential problems found
        with the current configuration of this ``Problem``.

        Args
        ----
        out_stream : a file-like object, optional
        """

        # check for some more options that need to be set
        if not self.options['nas_working_directory']:
            out_stream.write( "The option 'nas_working_directory' cannot be empty\n")
        if not self.options['nas_hostname']:
            out_stream.write( "The option 'nas_hostname' cannot be empty\n")
        if not self.options['qsub_filepath']:
            out_stream.write( "The option 'qsub_filepath' cannot be empty\n")

        # Check for options that are not fully implemented yet
        if self.options['remote_copy_command'] != 'scp' :
            out_stream.write( "The option 'remote_copy_command' currently must be 'scp'. Future versions will also support bbscp\n")

        # Check for missing input files
        missing_files = self._check_for_files(input=True)
        for iotype, path in missing_files:
            msg = "The %s file %s is missing\n" % ( iotype, path )
            out_stream.write(msg)

    def solve_nonlinear(self, params, unknowns, resids):
        """Runs the component
        """

        if not self.options['qsub_filepath']:
            raise ValueError("The option 'qsub_filepath' must be set")
        if not self.options['nas_working_directory']:
            raise ValueError("The option 'nas_working_directory' must be set")
        if not self.options['nas_hostname']:
            raise ValueError("The option 'nas_hostname' must be set")

        self._check_for_files(input=True)

        self._sup_command = self._sup
        if self.options['sup_verbose']:
            self._sup_command += ' -v'

        self._scp_command = self.options['remote_copy_command']
        if self._scp_command == 'scp':
            self._scp_command += ' -v' # need this so that the command outputs 
                                       # text to stderr which sup does not swallow
                                       # and we can use to see if the command executed properly

        # Transfer over the input files
        self._transfer_files_to_nas( self.options['external_input_files'] )

        # Submit job
        self._submit_job( self.options['qsub_filepath'] )
        
        # Wait for job to complete
        # Loop until job_status is complete
        # The status goes from Q to R to E to Finished when the job is completely done
        time_started = time.time()
        job_status = 'Unknown'
        while True:
            job_status = self.job_status()
            if job_status == 'Finished':
                break
            time_since_start = time.time() - time_started
            if self.options['job_completion_timeout'] > 0.0 and time_since_start > self.options['job_completion_timeout']:
                raise ValueError("NasAccess job time took longer than job_completion_timeout")
            time.sleep(self.options['job_status_poll_delay'])

        # Transfer over the output files
        self._transfer_files_from_nas( self.options['external_output_files'] )

        return

    def _submit_job(self, qsub_file_path):

        sup_command = self._sup_command
        sup_command += ' ssh ' + self.options['nas_hostname']

        qsub_command = 'qsub'
        qsub_command += ' ' + self.options['qsub_options']
        qsub_command += ' ' + qsub_file_path

        sup_command =  sup_command + ' ' + qsub_command

        self._process = \
            ShellProc(sup_command, self.stdin,
                      subprocess.PIPE, self.stderr, self.options['env_vars'])
        #self._logger.debug('PID = %d', self._process.pid)

        return_code = None
        error_msg = ''
        try:
            return_code, error_msg = \
                self._process.wait(self.options['poll_delay'], self.options['timeout'])
            self._job_id = None
            self._pbs_server = None
            for line in self._process.stdout:
                # look for a line like:
                # 1044002.pbspl1.nas.nasa.gov
                if self._nas_hostname in line:
                    self._job_id, self._pbs_server = line.split('.')[:2]
            if not self._job_id or not self._pbs_server:
                raise RuntimeError( 'PBS job not started by NasAccess. qsub command used is: ' + qsub_command )
               
        finally:
            self._process.close_files()
            self._process = None

        #### !!! check the return code ??
        # should be 0 and the message should be empty string


    def job_status(self):
        '''
        GRSLA40016394:P106502802-nas-access-component hschilli$ sup  ssh pfe20 qstat -u hschilli
                                                       Req'd    Elap
        JobID          User     Queue Jobname  TSK Nds wallt S wallt Eff
        -------------- -------- ----- -------- --- --- ----- - ----- ---
        1043458.pbspl1 hschilli devel sup_test   1   1 00:10 E 00:00 25%

        qstat -f 1043474.pbspl1.nas.nasa.gov

        which outputs a lot of lines including

            job_state = Q

        '''

        sup_command = self._sup_command
        sup_command += ' ssh ' + self.options['nas_hostname']

        qsub_command = 'qstat'
        qsub_command += ' -f {}.{}.{}'.format(self._job_id, self._pbs_server,self._nas_hostname)

        sup_command =  sup_command + ' ' + qsub_command

        self._process = \
            ShellProc(sup_command, self.stdin,
                      subprocess.PIPE, subprocess.PIPE, self.options['env_vars'])
        #self._logger.debug('PID = %d', self._process.pid)

        try:
            return_code, error_msg = \
                self._process.wait(self.options['poll_delay'], self.options['timeout'])
            # Need to look at the stdout
            job_status = None
            # look for something like this:
            # qstat: 1229530.pbspl1.nas.nasa.gov Job has finished, use -x or -H to obtain historical job information
            stdout_lines = list( self._process.stdout )
            stderr_lines = list( self._process.stderr )
            if stderr_lines and 'Job has finished' in stderr_lines[0]:
                job_status = 'Finished'
            else:
                # Look through the complete output
                for line in stdout_lines:
                    if 'job_state = ' in line:
                        job_status = line.split()[2]
                        break
        finally:
            self._process.close_files()
            self._process = None

        if job_status is None:
            raise RuntimeError( 'Unable to determine status of job' )

        return job_status

    def _transfer_files_to_nas(self, external_input_files ):
        """
            Copy the list of input files from local system to  
            the working directory on NAS
        """

        if not self.options['external_input_files']:
            return # nothing to do

        missing_files = self._check_for_files(input=True)
        if missing_files:
            missing_filepaths = [ path for iotype, path in missing_files ]
            msg = 'The following input files are missing: ' + ", ".join(missing_filepaths)
            raise RuntimeError( msg )

        # Build the remote copy command
        scp_command = self._scp_command
        scp_command += ' ' + ' '.join(self.options['external_input_files'])
        scp_command += ' '
        if self.options['nas_username']:
            scp_command += self.options['nas_username'] + '@'
        scp_command += self.options['nas_hostname'] + ':' + self.options['nas_working_directory']

        sup_command = self._sup_command
        sup_command =  sup_command + ' ' + scp_command

        self._process = \
            ShellProc(sup_command, self.stdin,
                      subprocess.PIPE, subprocess.PIPE, self.options['env_vars'])

        try:
            return_code, error_msg = \
                self._process.wait(self.options['poll_delay'], self.options['timeout'])
            if return_code:
                raise RuntimeError( error_msg )
        finally:
            # In here, looking for lines like this for each file:
            #   transfer to stderr Sending file modes: C0644 6 nas_input.txt
            #   transfer to stderr Sink: C0644 6 nas_input.txt
            std_error = self._process.stderr.read()
            filenames_with_errors = set()
            for filename in external_input_files:
                match_string = r'Sending file modes: [a-zA-Z][0-9]+ [0-9] %s' % filename
                if not re.search(match_string, std_error):
                    filenames_with_errors.add(filename)
                if not re.search(r'Sink: [a-zA-Z]\d+ \d %s' % filename, std_error):
                    filenames_with_errors.add(filename)

            self._process.close_files()
            self._process = None

            if filenames_with_errors:
                    raise RuntimeError( "Error sending files: " + ", ".join(filenames_with_errors) )


    def _transfer_files_from_nas(self, external_output_files ):
        """
            Copy list of output files from NAS working directory
            to the local current working directory
        """

        external_output_files = self.options['external_output_files']
        if not external_output_files :
            return

        # Build the remote copy command
        scp_command_root = self._scp_command
        scp_command_root += ' '
        #scp_command += '-r '
        if self.options['nas_username']:
            scp_command_root += self.options['nas_username'] + '@'
        scp_command_root += self.options['nas_hostname'] + ':' + self.options['nas_working_directory'] + '/'

        # This is the old way
        # if len(external_output_files) == 1 :
        #     scp_command += external_output_files[0]
        # else:
        #     # For multiple files, use this format for the scp command
        #     # scp your_username@remotehost.edu:/some/remote/directory/\{a,b,c\} .
        #     scp_command += '\{'
        #     scp_command += ','.join(external_output_files)
        #     scp_command += '\}'
        # scp_command += ' .'
        # end of old way


        # TODO Do scp commands one at a time. Not the most efficient but will work for now
        for filepath in external_output_files:
            scp_command = scp_command_root + filepath

            # get directory of filepath
            dirname = os.path.dirname( filepath )

            # set target of copy
            if dirname:
                scp_command += ' ' + dirname
            else:
                scp_command += ' .'

            sup_command = self._sup_command + ' ' + scp_command

            self._process = \
                ShellProc(sup_command, self.stdin,
                          subprocess.PIPE, subprocess.PIPE, self.options['env_vars'])

            try:
                return_code, error_msg = \
                    self._process.wait(self.options['poll_delay'], self.options['timeout'])
                if return_code:
                    raise RuntimeError( error_msg )
            finally:
                std_error = self._process.stderr.read()


                self._process.close_files()
                self._process = None

                # Looking for lines like this:
                # Sending file modes: C0644 6 nas_input.txt
                # Sink: C0644 6 nas_input.txt
                match_string = r'Sending file modes: [a-zA-Z][0-9]+ [0-9]+ %s' % os.path.basename( filepath )

                if not re.search(match_string, std_error):
                    raise RuntimeError( "Error receiving file: " + filepath )

                match_string = r'Sink: [a-zA-Z]\d+ \d+ %s' % os.path.basename( filepath )

                if not re.search(match_string, std_error):
                    raise RuntimeError( "Error receiving file: " + filepath )

        # See if the output files made it back
        missing_files = self._check_for_files(input=False)
        if missing_files:
            missing_filepaths = [ path for iotype, path in missing_files ]
            msg = 'The following output files are missing: ' + ", ".join(missing_filepaths)
            raise RuntimeError( msg )

    def delete_job(self):
        '''
        sup  ssh pfe20 qdel 1043458
        '''

        sup_command = self._sup_command
        sup_command += ' ssh ' + self.options['nas_hostname']

        qsub_command = 'qdel'
        qsub_command += ' {}'.format(self._job_id)

        sup_command =  sup_command + ' ' + qsub_command

        self._process = \
            ShellProc(sup_command, self.stdin,
                      subprocess.PIPE, subprocess.PIPE, self.options['env_vars'])
        #self._logger.debug('PID = %d', self._process.pid)

        try:
            return_code, error_msg = \
                self._process.wait(self.options['poll_delay'], self.options['timeout'])
        finally:
            self._process.close_files()
            self._process = None

        return


