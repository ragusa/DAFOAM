import shutil
import os
import numpy as np
import random
import csv


class Snapshot_manager:
    """
    Manages OpenFOAM case snapshots for data assimilation algorithms.
    
    This class handles the organization of OpenFOAM simulation cases and time steps,
    creating appropriate directory structures with symlinks to original data.
    It supports random selection of cases and time steps for offline training
    and online testing/application phases.
    
    Attributes:
        # Input attributes
        source_directory (str): Path to directory containing OpenFOAM cases
        project_directory (str): Path to directory for the DA algorithm application
        case_fraction_min (float): Minimum fraction of cases to use
        snap_fraction_per_case_min (float): Minimum fraction of snapshots per case to use
        file_name_chosen_time_steps (str, optional): File name with prespecified time steps for training of a DA algorithm
        
        # Derived attributes (created during initialization)
        symlinked_cases_directory (str): Path to directory with symlinked cases
        offline_directory (str): Path to directory for offline phase of the application of the DA algorithm
        online_directory (str): Path to directory for online phase data of the application of the DA algorithm
        
        # Runtime attributes (created during operation)
        list_cases (list): List of all numerical case names found in the symlinked directory
        Ncases (int): Total number of cases found
        time_steps_for_each_case (dict): Dictionary mapping case names to their time steps
        Ntime_steps_each_case (dict): Dictionary mapping case names to number of time steps available
        chosen_cases (list): List of cases selected for training
        unchosen_cases (list): List of cases not selected for training
        Nchosen_cases (int): Number of selected cases
        chosen_time_steps_for_each_chosen_case (dict): Dictionary mapping chosen cases to their selected time steps
        Nchosen_time_steps_for_each_chosen_case (dict): Dictionary mapping chosen cases to number of selected time steps
        unchosen_time_steps_for_each_chosen_case (dict): Dictionary mapping chosen cases to their unselected time steps
    
    Methods(public):
        set_environment(): Main method to set up the entire environment including directories and data selection
        make_dir_in_virtual_OpenFoam_directory(name_virtual_OF_directory, case, time_step): Creates snapshot directory for a specified case/time step in a virtual openfoam directory
        copy_a_snap_to_the_online_directory(dir_path, OF_case, time_step): Copies a snapshot to the online directory
    """

    def __init__(
        self,
        source_directory,
        project_directory,
        case_fraction_min,
        snap_fraction_per_case_min,
        file_name_chosen_time_steps=None,
    ):
        """
        Initialize the Snapshot_manager.
        
        Args:
            source_directory (str): Path to directory containing OpenFOAM cases
            project_directory (str): Path to directory for the DA algorithm application
            case_fraction_min (float): Minimum fraction of cases to use
            snap_fraction_per_case_min (float): Minimum fraction of snapshots per case to use
            file_name_chosen_time_steps (str, optional): File name with prespecidied time steps for testing
        """
        # it is assumed that in the source directory which holds the cases, the cases are named numerically with unique name each
        self.source_directory = source_directory
        self.project_directory = project_directory
        self.symlinked_cases_directory = os.path.join(
            project_directory, "symlinked_cases"
        )
        if os.path.exists(self.symlinked_cases_directory):
            shutil.rmtree(self.symlinked_cases_directory)

        self.offline_directory = os.path.join(
            self.project_directory, "offline_directory"
        )
        if os.path.exists(self.offline_directory):
            shutil.rmtree(self.offline_directory)

        self.online_directory = os.path.join(self.project_directory, "online_directory")
        if os.path.exists(self.online_directory):
            shutil.rmtree(self.online_directory)

        self.case_fraction_min = case_fraction_min
        self.snap_fraction_per_case_min = snap_fraction_per_case_min
        self.file_name_chosen_time_steps = file_name_chosen_time_steps

    def _replicate_directory_structure(self):
        """
        Replicate the directory structure from source directory to symlinked directory.
        
        Creates corresponding directories in the target location based on the
        directory structure in the source location.
        """
        for root, dirs, files in os.walk(self.source_directory):
            # Create corresponding directories in the target location
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                target_path = dir_path.replace(
                    self.source_directory, self.symlinked_cases_directory
                )
                os.makedirs(target_path, exist_ok=True)

    def _create_symlinks_of_files_to_the_files_in_original_directory(self):
        """
        Create symlinks to files in original directory.
        
        Creates symbolic links in the target location 
        (previously determined directory structure in the method replicate_directory_structure) 
        pointing to
        the files in the source location.
        """
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

    def _is_numeric(self, value):
        """
        Check if a value is numeric.
        
        Args:
            value: Value to check
            
        Returns:
            bool: True if value is numeric, False otherwise
        """
        try:
            # Attempt to convert to a float
            float(value)
            # Conversion successful
            return True
        except ValueError:
            # Conversion fails if the value is not numeric
            return False

    def _list_cases_in_symlinked_directory(self):
        """
        List and sort cases in the symlinked directory.
        
        Identifies and sorts the case directories (with numeric names)
        in the symlinked directory. Saves the list to a CSV file.
        """
        # list directory
        self._list_dirs = os.listdir(self.symlinked_cases_directory)
        # list cases
        self.list_cases = [
            k
            for k in self._list_dirs
            if self._is_numeric(k)
            and os.path.isdir(os.path.join(self.symlinked_cases_directory, k))
        ]
        # sort them according to the numeric value (assuming case name is numeric string)
        self.list_cases = sorted(self.list_cases, key=float)
        # Number of cases
        self.Ncases = len(self.list_cases)
        file_name = "case_list.csv"
        data = self.list_cases
        col_head_list = ["case"]
        self._write_in_a_CSV(file_name, data, col_head_list)

    def _build_dict_time_steps_for_each_case(self):
        """
        Build dictionaries of time steps for each case.
        
        Creates dictionaries containing time steps for each case
        and the count of time steps. Saves the information to a CSV file.
        """
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
        """
        Write data to a CSV file.
        
        Args:
            file_name (str): Name of the CSV file to write
            data (list): Data to write
            col_head_list (list): List of column headers
        """
        with open(file_name, "w", newline="") as csvfile:
            # create an instance of a writer object
            csv_writer = csv.writer(csvfile)
            # write header
            csv_writer.writerow(col_head_list)
            for unit in data:
                csv_writer.writerow(unit)

    def _randomly_choose_cases(self):
        """
        Randomly select cases from the list of cases.
        
        Selects a random subset of cases based on case_fraction_min.
        Saves the chosen cases to a CSV file.
        """
        # determine the number of chosen cases
        self.Nchosen_cases = int(np.ceil(self.case_fraction_min * self.Ncases))
        # randomly sample the cases
        self.chosen_cases = random.sample(self.list_cases, self.Nchosen_cases)

        # save chosen cases in a csv file
        file_name_chosen_case = "chosen_cases.csv"
        data_chosen_case = self.chosen_cases
        col_head_list_chosen_case = ["Chosen_Case"]
        self._write_in_a_CSV(
            file_name_chosen_case, data_chosen_case, col_head_list_chosen_case
        )

    def _determine_unchosen_cases(self):
        """
        Determine unchosen cases from the list of cases.
        
        Creates a list of cases not chosen in _randomly_choose_cases.
        Saves the unchosen cases to a CSV file.
        """
        # create list of the unchosen cases
        chosen_set = set(self.chosen_cases)
        self.unchosen_cases = [
            case for case in self.list_cases if case not in chosen_set
        ]
        # save unchosen cases in a csv file
        file_name_unchosen_case = "unchosen_cases.csv"
        data_unchosen_case = self.unchosen_cases
        col_head_list_unchosen_case = ["Unchosen_Case"]
        self._write_in_a_CSV(
            file_name_unchosen_case, data_unchosen_case, col_head_list_unchosen_case
        )

    def _randomly_choose_time_steps(self):
        """
        Randomly select time steps for each chosen case.
        
        Selects a random subset of time steps for each chosen case
        based on snap_fraction_per_case_min. Saves the chosen time steps to a CSV file.
        """
        # initialize dictionaries
        self.Nchosen_time_steps_for_each_chosen_case = {}
        self.chosen_time_steps_for_each_chosen_case = {}

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

        file_name_chosen = "chosen_time_steps_each_case.csv"
        col_head_list = ["case", "time_steps", "Ntime_steps"]
        self._write_in_a_CSV(file_name_chosen, data_chosen_time_steps, col_head_list)

    def _determine_unchosen_time_steps(self):
        """
        Determine unchosen time steps for each chosen case.
        
        Creates a list of time steps not chosen in _randomly_choose_time_steps
        for each chosen case. Saves the unchosen time steps to a CSV file.
        """
        # initialize
        self.unchosen_time_steps_for_each_chosen_case = {}
        # to save in a csv file
        data_unchosen_time_steps = []

        for cs in self.chosen_cases:
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

        file_name_unchosen = "unchosen_time_steps_each_case.csv"
        col_head_list = ["case", "time_steps", "Ntime_steps"]
        self._write_in_a_CSV(file_name_unchosen, data_unchosen_time_steps, col_head_list)

    def _set_virtual_OpenFoam_directory(self, directory_path):
        """
        Set up a virtual OpenFOAM directory.
        
        Creates the standard OpenFOAM directory structure (system, constant, 0)
        in the specified directory and copies the necessary files.
        
        Args:
            directory_path (str): Path to create the virtual OpenFOAM directory
        """
        # select a case, it could be random
        cs = self.chosen_cases[0]
        case_dir = os.path.join(self.symlinked_cases_directory, cs)

        # build source directory path to copy
        system_dir_in_case_dir = os.path.join(case_dir, "system")
        constant_dir_in_case_dir = os.path.join(case_dir, "constant")
        zero_dir_in_case_dir = os.path.join(case_dir, "0")

        # build target directory path to copy to
        system_dir_in_virtual_OpenFoam_directory = os.path.join(
            directory_path, "system"
        )
        if os.path.exists(system_dir_in_virtual_OpenFoam_directory):
            shutil.rmtree(system_dir_in_virtual_OpenFoam_directory)
        constant_dir_in_virtual_OpenFoam_directory = os.path.join(
            directory_path, "constant"
        )
        if os.path.exists(constant_dir_in_virtual_OpenFoam_directory):
            shutil.rmtree(constant_dir_in_virtual_OpenFoam_directory)
        zero_dir_in_virtual_OpenFoam_directory = os.path.join(directory_path, "0")
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

    def make_dir_in_virtual_OpenFoam_directory(
        self, name_virtual_OF_directory, case, time_step
    ):
        """
        Create a directory for a snap in the virtual OpenFOAM directory.
        
        Args:
            name_virtual_OF_directory (str): Path to the virtual OpenFOAM directory
            case (str): Case name
            time_step (str): Time step
            
        Returns:
            str: Path to the created directory
        """
        # create directory structure
        dir_name = case + "/" + time_step
        # construct the path
        dir_path = os.path.join(name_virtual_OF_directory, dir_name)
        # make the directory
        os.makedirs(dir_path, exist_ok=True)

        return dir_path

    def _copy_chosen_time_steps_to_virtual_OF_directory_offline(self):
        """
        Copy chosen time steps to the virtual OpenFOAM directory for offline phase.
        
        Copies the selected time steps for each chosen case to the offline directory for training phase.
        """
        # loop over the dictionary
        for key, value in self.chosen_time_steps_for_each_chosen_case.items():
            for t_step in value:
                # construct the source directory path to copy from
                source_dir_path = os.path.join(
                    self.symlinked_cases_directory, key, t_step
                )
                # construct the taget directory path to copy to
                target_dir_path = self.make_dir_in_virtual_OpenFoam_directory(
                    self.offline_directory, key, t_step
                )

                # copy the directory with symlinks
                shutil.copytree(
                    source_dir_path, target_dir_path, dirs_exist_ok=True, symlinks=True
                )

    def _parse_time_steps_from_file_chosen_time_steps(self):
        """
        Parse time steps from a CSV file.
        
        Reads chosen cases and time steps from the specified CSV file
        instead of randomly selecting them.
        """
        # initialize
        self.Nchosen_time_steps_for_each_chosen_case = {}
        self.chosen_time_steps_for_each_chosen_case = {}
        self.chosen_cases = []

        with open(self.file_path_chosen_time_steps, "r") as file:
            reader = csv.reader(file)
            # Skip header row
            next(reader)
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
                    self.Nchosen_time_steps_for_each_chosen_case[case_name] = (
                        n_time_steps
                    )

                    # store in list
                    self.chosen_cases.append(case_name)
                else:
                    raise FileNotFoundError("File is not of expected structure")

    def set_environment(self):
        """
        Set up the environment for data assimilation.
        
        Creates the necessary directory structure, selects cases and time steps
        (either randomly or from a file), and sets up virtual OpenFOAM directories
        for offline and online phases.
        
        Raises:
            FileNotFoundError: If the specified file for chosen time steps does not exist or has an invalid structure
        """

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
        

        # set a virtual OpenFoam directory for Offline
        self._set_virtual_OpenFoam_directory(self.offline_directory)
        self._copy_chosen_time_steps_to_virtual_OF_directory_offline()

        # set a virtual OpenFoam directory for Online
        self._set_virtual_OpenFoam_directory(self.online_directory)

    def copy_a_snap_to_the_online_directory(self, dir_path, OF_case, time_step):
        """
        Copy a snapshot to the online directory.
        
        Args:
            dir_path (str): Target directory path (online directory)
            OF_case (str): OpenFOAM case name
            time_step (str): Time step
        """
        self.real_cs_dir = os.path.join(self.symlinked_cases_directory, OF_case)
        self.real_time_dir = os.path.join(self.real_cs_dir, time_step)
        shutil.copytree(
            self.real_time_dir,
            dir_path,
            dirs_exist_ok=True,
            symlinks=True,
        )


if __name__ == "__main__":
    import argparse

    # Set up command line argument parsing
    parser = argparse.ArgumentParser(
        description="Manage OpenFOAM case snapshots for the Application of Data Assimilation Algorithms"
    )
    parser.add_argument(
        "--source", required=True, help="Source directory containing OpenFOAM cases"
    )
    parser.add_argument(
        "--project_directory",
        default=".",
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

    # Set up a test case
    firs_case = list(sm.unchosen_time_steps_for_each_chosen_case.keys())[0]
    time_step = sm.unchosen_time_steps_for_each_chosen_case[firs_case][0]

    dir_path = sm.make_dir_in_virtual_OpenFoam_directory(
        sm.online_directory, firs_case, time_step
    )
    sm.copy_a_snap_to_the_online_directory(dir_path, firs_case, time_step)