import shutil
import os
import numpy as np
import random

class Snapshot_manager:
    def __init__(self, source_directory, symlinked_cases_directory, geim_directory, reconstruction_directory, case_fraction_min, snap_fraction_per_case_min):
        self.source_directory = source_directory
        self.symlinked_cases_directory = symlinked_cases_directory
        if os.path.exists(self.symlinked_cases_directory):
            shutil.rmtree(self.symlinked_cases_directory)

        self.geim_directory = geim_directory
        if os.path.exists(self.geim_directory):
            shutil.rmtree(self.geim_directory)

        self.reconstruction_directory = reconstruction_directory
        if os.path.exists(self.reconstruction_directory):
            shutil.rmtree(self.reconstruction_directory)

        self.case_fraction_min = case_fraction_min
        self.snap_fraction_per_case_min = snap_fraction_per_case_min

    def replicate_directory_structure(self):
        for root, dirs, files in os.walk(self.source_directory):
            # Create corresponding directories in the target location
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                target_path = dir_path.replace(self.source_directory, self.symlinked_cases_directory)
                os.makedirs(target_path, exist_ok=True)
    
    def create_symlinks_of_files_to_the_files_in_original_directory(self):
        for root, dirs, files in os.walk(self.source_directory):
            for file in files:
                # Build the full path of the file in the source directory
                source_file = os.path.join(root, file)
                # Map the source file path to the corresponding target file path
                target_file = source_file.replace(self.source_directory, self.symlinked_cases_directory)
                # Check if the symbolic link (or file) already exists in the target; if not, create it.
                if not os.path.exists(target_file):
                    os.symlink(source_file, target_file)
    def is_numeric(self, value):
        try:
            float(value)  # Attempt to convert to a float
            return True   # Conversion successful
        except ValueError:
            return False  # Conversion fails if the value is not numeric

   
    def list_cases_symlinked_directory(self):
        #list directory
        self.list_dirs = os.listdir(self.symlinked_cases_directory)
        #list cases
        self.list_cases = [k for k in self.list_dirs if self.is_numeric(k) and os.path.isdir(os.path.join(self.symlinked_cases_directory, k))]
        #sort them according to the numeric value (assuming case name is numeric string)
        self.list_cases = sorted(self.list_cases, key=float)
        # Number of cases
        self.Ncases = len(self.list_cases)
    
    def build_dict_time_steps_for_each_case(self):

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
                if d.isnumeric() and d != "0" and os.path.isdir(os.path.join(case_directory, d))
            ]
            # Sort time steps numerically
            time_steps = sorted(time_steps, key=float)
            self.time_steps_for_each_case[cs] = time_steps
            self.Ntime_steps_each_case[cs] = len(time_steps)
    
    def randomly_choose_cases(self):

        #determine the number of chosen cases
        self.Nchosen_cases = int(np.ceil(self.case_fraction_min * self.Ncases))
        # randomly sample the cases
        self.chosen_cases = random.sample(self.list_cases, self.Nchosen_cases)
        # create list of the unchosen cases
        chosen_set = set(self.chosen_cases)
        self.unchosen_cases = [case for case in self.list_cases if case not in chosen_set]
    
    def randomly_choose_time_steps(self):
        #initialize dictionaries
        self.Nchosen_time_steps_for_each_chosen_case = {}
        self.chosen_time_steps_for_each_chosen_case = {}
        self.unchosen_time_steps_for_each_chosen_case = {}

        for cs in self.chosen_cases:
            #determine how many snaps the case has
            Nsnap = self.Ntime_steps_each_case[cs] 
            #determine the number of snaps that would be chosen
            Nchosen_snap = int(np.ceil(self.snap_fraction_per_case_min * Nsnap))
            #hold the value in the dictionary
            self.Nchosen_time_steps_for_each_chosen_case[cs] = Nchosen_snap
            #randomly sample the chosen time steps
            self.chosen_time_steps_for_each_chosen_case[cs] = random.sample(self.time_steps_for_each_case[cs], Nchosen_snap)
            chosen_set = set(self.chosen_time_steps_for_each_chosen_case[cs])
            self.unchosen_time_steps_for_each_chosen_case[cs] = [time_step for time_step in self.time_steps_for_each_case[cs] if time_step not in chosen_set]

    
        
    def copy_necessary_files_dirs_in_geim_dir(self):
        
        #select a case, it could be random
        cs = self.chosen_cases[0]
        case_dir = os.path.join(self.symlinked_cases_directory, cs)
        
        #build source directory path to copy
        system_dir_in_case_dir = os.path.join(case_dir, "system")
        constant_dir_in_case_dir = os.path.join(case_dir, "constant")
        zero_dir_in_case_dir = os.path.join(case_dir, "0")

        #build target directory path to copy to
        system_dir_in_geim_dir = os.path.join(self.geim_directory, "system")
        if os.path.exists(system_dir_in_geim_dir):
                shutil.rmtree(system_dir_in_geim_dir)
        constant_dir_in_geim_dir = os.path.join(self.geim_directory, "constant")
        if os.path.exists(constant_dir_in_geim_dir):
                shutil.rmtree(constant_dir_in_geim_dir)
        zero_dir_in_geim_dir = os.path.join(self.geim_directory, "0")
        if os.path.exists(zero_dir_in_geim_dir):
                shutil.rmtree(zero_dir_in_geim_dir)

        #create directories in the virtual OF directory for GEIM
        os.makedirs(zero_dir_in_geim_dir, exist_ok=True)
        os.makedirs(constant_dir_in_geim_dir,exist_ok=True)
        os.makedirs(system_dir_in_geim_dir, exist_ok=True)
            

        #copy the directory to the virtual OF directory for GEIM
        shutil.copytree(system_dir_in_case_dir, system_dir_in_geim_dir, dirs_exist_ok=True, symlinks=True)
        shutil.copytree(constant_dir_in_case_dir, constant_dir_in_geim_dir, dirs_exist_ok=True, symlinks=True)
        shutil.copytree(zero_dir_in_case_dir, zero_dir_in_geim_dir, dirs_exist_ok=True, symlinks=True)

    
    def make_dir_in_geim_directory(self, case, time_step):
        #create time directory name
        index_case = self.list_cases.index(case)
        str_index_case = str(index_case)
        structured_str_index_case = str_index_case.zfill(6)
        dir_name = time_step + structured_str_index_case 
        #construct the path
        dir_path = os.path.join(self.geim_directory, dir_name)
        #make the directory
        os.makedirs(dir_path, exist_ok=True)

        return dir_path, dir_name
        

    def copy_chosen_time_steps_to_virtual_OF_directory_for_geim(self):

        #loop over the dictionary
        self.time_directory_name_in_geim_directory = []
        for key, value in self.chosen_time_steps_for_each_chosen_case.items():
            for t_step in value:
                #construct the source directory path to copy from
                source_dir_path = os.path.join(self.symlinked_cases_directory, key, t_step)
                #construct the taget directory path to copy to
                target_dir_path, target_dir_name = self.make_dir_in_geim_directory(key,t_step)
                self.time_directory_name_in_geim_directory.append(target_dir_name)
                # copy the directory with symlinks
                shutil.copytree(source_dir_path, target_dir_path, dirs_exist_ok=True, symlinks=True)
    
    def set_environment_random(self):
    	#it is random because the cases and snaps are selected randomly
        self.replicate_directory_structure()
        self.create_symlinks_of_files_to_the_files_in_original_directory()
        self.list_cases_symlinked_directory()

        self.build_dict_time_steps_for_each_case()
        self.randomly_choose_cases()
        self.randomly_choose_time_steps()
        self.copy_necessary_files_dirs_in_geim_dir()
        self.copy_chosen_time_steps_to_virtual_OF_directory_for_geim()


    def set_reconstruction_directory(self):
        #select a case, it could be random
        cs = self.chosen_cases[0]
        case_dir = os.path.join(self.symlinked_cases_directory, cs)
        
        #build source directory path to copy
        system_dir_in_case_dir = os.path.join(case_dir, "system")
        constant_dir_in_case_dir = os.path.join(case_dir, "constant")
        zero_dir_in_case_dir = os.path.join(case_dir, "0")

        #build target directory path to copy to
        system_dir_in_reconstruction_dir = os.path.join(self.reconstruction_directory, "system")
        constant_dir_in_reconstruction_dir = os.path.join(self.reconstruction_directory, "constant")
        zero_dir_in_reconstruction_dir = os.path.join(self.reconstruction_directory, "0")

        #create directories in the virtual OF directory for GEIM
        os.makedirs(zero_dir_in_reconstruction_dir, exist_ok=True)
        os.makedirs(constant_dir_in_reconstruction_dir,exist_ok=True)
        os.makedirs(system_dir_in_reconstruction_dir, exist_ok=True)

        #copy the directory to the virtual OF directory for GEIM
        shutil.copytree(system_dir_in_case_dir, system_dir_in_reconstruction_dir, dirs_exist_ok=True, symlinks=True)
        shutil.copytree(constant_dir_in_case_dir, constant_dir_in_reconstruction_dir, dirs_exist_ok=True, symlinks=True)
        shutil.copytree(zero_dir_in_case_dir, zero_dir_in_reconstruction_dir, dirs_exist_ok=True, symlinks=True)
                

    def make_dir_in_reconstruction_directory(self, case, time_step):
        #create time directory name
        index_case = self.list_cases.index(case)
        str_index_case = str(index_case)
        structured_str_index_case = str_index_case.zfill(6)
        self.reconstruction_time_dir_name = time_step + structured_str_index_case 
        #construct the path
        self.reconstruction_time_dir_path = os.path.join(self.reconstruction_directory, self.reconstruction_time_dir_name)
        #make the directory
        os.makedirs(self.reconstruction_time_dir_path, exist_ok=True)

    
    def copy_a_snap_to_the_reconstruction_directory(self, OF_case, time_step):
        self.real_cs_dir = os.path.join(self.symlinked_cases_directory, OF_case)
        self.real_time_dir = os.path.join(self.real_cs_dir, time_step)
        shutil.copytree(self.real_time_dir, self.reconstruction_time_dir_path, dirs_exist_ok=True, symlinks=True)


    
    

