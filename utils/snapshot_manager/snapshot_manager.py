import shutil
import os
import numpy as np
import random
import pickle
from pathlib import Path
from collections import Counter

class FieldsNotSameError(Exception):
    pass

class WrongPathError(Exception):
    pass

class DirectoryExistsError(Exception):
    pass


class Snapshot_manager:

    def __init__(self, source_directory, project_directory):
        try:
            self.source_directory = str(Path(source_directory).resolve(strict=False))
        except:
            raise WrongPathError("Provide a correct absolute path to the source directory")
        try:    
            self.project_directory = str(Path(project_directory).resolve(strict=False))
        except:
            raise WrongPathError("Provide a correct absolute path to the project directory")
        
        self.symlinked_cases_directory = os.path.join(project_directory, "symlinked_cases")
        if not os.path.isdir(self.symlinked_cases_directory):    
            self._replicate_directory_structure()

            #create symlinks_of files to the files in original directory
            self._create_symlinks()
            
        self._create_list_cases_in_symlinked_directory()

        self._create_list_snapshot_paths()
        self._create_list_fields()
        self._build_dict_time_steps_for_each_case()

        self.virtual_openFoam_directory = os.path.join(self.project_directory, "virtual_OF")
        if os.path.exists(self.virtual_openFoam_directory):
            raise DirectoryExistsError("virtual_openFoam_directory already exists !!!")


    @classmethod
    def load(cls, file_path):
        try:
            file_path = str(Path(file_path).resolve(strict=False))
            with open(file_path, 'rb') as file:
                object_instance = pickle.load(file)
            return object_instance
        except:
            raise FileNotFoundError("File doesn't exist.")
    
    def save(self, file_name):

        #check if the file name ends with .pkl extension
        if not file_name.endswith('.pkl'):
            file_name += '.pkl'

        #build absolute path if not already
        file_path = os.path.join(self.project_directory, file_name)
        # Save the instance as pickle
        with open(file_path, 'wb') as f:
            pickle.dump(self, f)
    
    def set_environment(self, case_fraction=1, time_fraction_per_case=1, list_chosen_snapshot_paths=None):

        self.case_fraction = case_fraction
        self.time_fraction_per_case = time_fraction_per_case
        
        if list_chosen_snapshot_paths is not None:
            self.list_chosen_snapshot_paths = list_chosen_snapshot_paths
            
        else:
           self.list_chosen_snapshot_paths = self._randomly_choose_snapshots(self.case_fraction, self.time_fraction_per_case)

        # set up the virtual OpenFoam directory for Offline (bases are kept here)
        self._set_virtual_OpenFoam_directory()

    def _randomly_choose_snapshots(self, case_fraction, time_fraction_per_case):

        #choose cases
        self.Nchosen_cases = np.int(np.ceil(self.Ncases * case_fraction))
        self.list_chosen_cases = random.sample(self.list_cases, self.Nchosen_cases)
        self.list_unchosen_cases = list(set(self.list_cases) - set(self.list_chosen_cases))

        # initialize dictionaries
        self.Nchosen_time_steps_for_each_chosen_case = {}
        self.chosen_time_steps_for_each_chosen_case = {}
        list_chosen_snapshot_paths = [] 

        for cs in self.list_chosen_cases:
            # determine how many snaps the case has
            Nsnap = self.Ntime_steps_each_case[cs]
            # determine the number of snaps that would be chosen
            Nchosen_snap = int(np.ceil(time_fraction_per_case * Nsnap))
            # hold the value in the dictionary
            self.Nchosen_time_steps_for_each_chosen_case[cs] = Nchosen_snap
            # randomly sample the chosen time steps
            self.chosen_time_steps_for_each_chosen_case[cs] = random.sample(
                self.time_steps_for_each_case[cs], Nchosen_snap
            )
            self.chosen_time_steps_for_each_chosen_case[cs] = sorted(
                self.chosen_time_steps_for_each_chosen_case[cs], key=float
            )
            time_steps_case = self.chosen_time_steps_for_each_chosen_case[cs]
            list_chosen_snapshot_paths.extend([cs+"/"+elem for elem in time_steps_case])
        return list_chosen_snapshot_paths

    def _replicate_directory_structure(self):
    
        for root, dirs, files in os.walk(self.source_directory):
            # Create corresponding directories in the target location
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                target_path = dir_path.replace(
                    self.source_directory, self.symlinked_cases_directory
                )
                os.makedirs(target_path, exist_ok=True)
    
    #create symlinks_of files to the files in original directory
    def _create_symlinks(self):
        
        for root, dirs, files in os.walk(self.source_directory):
            for file in files:
                # Build the full path of the file in the source directory
                source_file = os.path.join(root, file)
                # Map the source file path to the corresponding target file path
                target_file = source_file.replace(self.source_directory, self.symlinked_cases_directory)
                # Check if the symbolic link (or file) already exists in the target; if not, create it.
                if not os.path.exists(target_file):
                    os.symlink(source_file, target_file)

    def _create_list_cases_in_symlinked_directory(self):
  
        # sort them according to the numeric value (assuming case name is numeric string)
        self.list_cases = os.listdir(self.symlinked_cases_directory)
        # Number of cases
        self.Ncases = len(self.list_cases)
    
    def _create_list_snapshot_paths(self):
        self.list_snapshot_paths_in_symlinked_directory = []
        for cs in self.list_cases:
            time_steps, _ = self._create_list_time_steps_in_case(cs)
            temp_list = [cs+"/"+time for time in time_steps]
            self.list_snapshot_paths_in_symlinked_directory.extend(temp_list)

    def _create_list_fields(self):
        
        self.fields_paths = []
        flag = 0

        for path in self.list_snapshot_paths_in_symlinked_directory:
            true_path = os.path.join(self.symlinked_cases_directory, path)
            directories = os.listdir(true_path)
            self.regions = [elem for elem in directories if elem.endswith("Region")]
            self.Nregions = len(self.regions)
            fields_paths = []
            if self.Nregions == 0:
                fields = [elem for elem in directories if os.path.isfile(os.path.join(true_path, elem))]
                fields_paths.extend(fields)

            else:
                for region in self.regions:
                    fields = os.listdir(os.path.join(true_path, region))
                    fields_paths.extend([region+"/"+elem for elem in fields])
                
            if flag == 0:
                self.fields_paths.extend(fields_paths)
                self.Nfields = len(self.fields_paths)
                flag = 1
            else:
                identical = (Counter(self.fields_paths) == Counter(fields_paths))
                if not identical:
                    raise FieldsNotSameError("Fields in different cases are not identical.")
           
    def _create_list_time_steps_in_case(self, case):

        # List all items in the target directory
        case_directory = os.path.join(self.symlinked_cases_directory, case)
        list_current_directory = os.listdir(case_directory)
        # Filter directories that are named with numeric values and exist
        time_steps = [
            d
            for d in list_current_directory
            if d.isnumeric()
            and d != "0"
            and os.path.isdir(os.path.join(case_directory, d))
        ]
        # Sort time steps numerically
        time_steps = sorted(time_steps, key=float)
        Ntime_steps = len(time_steps)

        return time_steps, Ntime_steps
    
    def _build_dict_time_steps_for_each_case(self):
        
        # initialize
        self.time_steps_for_each_case = {}
        self.Ntime_steps_each_case = {}

        for cs in self.list_cases:
            # List all items in the target directory
            case_directory = os.path.join(self.symlinked_cases_directory, cs)
            list_current_directory = os.listdir(case_directory)
            # Filter directories that are named with numeric values and exist
            time_steps = [
                d
                for d in list_current_directory
                if d.isnumeric()
                and d != "0"
                and os.path.isdir(os.path.join(case_directory, d))
            ]
            # Sort time steps numerically
            time_steps = sorted(time_steps, key=float)
            self.time_steps_for_each_case[cs] = time_steps
            self.Ntime_steps_each_case[cs] = len(time_steps)
 
    def _set_virtual_OpenFoam_directory(self):
        
        # select a case, it could be random
        cs = self.list_cases[0]
        case_dir = os.path.join(self.symlinked_cases_directory, cs)

        # build source directory path to copy
        system_dir_in_case_dir = os.path.join(case_dir, "system")
        constant_dir_in_case_dir = os.path.join(case_dir, "constant")
        
        # build target directory path to copy to
        system_dir_in_virtual_OpenFoam_directory = os.path.join(
            self.virtual_openFoam_directory, "system"
        )
        if os.path.exists(system_dir_in_virtual_OpenFoam_directory):
            shutil.rmtree(system_dir_in_virtual_OpenFoam_directory)
        constant_dir_in_virtual_OpenFoam_directory = os.path.join(
            self.virtual_openFoam_directory, "constant"
        )
        if os.path.exists(constant_dir_in_virtual_OpenFoam_directory):
            shutil.rmtree(constant_dir_in_virtual_OpenFoam_directory)

        # create directories in the virtual OF directory for the application of an Algorithm
        os.makedirs(constant_dir_in_virtual_OpenFoam_directory, exist_ok=True)
        os.makedirs(system_dir_in_virtual_OpenFoam_directory, exist_ok=True)

        # copy the directory to the virtual OF directory
        shutil.copytree(
            system_dir_in_case_dir,
            system_dir_in_virtual_OpenFoam_directory,
            dirs_exist_ok=True,
            symlinks=True,
        )
        shutil.copytree(
            constant_dir_in_case_dir,
            constant_dir_in_virtual_OpenFoam_directory,
            dirs_exist_ok=True,
            symlinks=True,
        )

if __name__ == "__main__":
    import argparse
    current_dir = os.path.abspath(".")

    # Set up command line argument parsing
    parser = argparse.ArgumentParser(
        description="Manage OpenFOAM case snapshots for the Application of Data Assimilation Algorithms"
    )
    parser.add_argument(
        "--source", required=True, help="Source directory containing OpenFOAM cases"
    )
    parser.add_argument(
        "--project_directory",
        default=current_dir,
        help="Directory for the DA algorithm to be applied",
    )

    args = parser.parse_args()

    # Create and use the Snapshot_manager
    sm = Snapshot_manager(
        source_directory=args.source,
        project_directory=args.project_directory,
    )

    # Set up the environment
    sm.set_environment(case_fraction=0.5, time_fraction_per_case=0.6)
    print(f"Selected {sm.Nchosen_cases} cases out of {sm.Ncases}")
    