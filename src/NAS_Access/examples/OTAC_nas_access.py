import os

from openmdao.api import Problem, Group
from openmdao.components.nas_access import NasAccess

class NasAccessForTesting(NasAccess):
    def __init__(self):
        super(NasAccessForTesting, self).__init__()

top = Problem()
top.root = Group()

nas_access = NasAccess()
top.root.add('nas_access', nas_access)

# nas_access.options['external_input_files'] = ['nas_input.txt','nas_input2.txt',]
# nas_access.options['external_output_files'] = ['nas_input.txt','nas_input2.txt',]
# nas_access.options['external_input_files'] = ['nas_input.txt','nas_input2.txt',]
# nas_access.options['external_output_files'] = ['nas_input.txt','nas_input2.txt',]
# nas_access.options['nas_working_directory'] = '/u/hschilli/openmdao/testing_sup'
# nas_access.options['nas_username'] = 'hschilli'
# nas_access.options['nas_hostname'] = 'pfe20'
# nas_access.options['remote_copy_command'] = 'scp' # could also be bbscp
# nas_access.options['sup_verbose'] = False
# #nas_access.options['qsub_filepath'] = '/u/hschilli/openmdao/testing_sup/sup_test.qsub'
# nas_access.options['qsub_filepath'] = '/u/hschilli/openmdao/sup_testqqq.qsub'
# #nas_access.options['qsub_options'] = '-q devel -lselect=2:ncpus=8,walltime=1:00:00' # to override what is in the qsub file
# nas_access.options['qsub_options'] = '-N sup_test -l select=1:ncpus=1:mpiprocs=1 -l walltime=0:10:00 -j oe -W group_list=a1607 -m e -q devel' # to override what is in the qsub file

nas_access.options['external_input_files'] = []
nas_access.options['external_output_files'] = ['Output/doe','Output/doe.csv']
nas_access.options['nas_working_directory'] = '/u/hschilli/openmdao/nas_access_testing/NPSS/model/VSPT_Turbine_MDP_TD/try_doe'
nas_access.options['nas_username'] = 'hschilli'
nas_access.options['nas_hostname'] = 'pfe20'
nas_access.options['remote_copy_command'] = 'scp' # could also be bbscp
nas_access.options['sup_verbose'] = False
nas_access.options['qsub_filepath'] = '/u/hschilli/openmdao/nas_access_testing/NPSS/model/VSPT_Turbine_MDP_TD/OTAC_doe_LatinHypercubeDriver_small.qsub'
#nas_access.options['qsub_options'] = '-q devel -lselect=2:ncpus=8,walltime=1:00:00' # to override what is in the qsub file
#nas_access.options['qsub_options'] = '-N OTAC_doe_NAS -l select=1:ncpus=4:mpiprocs=4 -l walltime=0:10:00 -j oe -W group_list=a1607 -m e -q devel' # to override what is in the qsub file
nas_access.options['qsub_options'] = '-N OTAC_doe_NAS -l select=1:ncpus=4:mpiprocs=4: -l walltime=0:10:00 -j oe -W group_list=a1607 -m e -q devel' # to override what is in the qsub file

dev_null = open(os.devnull, 'w')
top.setup(check=True, out_stream=dev_null)
top.run()

