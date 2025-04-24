import shutil
import os
import numpy as np
import random
import csv
from pathlib import Path


class Snapshot_manager:

    def __init__(
        self,
        source_directory,
        project_directory,
        case_fraction_min,
        snap_fraction_per_case_min,
        file_name_chosen_time_steps=None,
    ):

        # it is assumed that in the source directory which holds the cases, the cases are named numerically with unique name each
        if Path(source_directory).is_absolute() and Path(source_directory).exists():
            self.source_directory = source_directory
        else:
            raise ValueError("Provide a correct absolute path to the source directory")
        if Path(project_directory).is_absolute() and Path(project_directory).exists():   
            self.project_directory = project_directory
        else:
            raise ValueError("Provide a correct absolute path to the project directory")
        
        self.symlinked_cases_directory = os.path.join(
            project_directory, "symlinked_cases"
        )
        if os.path.exists(self.symlinked_cases_directory):
            shutil.rmtree(self.symlinked_cases_directory)

        self.bases_directory = os.path.join(
            self.project_directory, "bases"
        )
        if os.path.exists(self.bases_directory):
            shutil.rmtree(self.bases_directory)

        self.case_fraction_min = case_fraction_min
        self.snap_fraction_per_case_min = snap_fraction_per_case_min
        
        #it is assumed that the file is in the project directory 
        self.file_name_chosen_time_steps = file_name_chosen_time_steps
    
    #this is the main method that drives almost everything
    def set_environment(self):

        self._replicate_directory_structure()
        self._create_symlinks_of_files_to_the_files_in_original_directory()
        self._list_cases_in_symlinked_directory()

        self._build_dict_time_steps_for_each_case()

        if self.file_name_chosen_time_steps is not None:
            self.file_path_chosen_time_steps = os.path.join(
                self.project_directory, self.file_name_chosen_time_steps
            )
            if os.path.exists(self.file_path_chosen_time_steps):
                if os.path.isfile(self.file_path_chosen_time_steps):
                    self._parse_time_steps_from_file_chosen_time_steps()
                    self._determine_unchosen_cases()
                    self._determine_unchosen_time_steps()
                else:
                    raise FileNotFoundError("There is no file of the given file name.")
            else:
                raise FileNotFoundError("File does not exist.")
        else:
            self._randomly_choose_cases()
            self._determine_unchosen_cases()
            self._randomly_choose_time_steps()
            self._determine_unchosen_time_steps()
        

        # set up the virtual OpenFoam directory for Offline (bases are kept here)
        self._set_virtual_OpenFoam_directory()


    def _replicate_directory_structure(self):
    
        for root, dirs, files in os.walk(self.source_directory):
            # Create corresponding directories in the target location
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                target_path = dir_path.replace(
                    self.source_directory, self.symlinked_cases_directory
                )
                os.makedirs(target_path, exist_ok=True)

    def _create_symlinks_of_files_to_the_files_in_original_directory(self):
        
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

    def _list_cases_in_symlinked_directory(self):
  
        # sort them according to the numeric value (assuming case name is numeric string)
        self.list_cases = os.listdir(self.symlinked_cases_directory)
        # Number of cases
        self.Ncases = len(self.list_cases)
        file_name = "case_list.csv"
        data = [[case] for case in self.list_cases]
        col_head_list = ["case"]
        self._write_in_a_CSV(file_name, data, col_head_list)

    def _build_dict_time_steps_for_each_case(self):
        
        # initialize
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
        col_head_list = ["case", "time_steps", "Ntime_steps"]
        self._write_in_a_CSV(file_name, data, col_head_list)

    def _write_in_a_CSV(self, file_name, data, col_head_list):
       
        with open(file_name, "w", newline="") as csvfile:
            # create an instance of a writer object
            csv_writer = csv.writer(csvfile)
            # write header
            csv_writer.writerow(col_head_list)
            for unit in data:
                csv_writer.writerow(unit)

    def _randomly_choose_cases(self):
        
        # determine the number of chosen cases
        self.Nchosen_cases = int(np.ceil(self.case_fraction_min * self.Ncases))
        # randomly sample the cases
        self.chosen_cases = random.sample(self.list_cases, self.Nchosen_cases)

        # save chosen cases in a csv file
        file_name_chosen_case = "chosen_cases.csv"
        data_chosen_case = [[case] for case in self.chosen_cases]
        col_head_list_chosen_case = ["Chosen_Case"]
        self._write_in_a_CSV(
            file_name_chosen_case, data_chosen_case, col_head_list_chosen_case
        )


    def _determine_unchosen_cases(self):
        
        # create list of the unchosen cases
        chosen_set = set(self.chosen_cases)
        self.unchosen_cases = [
            case for case in self.list_cases if case not in chosen_set
        ]
        # save unchosen cases in a csv file
        file_name_unchosen_case = "unchosen_cases.csv"
        data_unchosen_case = [[case] for case in self.unchosen_cases]
        col_head_list_unchosen_case = ["Unchosen_Case"]
        self._write_in_a_CSV(
            file_name_unchosen_case, data_unchosen_case, col_head_list_unchosen_case
        )

    def _randomly_choose_time_steps(self):
        
        # initialize dictionaries
        self.Nchosen_time_steps_for_each_chosen_case = {}
        self.chosen_time_steps_for_each_chosen_case = {}
        #dictionary storing directory paths
        self.directory_paths_for_chosen_time_steps_for_each_chosen_case = {}

        # to save in a csv file
        data_chosen_time_steps = []

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
            self.chosen_time_steps_for_each_chosen_case[cs] = sorted(
                self.chosen_time_steps_for_each_chosen_case[cs], key=float
            )

            chosen_time_steps_str = ",".join(
                self.chosen_time_steps_for_each_chosen_case[cs]
            )
            data_chosen_time_steps.append(
                [
                    cs,
                    chosen_time_steps_str,
                    self.Nchosen_time_steps_for_each_chosen_case[cs],
                ]
            )
            time_steps_case = self.chosen_time_steps_for_each_chosen_case[cs]
            self.directory_paths_for_chosen_time_steps_for_each_chosen_case[cs] = self._build_paths(time_steps_case, cs)


        file_name_chosen = "chosen_time_steps_each_case.csv"
        col_head_list = ["case", "time_steps", "Ntime_steps"]
        self._write_in_a_CSV(file_name_chosen, data_chosen_time_steps, col_head_list)

    def _determine_unchosen_time_steps(self):
        
        # initialize
        self.unchosen_time_steps_for_each_chosen_case = {}
        self.unchosen_time_steps_for_each_unchosen_case = {}
        # to save in a csv file

        data_unchosen_time_steps = []

        self.directory_paths_for_unchosen_time_steps_for_each_chosen_case = {}
        self.directory_paths_for_unchosen_time_steps_for_each_unchosen_case = {}

        for cs in self.chosen_cases:
            # chosen case, unchosen time steps
            chosen_set = set(self.chosen_time_steps_for_each_chosen_case[cs])
            self.unchosen_time_steps_for_each_chosen_case[cs] = [
                time_step
                for time_step in self.time_steps_for_each_case[cs]
                if time_step not in chosen_set
            ]
            self.unchosen_time_steps_for_each_chosen_case[cs] = sorted(
                self.unchosen_time_steps_for_each_chosen_case[cs], key=float
            )
            unchosen_time_steps_str = ",".join(
                self.unchosen_time_steps_for_each_chosen_case[cs]
            )
            data_unchosen_time_steps.append(
                [
                    cs,
                    unchosen_time_steps_str,
                    self.Ntime_steps_each_case[cs]
                    - self.Nchosen_time_steps_for_each_chosen_case[cs],
                ]
            )
            time_steps_case = self.unchosen_time_steps_for_each_chosen_case[cs]
            self.directory_paths_for_unchosen_time_steps_for_each_chosen_case[cs] = self._build_paths(time_steps_case, cs)

        for cs in self.unchosen_cases:
            #unchosen case unchosen time steps
            self.unchosen_time_steps_for_each_unchosen_case[cs] = self.time_steps_for_each_case[cs]
            time_steps_case = self.unchosen_time_steps_for_each_unchosen_case[cs]
            self.directory_paths_for_unchosen_time_steps_for_each_unchosen_case[cs] = self._build_paths(time_steps_case, cs)

        file_name_unchosen = "unchosen_time_steps_each_case.csv"
        col_head_list = ["case", "time_steps", "Ntime_steps"]
        self._write_in_a_CSV(file_name_unchosen, data_unchosen_time_steps, col_head_list)

    def _set_virtual_OpenFoam_directory(self):
        
        # select a case, it could be random
        cs = self.chosen_cases[0]
        case_dir = os.path.join(self.symlinked_cases_directory, cs)

        # build source directory path to copy
        system_dir_in_case_dir = os.path.join(case_dir, "system")
        constant_dir_in_case_dir = os.path.join(case_dir, "constant")
        zero_dir_in_case_dir = os.path.join(case_dir, "0")

        # build target directory path to copy to
        system_dir_in_virtual_OpenFoam_directory = os.path.join(
            self.bases_directory, "system"
        )
        if os.path.exists(system_dir_in_virtual_OpenFoam_directory):
            shutil.rmtree(system_dir_in_virtual_OpenFoam_directory)
        constant_dir_in_virtual_OpenFoam_directory = os.path.join(
            self.bases_directory, "constant"
        )
        if os.path.exists(constant_dir_in_virtual_OpenFoam_directory):
            shutil.rmtree(constant_dir_in_virtual_OpenFoam_directory)
        zero_dir_in_virtual_OpenFoam_directory = os.path.join(self.bases_directory, "0")
        if os.path.exists(zero_dir_in_virtual_OpenFoam_directory):
            shutil.rmtree(zero_dir_in_virtual_OpenFoam_directory)

        # create directories in the virtual OF directory for the application of an Algorithm
        os.makedirs(zero_dir_in_virtual_OpenFoam_directory, exist_ok=True)
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
        shutil.copytree(
            zero_dir_in_case_dir,
            zero_dir_in_virtual_OpenFoam_directory,
            dirs_exist_ok=True,
            symlinks=True,
        )

    def make_dir_for_bases_in_virtual_OpenFoam_directory(
        self, index_basis
    ):
        
        # construct the path
        dir_path = os.path.join(self.bases_directory, dir_name)
        # make the directory
        os.makedirs(dir_path, exist_ok=True)

        return dir_path

    def _parse_time_steps_from_file_chosen_time_steps(self):
        
        # initialize
        self.Nchosen_time_steps_for_each_chosen_case = {}
        self.chosen_time_steps_for_each_chosen_case = {}
        self.chosen_cases = []

        with open(self.file_path_chosen_time_steps, "r") as file:
            reader = csv.reader(file)
            # Skip header row
            next(reader)
            self.directory_paths_for_chosen_time_steps_for_each_chosen_case = {}
            for row in reader:
                # Ensure we have all three columns
                if len(row) == 3:
                    case_name = row[0]
                    time_steps_str = row[1]
                    n_time_steps = int(row[2])

                    # Parse the time steps string - remove quotes if present
                    if time_steps_str.startswith('"') and time_steps_str.endswith('"'):
                        time_steps_str = time_steps_str[1:-1]

                    # Split the time steps string
                    time_steps = [step.strip() for step in time_steps_str.split(",")]

                    # Store in dictionaries
                    self.chosen_time_steps_for_each_chosen_case[case_name] = time_steps
                    self.Nchosen_time_steps_for_each_chosen_case[case_name] = n_time_steps

                    # store in list
                    self.chosen_cases.append(case_name)

                    #build directory path
                    time_steps_case = self.chosen_time_steps_for_each_chosen_case[case_name]
                    self.directory_paths_for_chosen_time_steps_for_each_chosen_case[case_name] = self._build_paths(time_steps_case, case_name)
                else:
                    raise FileNotFoundError("File is not of expected structure")

    def _build_paths(self, time_steps_case, case):
        temp_dict = {}
        for time_step in time_steps_case:
            dir_path = os.path.join(self.symlinked_cases_directory, case, time_step)
            temp_dict[time_step] = dir_path
        return temp_dict



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
    parser.add_argument(
        "--case_fraction",
        type=float,
        default=0.7,
        help="Minimum fraction of cases to use",
    )
    parser.add_argument(
        "--snap_fraction",
        type=float,
        default=0.8,
        help="Minimum fraction of snapshots per case to use",
    )
    parser.add_argument(
        "--file_name", default=None, help="File name of the chosen time steps"
    )

    args = parser.parse_args()

    # Create and use the Snapshot_manager
    sm = Snapshot_manager(
        source_directory=args.source,
        project_directory=args.project_directory,
        case_fraction_min=args.case_fraction,
        snap_fraction_per_case_min=args.snap_fraction,
        file_name_chosen_time_steps=args.file_name,
    )

    # Set up the environment
    sm.set_environment()
    print(f"Selected {len(sm.chosen_cases)} cases out of {sm.Ncases}")
    