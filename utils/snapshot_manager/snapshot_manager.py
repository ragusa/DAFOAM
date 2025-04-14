import shutil
import os
import numpy as np
import random
import csv


# an instance of Snapshot_manager object takes the path to the directory where the OpenFoam cases are named numerically
class Snapshot_manager:
    def __init__(
        self,
        source_directory,
        symlinked_cases_directory,
        geim_offline_directory,
        geim_online_directory,
        case_fraction_min,
        snap_fraction_per_case_min,
    ):
        # it is assumed that in the source directory which holds the cases, the cases are named numerically with unique name each
        self.source_directory = source_directory
        self.symlinked_cases_directory = symlinked_cases_directory
        if os.path.exists(self.symlinked_cases_directory):
            shutil.rmtree(self.symlinked_cases_directory)

        self.geim_offline_directory = geim_offline_directory
        if os.path.exists(self.geim_offline_directory):
            shutil.rmtree(self.geim_offline_directory)

        self.geim_online_directory = geim_online_directory
        if os.path.exists(self.geim_online_directory):
            shutil.rmtree(self.geim_online_directory)

        self.case_fraction_min = case_fraction_min
        self.snap_fraction_per_case_min = snap_fraction_per_case_min

    def replicate_directory_structure(self):
        for root, dirs, files in os.walk(self.source_directory):
            # Create corresponding directories in the target location
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                target_path = dir_path.replace(
                    self.source_directory, self.symlinked_cases_directory
                )
                os.makedirs(target_path, exist_ok=True)

    def create_symlinks_of_files_to_the_files_in_original_directory(self):
        for root, dirs, files in os.walk(self.source_directory):
            for file in files:
                # Build the full path of the file in the source directory
                source_file = os.path.join(root, file)
                # Map the source file path to the corresponding target file path
                target_file = source_file.replace(
                    self.source_directory, self.symlinked_cases_directory
                )
                # Check if the symbolic link (or file) already exists in the target; if not, create it.
                if not os.path.exists(target_file):
                    os.symlink(source_file, target_file)

    def is_numeric(self, value):
        try:
            # Attempt to convert to a float
            float(value)
            # Conversion successful
            return True
        except ValueError:
            # Conversion fails if the value is not numeric
            return False

    def list_cases_in_symlinked_directory(self):
        # list directory
        self.list_dirs = os.listdir(self.symlinked_cases_directory)
        # list cases
        self.list_cases = [
            k
            for k in self.list_dirs
            if self.is_numeric(k)
            and os.path.isdir(os.path.join(self.symlinked_cases_directory, k))
        ]
        # sort them according to the numeric value (assuming case name is numeric string)
        self.list_cases = sorted(self.list_cases, key=float)
        # Number of cases
        self.Ncases = len(self.list_cases)
        file_name = "case_list.csv"
        data = self.list_cases
        col_head_list = ['case']
        self.write_in_a_CSV(file_name, data, col_head_list)

    def build_dict_time_steps_for_each_case(self):

        self.time_steps_for_each_case = {}
        self.Ntime_steps_each_case = {}
        data = []

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

            time_steps_str = ",".join(self.time_steps_for_each_case[cs])
            data.append([cs, time_steps_str, self.Ntime_steps_each_case[cs]])

        file_name = "time_steps_each_case.csv"
        col_head_list = ['case', 'time_steps', 'Ntime_steps']
        self.write_in_a_CSV(file_name, data, col_head_list)

    def write_in_a_CSV(self, file_name, data, col_head_list):
        with open (file_name, 'w', newline='') as csvfile:
            # create an instance of a writer object
            csv_writer = csv.writer(csvfile)
            #write header
            csv_writer.writerow(col_head_list)
            for unit in data:
                csv_writer.writerow(unit)


    def randomly_choose_cases(self):

        # determine the number of chosen cases
        self.Nchosen_cases = int(np.ceil(self.case_fraction_min * self.Ncases))
        # randomly sample the cases
        self.chosen_cases = random.sample(self.list_cases, self.Nchosen_cases)
        # create list of the unchosen cases
        chosen_set = set(self.chosen_cases)
        self.unchosen_cases = [
            case for case in self.list_cases if case not in chosen_set
        ]
        
        # save chosen cases in a csv file
        file_name_chosen_case = "chosen_cases.csv"
        data_chosen_case = self.chosen_cases 
        col_head_list_chosen_case = ['Chosen_Case']
        self.write_in_a_CSV(file_name_chosen_case, data_chosen_case, col_head_list_chosen_case)
        
        # save unchosen cases in a csv file
        file_name_unchosen_case = "unchosen_cases.csv"
        data_unchosen_case = self.unchosen_cases 
        col_head_list_unchosen_case = ['Unchosen_Case']
        self.write_in_a_CSV(file_name_unchosen_case, data_unchosen_case, col_head_list_unchosen_case)


    def randomly_choose_time_steps(self):
        # initialize dictionaries
        self.Nchosen_time_steps_for_each_chosen_case = {}
        self.chosen_time_steps_for_each_chosen_case = {}
        self.unchosen_time_steps_for_each_chosen_case = {}

        data_chosen_time_steps = []
        data_unchosen_time_steps = []

        for cs in self.chosen_cases:
            # determine how many snaps the case has
            Nsnap = self.Ntime_steps_each_case[cs]
            # determine the number of snaps that would be chosen
            Nchosen_snap = int(np.ceil(self.snap_fraction_per_case_min * Nsnap))
            # hold the value in the dictionary
            self.Nchosen_time_steps_for_each_chosen_case[cs] = Nchosen_snap
            # randomly sample the chosen time steps
            self.chosen_time_steps_for_each_chosen_case[cs] = random.sample(
                self.time_steps_for_each_case[cs], Nchosen_snap
            )
            self.chosen_time_steps_for_each_chosen_case[cs] = sorted(self.chosen_time_steps_for_each_chosen_case[cs], key=float)
            chosen_time_steps_str = ",".join(self.chosen_time_steps_for_each_chosen_case[cs])
            data_chosen_time_steps.append([cs, chosen_time_steps_str, self.Nchosen_time_steps_for_each_chosen_case[cs]])

            #unchosen
            chosen_set = set(self.chosen_time_steps_for_each_chosen_case[cs])
            self.unchosen_time_steps_for_each_chosen_case[cs] = [
                time_step
                for time_step in self.time_steps_for_each_case[cs]
                if time_step not in chosen_set
            ]
            self.unchosen_time_steps_for_each_chosen_case[cs] = sorted(self.unchosen_time_steps_for_each_chosen_case[cs], key=float)
            unchosen_time_steps_str = ",".join(self.unchosen_time_steps_for_each_chosen_case[cs])
            data_unchosen_time_steps.append([cs, unchosen_time_steps_str, self.Ntime_steps_each_case[cs] - self.Nchosen_time_steps_for_each_chosen_case[cs]])
        
        file_name_chosen = "chosen_time_steps_each_case.csv"
        file_name_unchosen = "unchosen_time_steps_each_case.csv"
        col_head_list = ['case', 'time_steps', 'Ntime_steps']
        self.write_in_a_CSV(file_name_chosen, data_chosen_time_steps, col_head_list)
        self.write_in_a_CSV(file_name_unchosen, data_unchosen_time_steps, col_head_list)



    def set_virtual_OpenFoam_directory(self, directory_path):

        # select a case, it could be random
        cs = self.chosen_cases[0]
        case_dir = os.path.join(self.symlinked_cases_directory, cs)

        # build source directory path to copy
        system_dir_in_case_dir = os.path.join(case_dir, "system")
        constant_dir_in_case_dir = os.path.join(case_dir, "constant")
        zero_dir_in_case_dir = os.path.join(case_dir, "0")

        # build target directory path to copy to
        system_dir_in_virtual_OpenFoam_directory = os.path.join(directory_path, "system")
        if os.path.exists(system_dir_in_virtual_OpenFoam_directory):
            shutil.rmtree(system_dir_in_virtual_OpenFoam_directory)
        constant_dir_in_virtual_OpenFoam_directory = os.path.join(directory_path, "constant")
        if os.path.exists(constant_dir_in_virtual_OpenFoam_directory):
            shutil.rmtree(constant_dir_in_virtual_OpenFoam_directory)
        zero_dir_in_virtual_OpenFoam_directory = os.path.join(directory_path, "0")
        if os.path.exists(zero_dir_in_virtual_OpenFoam_directory):
            shutil.rmtree(zero_dir_in_virtual_OpenFoam_directory)

        # create directories in the virtual OF directory for GEIM
        os.makedirs(zero_dir_in_virtual_OpenFoam_directory, exist_ok=True)
        os.makedirs(constant_dir_in_virtual_OpenFoam_directory, exist_ok=True)
        os.makedirs(system_dir_in_virtual_OpenFoam_directory, exist_ok=True)

        # copy the directory to the virtual OF directory for GEIM
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
        shutil.copytree(
            zero_dir_in_case_dir,
            zero_dir_in_virtual_OpenFoam_directory,
            dirs_exist_ok=True,
            symlinks=True,
        )

    def make_dir_in_geim_offline_directory(self, case, time_step):
        # create time directory name
        index_case = self.list_cases.index(case)
        str_index_case = str(index_case)
        structured_str_index_case = str_index_case.zfill(6)
        dir_name = time_step + structured_str_index_case
        # construct the path
        dir_path = os.path.join(self.geim_offline_directory, dir_name)
        # make the directory
        os.makedirs(dir_path, exist_ok=True)

        return dir_path, dir_name

    def copy_chosen_time_steps_to_virtual_OF_directory_for_geim(self):
        # loop over the dictionary
        self.time_directory_name_in_geim_offline_directory = []
        for key, value in self.chosen_time_steps_for_each_chosen_case.items():
            for t_step in value:
                # construct the source directory path to copy from
                source_dir_path = os.path.join(
                    self.symlinked_cases_directory, key, t_step
                )
                # construct the taget directory path to copy to
                target_dir_path, target_dir_name = self.make_dir_in_geim_offline_directory(
                    key, t_step
                )
                self.time_directory_name_in_geim_offline_directory.append(target_dir_name)
                # copy the directory with symlinks
                shutil.copytree(
                    source_dir_path, target_dir_path, dirs_exist_ok=True, symlinks=True
                )

    def set_environment_random(self):
        # it is random because the cases and snaps are selected randomly
        self.replicate_directory_structure()
        self.create_symlinks_of_files_to_the_files_in_original_directory()
        self.list_cases_in_symlinked_directory()

        self.build_dict_time_steps_for_each_case()
        self.randomly_choose_cases()
        self.randomly_choose_time_steps()

        #set a virtual OpenFoam directory for GEIM Offline
        self.set_virtual_OpenFoam_directory(self.geim_offline_directory)
        self.copy_chosen_time_steps_to_virtual_OF_directory_for_geim()

        #set a virtual OpenFoam directory for GEIM Online
        self.set_virtual_OpenFoam_directory(self.geim_online_directory)

    # for user
    def make_dir_in_geim_online_directory(self, case, time_step):
        # create time directory name
        index_case = self.list_cases.index(case)
        str_index_case = str(index_case)
        structured_str_index_case = str_index_case.zfill(6)
        self.geim_online_time_dir_name = time_step + structured_str_index_case
        # construct the path
        self.geim_online_time_dir_path = os.path.join(
            self.geim_online_directory, self.geim_online_time_dir_name
        )
        # make the directory
        os.makedirs(self.geim_online_time_dir_path, exist_ok=True)

    # for user
    def copy_a_snap_to_the_geim_online_directory(self, OF_case, time_step):
        self.real_cs_dir = os.path.join(self.symlinked_cases_directory, OF_case)
        self.real_time_dir = os.path.join(self.real_cs_dir, time_step)
        shutil.copytree(
            self.real_time_dir,
            self.geim_online_time_dir_path,
            dirs_exist_ok=True,
            symlinks=True,
        )


if __name__ == "__main__":
    import argparse
    
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description='Manage OpenFOAM case snapshots for GEIM')
    parser.add_argument('--source', required=True, help='Source directory containing OpenFOAM cases')
    parser.add_argument('--symlinked', default='symlinked_cases', help='Directory for symlinked cases')
    parser.add_argument('--geim', default='geim_offline_directory', help='Directory for GEIM offline')
    parser.add_argument('--recon', default='geim_online_directory', help='Directory for GEIM online')
    parser.add_argument('--case-fraction', type=float, default=0.7, help='Minimum fraction of cases to use')
    parser.add_argument('--snap-fraction', type=float, default=0.8, help='Minimum fraction of snapshots per case to use')
    
    args = parser.parse_args()
    
    # Create and use the Snapshot_manager
    sm = Snapshot_manager(
        source_directory=args.source,
        symlinked_cases_directory=args.symlinked,
        geim_offline_directory=args.geim,
        geim_online_directory=args.recon,
        case_fraction_min=args.case_fraction,
        snap_fraction_per_case_min=args.snap_fraction
    )
    
    # Set up the environment
    print("Setting up environment...")
    sm.set_environment_random()
    print(f"Selected {len(sm.chosen_cases)} cases out of {sm.Ncases}")
    
