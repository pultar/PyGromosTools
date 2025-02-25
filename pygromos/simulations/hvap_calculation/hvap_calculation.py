"""
File:            automatic calculation of Hvap
Warnings: this class is WIP!

Description:
    For a given gromos_system (or smiles) the heat of vaporization is automaticaly calculated.

    Main elements:
        1) create single molecule topo and conformation
        2) run gas (single molecule) minimization
        3) run gas SD simulation (and equilibaration)
        4) generate multi molecule (liquid) topo and conformation
        5) run liquid minimization
        6) run liquid MD run (and equilibaration)
        7) calculate Hvap from gas and liquid trajectories

Author: Marc Lehner
"""

from copy import deepcopy
from rdkit import Chem
import os
import warnings
import time

from pygromos.gromos.pyGromosPP.ran_box import ran_box
from pygromos.gromos.pyGromosPP.com_top import com_top
from pygromos.files.gromos_system.gromos_system import Gromos_System
from pygromos.simulations.hvap_calculation import hvap_input_files
from pygromos.files.gromos_system.ff.forcefield_system import forcefield_system

from pygromos.simulations.hpc_queuing.submission_systems.local import LOCAL as subSys
from pygromos.simulations.modules.general_simulation_modules import simulation
from pygromos.simulations.hpc_queuing.job_scheduling.workers.analysis_workers import simulation_analysis

from pygromos.files.coord.cnf import Cnf
from pygromos.files.simulation_parameters.imd import Imd
from pygromos.files.topology.top import Top

class Hvap_calculation():
    def __init__(self, input_system:Gromos_System or str or Chem.rdchem.Mol, work_folder:str, system_name:str="dummy", forcefield:forcefield_system=forcefield_system(name="54A7"), gromosXX:str=None, gromosPP:str=None, useGromosPlsPls:bool=True, verbose:bool=True) -> None:
        """For a given gromos_system (or smiles) the heat of vaporization is automaticaly calculated

        Parameters
        ----------
        input_system : Gromos_SystemorstrorChem.rdchem.Mol
            single molecule gromos_sytem or rdkit Molecule or SMILES
        """
        # system variables
        if type(input_system) is Gromos_System:
            self.groSys_gas = input_system
        elif (type(input_system) is str) or (type(input_system) is Chem.rdchem.Mol):
            self.groSys_gas = Gromos_System(work_folder=work_folder, system_name=system_name, in_smiles=input_system, Forcefield=forcefield, in_imd_path=hvap_input_files.imd_hvap_gas_sd, verbose=verbose)
            

        self.work_folder = work_folder
        self.system_name = system_name

        # create folders and structure
        try:
            os.mkdir(path=work_folder)
        except:
            if verbose:
                warnings.warn("Folder does already exist")
            else:
                pass
        self.groSys_gas.work_folder = work_folder + "/" + system_name +"_gas"
        self.groSys_gas.rebase_files()
        self.groSys_liq = deepcopy(self.groSys_gas)
        self.groSys_liq.work_folder = work_folder + "/" + system_name +"_liq"
        self.groSys_liq.rebase_files()

        self.submissonSystem = subSys()

        self.gromosXX = self.groSys_gas.gromosXX
        self.gromosPP = self.groSys_gas.gromosPP

        # define template imd files (overwritte for specific systems) 
        # made for small molecule Hvap calculation
        self.imd_gas_min = Imd(hvap_input_files.imd_hvap_emin)
        self.imd_gas_eq = Imd(hvap_input_files.imd_hvap_gas_sd)
        self.imd_gas_sd = Imd(hvap_input_files.imd_hvap_gas_sd)
        self.imd_liq_min = Imd(hvap_input_files.imd_hvap_emin)
        self.imd_liq_eq = Imd(hvap_input_files.imd_hvap_liquid_eq)
        self.imd_liq_md = Imd(hvap_input_files.imd_hvap_liquid_md)

        # parameters for liquid simulation
        # used to multiply the single molecule system
        # made for small molecule Hvap calculation
        self.num_molecules = 512
        self.density = 1000
        self.temperature = 298.15

        self.groSys_gas_final = None
        self.groSys_liq_final = None

        self.useGromosPlsPls = useGromosPlsPls

        self.verbose = verbose

    def run(self) -> int:
        self.create_liq()
        self.run_gas()
        self.run_liq()
        return self.calc_hvap()

    def create_liq(self):
        # create liq top
        if self.useGromosPlsPls:
            try:
                self.gromosPP.com_top(self.groSys_gas.top.path, topo_multiplier=self.num_molecules, out_top_path=self.work_folder + "/temp.top")
                tempTop = Top(in_value=self.work_folder+"/temp.top")
                tempTop.write(out_path=self.work_folder+"temp.top")
                time.sleep(1) #wait for file to write and close
                self.groSys_liq.top = tempTop
            except:
                self.groSys_liq.top = com_top(top1=self.groSys_gas.top, top2=self.groSys_gas.top, topo_multiplier=[self.num_molecules,0], verbose=False)
        else:
            self.groSys_liq.top = com_top(top1=self.groSys_gas.top, top2=self.groSys_gas.top, topo_multiplier=[self.num_molecules,0], verbose=False)
        

        #create liq cnf
        if self.useGromosPlsPls:
            self.gromosPP.ran_box(in_top_path=self.groSys_gas.top.path, in_cnf_path=self.groSys_gas.cnf.path, out_cnf_path=self.work_folder+"/temp.cnf", nmolecule=self.num_molecules, dens=self.density, threshold=0.1, layer=True)
        else:
            ran_box(in_top_path=self.groSys_gas.top.path, in_cnf_path=self.groSys_gas.cnf.path, out_cnf_path=self.work_folder+"/temp.cnf", nmolecule=self.num_molecules, dens=self.density)
        time.sleep(3) #wait for file to write and close 
        self.groSys_liq.cnf = Cnf(in_value=self.work_folder+"/temp.cnf")

        #reset liq system
        self.groSys_liq.rebase_files()

    def run_gas(self):
        self.groSys_gas.rebase_files()

        #min
        print(self.groSys_gas.work_folder)
        sys_emin_gas, jobID = simulation(in_gromos_system=self.groSys_gas,
                                         project_dir=self.groSys_gas.work_folder,
                                         step_name="1_emin",
                                         in_imd_path=self.imd_gas_min,
                                         submission_system=self.submissonSystem,
                                         analysis_script=simulation_analysis.do,
                                         verbose=self.verbose)
        print(self.groSys_gas.work_folder)

        #eq
        sys_eq_gas, jobID = simulation(in_gromos_system=sys_emin_gas,
                                       project_dir=self.groSys_gas.work_folder,
                                       step_name="2_eq",
                                       in_imd_path=self.imd_gas_eq,
                                       submission_system=self.submissonSystem,
                                       analysis_script=simulation_analysis.do,
                                       verbose=self.verbose)

        #sd
        sys_sd_gas, jobID = simulation(in_gromos_system=sys_eq_gas,
                                       project_dir=self.groSys_gas.work_folder,
                                       step_name="3_sd",
                                       in_imd_path=self.imd_gas_sd,
                                       submission_system=self.submissonSystem,
                                       analysis_script=simulation_analysis.do,
                                       verbose=self.verbose)

        self.groSys_gas_final = sys_sd_gas


    def run_liq(self):
        self.groSys_liq.rebase_files()

        #minsys_emin_liq, jobID
        sys_emin_liq, jobID = simulation(in_gromos_system=self.groSys_liq,
                                         project_dir=self.groSys_liq.work_folder,
                                         step_name="1_emin",
                                         in_imd_path=self.imd_liq_min,
                                         submission_system=self.submissonSystem,
                                         analysis_script=simulation_analysis.do,
                                         verbose=self.verbose)

        #eq
        sys_eq_liq, jobID = simulation(in_gromos_system=sys_emin_liq,
                                       project_dir=self.groSys_liq.work_folder,
                                       step_name="2_eq",
                                       in_imd_path=self.imd_liq_eq,
                                       submission_system=self.submissonSystem,
                                       analysis_script=simulation_analysis.do,
                                       verbose=self.verbose)

        #md
        sys_md_liq, jobID = simulation(in_gromos_system=sys_eq_liq,
                                       project_dir=self.groSys_liq.work_folder,
                                       step_name="3_sd",
                                       in_imd_path=self.imd_liq_md,
                                       submission_system=self.submissonSystem,
                                       analysis_script=simulation_analysis.do,
                                       verbose=self.verbose)

        self.groSys_liq_final = sys_md_liq

    def calc_hvap(self) -> float:
        h_vap = self.groSys_liq_final.tre.get_Hvap(gas_traj=self.groSys_gas_final.tre, nMolecules=self.num_molecules, temperature=self.temperature)
        return h_vap
