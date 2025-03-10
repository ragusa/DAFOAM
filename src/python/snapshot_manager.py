import os

class Snapshot_manager:
    def __init__(self, source_directory, target_directory):
        self.source_directory = source_directory
        self.target_directory = target_directory

    def replicate_directory_structure(self):
        for root, dirs, files in os.walk(self.source_directory):
            # Create corresponding directories in the target location
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                target_path = dir_path.replace(self.source_directory, self.target_directory)
                os.makedirs(target_path, exist_ok=True)
    
    def create_symlinks_of_files_to_the_files_in_original_directory(self):
        for root, dirs, files in os.walk(self.source_directory):
            for file in files:
                # Build the full path of the file in the source directory
                source_file = os.path.join(root, file)
                # Map the source file path to the corresponding target file path
                target_file = source_file.replace(self.source_directory, self.target_directory)
                # Check if the symbolic link (or file) already exists in the target; if not, create it.
                if not os.path.exists(target_file):
                    os.symlink(source_file, target_file)
    def is_numeric(self, value):
        try:
            float(value)  # Attempt to convert to a float
            return True   # Conversion successful
        except ValueError:
            return False  # Conversion fails if the value is not numeric

   
    def list_cases_target(self):
        self.list_dirs = os.listdir(self.target_directory)
        self.list_cases = [k for k in self.list_dirs if self.is_numeric(k) and os.path.isdir(os.path.join(target_directory, k))]
        self.list_cases = sorted(self.list_cases, key=float)
    
    def build_dict_time_steps_for_each_case(self):

        self.time_steps_for_each_case = {}
        
        for cs in self.list_cases:
            # List all items in the target  directory
            case_directory = os.path.join(self.target_directory, cs)
            list_current_directory = os.listdir(case_directory)

            # Filter directories that are named with numeric values and exist
            time_steps = [
                d
                for d in list_current_directory
                if d.isnumeric() and os.path.isdir(os.path.join(case_directory, d))
            ]
            # Sort time steps numerically
            time_steps = sorted(time_steps, key=float)
            self.time_steps_for_each_case[cs] = time_steps
    
            

        
            
