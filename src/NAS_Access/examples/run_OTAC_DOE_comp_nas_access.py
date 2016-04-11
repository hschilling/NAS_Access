import os
import csv
import numpy as np

from openmdao.api import Problem, Group
from openmdao.components.nas_access import NasAccess

class OTAC_doe_NAS(NasAccess):
    def __init__(self):
        super(OTAC_doe_NAS, self).__init__()

        self.add_param('num_samples', val=1)

        self.add_output("Vane4_bx_avg", val=0.0)

        self.input_filepath = "doe_input.dat"
        self.output_filepath = "Output/doe.csv"

    def solve_nonlinear(self, params, unknowns, resids):
        self.generate_input(params) 
        super(OTAC_doe_NAS, self).solve_nonlinear(params, unknowns, resids)
        self.parse_output(params, unknowns)

    def generate_input(self, params):
        '''Take the params and writes them to a file 
        which gets transferred to NAS. There, the script on NAS
        can read it and get the input parameters
        '''
        with open(self.input_filepath, 'w') as f:
            f.write( '{}\n'.format( params['num_samples']))

    def parse_output(self, params, unknowns):
        """Parses the DOE output file and populates the component
        outputs with the data.
        """

        sum = 0.0
        with open(self.output_filepath, 'rb') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                sum += float(row['Vane4_bx'])

        unknowns['Vane4_bx_avg'] = sum / float(i+1)


top = Problem()
top.root = Group()

nas_access = OTAC_doe_NAS()
top.root.add('nas_access', nas_access)

nas_access.options['external_input_files'] = ['doe_input.dat']
nas_access.options['external_output_files'] = ['Output/doe','Output/doe.csv']
nas_access.options['nas_working_directory'] = '/u/hschilli/openmdao/nas_access_testing/NPSS/model/VSPT_Turbine_MDP_TD/try_doe'
nas_access.options['nas_username'] = 'hschilli'
nas_access.options['nas_hostname'] = 'pfe20'
nas_access.options['remote_copy_command'] = 'scp' # could also be bbscp
nas_access.options['sup_verbose'] = False
nas_access.options['qsub_filepath'] = '/u/hschilli/openmdao/nas_access_testing/NPSS/model/VSPT_Turbine_MDP_TD/OTAC_doe_LatinHypercubeDriver_small.qsub'
#nas_access.options['qsub_options'] = '-N OTAC_doe_NAS -l select=1:ncpus=4:mpiprocs=4: -l walltime=0:10:00 -j oe -W group_list=a1607 -m e -q devel' # to override what is in the qsub file
#nas_access.options['qsub_options'] = '-N OTAC_doe_NAS -l select=1:ncpus=4:mpiprocs=4,walltime=0:10:00 -j oe -W group_list=a1607 -m e -q devel' # to override what is in the qsub file
nas_access.options['qsub_options'] = '' # to override what is in the qsub file


dev_null = open(os.devnull, 'w')
top.setup(check=True, out_stream=dev_null)

top.root.nas_access.params['num_samples'] = 10

top.run()

print top.root.nas_access.unknowns['Vane4_bx_avg']


