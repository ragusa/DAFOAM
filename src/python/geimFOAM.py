import numpy as np
import shutil
import os
import copy
import sys
from pathlib import Path

# Add the root directory to Python's path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))
from tools.linAlg4Foam.linAlg4Foam import * 

#this function is used to get the  case_name and time from for formatted snapshot path value like "case_name/time_name"
# moreover, and more importantly, it is used to get the region and field_name from a formatted field "region/field_name"
def split_on_slash(input_string):
        if '/' in input_string:
            before, after = input_string.split('/', 1)
        else:
            before = ''
            after = input_string
        return before, after


class GeimFOAM_offline:
    def __init__(self, rank,  snapshot_manager_object, observable_fields = None, non_observable_fields = None):
        self.rank = rank
        self.snapshot_manager_object = snapshot_manager_object
        self.list_observable_fields = observable_fields
        if self.list_observable_fields is None:
            raise ValueError("Observable fields must be provided.")
        self.Nfields = len(self.list_observable_fields)
        self.list_non_observable_fields = non_observable_fields
        # create a list of all fields, observable and non-observable
        self.all_fields = copy.deepcopy(self.list_observable_fields) + copy.deepcopy(self.list_non_observable_fields) if self.list_non_observable_fields is not None else self.list_observable_fields

        # it is assumed that snapshot_manager_object  comes with a list of chosen snapshots
        self.list_chosen_snaps = self.snapshot_manager_object.list_chosen_snapshot_paths
        self.Ntraining_set = len(self.list_chosen_snaps)
        self.virtual_openFoam_directory =  self.snapshot_manager_object.virtual_openFoam_directory
        self.symlinked_directory = self.snapshot_manager_object.symlinked_cases_directory

        #initialize directories
        #we may want to change the parent directory to virtual_openFoam_directory later. It's done the way now it is to avoid the clever getaround of the structure of the linnalg4Foam package.
        self.bases_directory = os.path.join(self.symlinked_directory, "bases_directory")
        if not os.path.exists(self.bases_directory):
            os.makedirs(self.bases_directory)

        # create a basis directory for each basis. The bases for all the fields get stored following the OF time directory structure.
        for i in range(rank):
            basis_dir = os.path.join(self.bases_directory, str(i+1))
            if not os.path.exists(basis_dir):
                os.makedirs(basis_dir)
        # make it so that it has necessary system and constant directories
        self._set_vod(self.bases_directory)

        # in the same way, we create two directories for each reconstructed snap- reconstructed and residual. This allows us to keep the book keeping minimal and address the fields in the same way as they are in the original snapshots.
        self.list_reconstructed_snaps = []
        self.list_residual_snaps = []
        for snap in self.list_chosen_snaps:
            case, time = split_on_slash(snap)
            self.list_reconstructed_snaps.append(case+"_Reconstructed/"+time)
            self.list_residual_snaps.append(case+"_Residual/"+time)
            if not os.path.exists(os.path.join(self.symlinked_directory, case+"_Reconstructed", "system")):
                self._set_vod(os.path.join(os.path.join(self.symlinked_directory, case+"_Reconstructed")))
                self._set_vod(os.path.join(os.path.join(self.symlinked_directory, case+"_Residual")))
                
        #initialization
        self.list_points = []
        self.list_bases_snap = []
        self.scaling_factor = []
        
        self.list_sensor_to_field = []
        self.list_sensor_to_basis_paths = []
        self.A = np.zeros((rank, rank))

    #This method is the driver of the whole GEIM algorithm. 
    def run_geim(self):
        # generate the norm for each time step.
        self.L2_norm_snaps = self._generate_L2_norm_snaps(list_snaps=self.list_chosen_snaps, relative=False)
        # find bases
        self._find_bases()
    
    # This method copies the system and constant directories from the first case in the symlinked directory to newly created directory of concern.
    def _set_vod(self, dir_of_concern):
        # select a case, it could be random
        cs = self.snapshot_manager_object.list_cases[0]
        case_dir = os.path.join(self.symlinked_directory, cs)

        # build source directory path to copy
        system_dir_in_case_dir = os.path.join(case_dir, "system")
        constant_dir_in_case_dir = os.path.join(case_dir, "constant")
    
        # build target directory path to copy to
        system_dir_in_dir_of_concern = os.path.join(dir_of_concern, "system")
        shutil.rmtree(system_dir_in_dir_of_concern) if os.path.exists(system_dir_in_dir_of_concern) else None
        constant_dir_in_dir_of_concern = os.path.join(dir_of_concern, "constant")
        shutil.rmtree(constant_dir_in_dir_of_concern) if os.path.exists(constant_dir_in_dir_of_concern) else None
        # create directories in the virtual OF directory for the application of an Algorithm
        os.makedirs(constant_dir_in_dir_of_concern, exist_ok=True)
        os.makedirs(system_dir_in_dir_of_concern, exist_ok=True)
        # copy the directory to the virtual OF directory
        shutil.copytree(system_dir_in_case_dir, system_dir_in_dir_of_concern, dirs_exist_ok=True, symlinks=True)
        shutil.copytree(constant_dir_in_case_dir, constant_dir_in_dir_of_concern, dirs_exist_ok=True, symlinks=True)
    
    
    #It does the what the name suggests, it generates the L2 norm of the snapshots be it residual or original snaps
    # For the original snaps, we don't do the relative norm, but for the residual snaps, we do the relative norm.
    def _generate_L2_norm_snaps(self, list_snaps, relative=True):
        L2norm_data = linAlg4Foam.L2norm(self.virtual_openFoam_directory, list_snaps, self.list_observable_fields)
        L2_norm_snaps = np.zeros((self.Nfields, self.Ntraining_set))
        for i_snap, snap in enumerate(list_snaps):
            for i_field, field in enumerate(self.list_observable_fields):
                L2_norm_snaps[i_field, i_snap] = float(L2norm_data[snap][field][0])
                if relative == True:
                    L2_norm_snaps[i_field, i_snap] = L2_norm_snaps[i_field, i_snap] / self.L2_norm_snaps[i_field, i_snap] 

        return L2_norm_snaps
    
    # This method is the de factor driver of the GEIM algorithm. It finds the bases, finds the sensor field, sensor locations, and builds the matrix A. 
    def _find_bases(self):
        count_basis = 0
        sensor_snap, sensor_field = self._keep_the_book(count_basis=count_basis, norm_resid_snaps=self.L2_norm_snaps)
        self._generate_a_basis(count_basis=count_basis, sensor_snap=sensor_snap, sensor_field=sensor_field)
        self._build_matrix_A(count_basis=count_basis)
        self._reconstruct_training_space(self.A[:count_basis + 1, :count_basis + 1])

        for count_basis in range(1, self.rank):
            self._determine_residual_snaps()
            norm_residual_snaps = self._generate_L2_norm_snaps(self.list_residual_snaps)
            sensor_snap, sensor_field = self._keep_the_book(count_basis=count_basis, norm_resid_snaps=norm_residual_snaps)
            self._generate_a_basis(count_basis=count_basis, sensor_snap=sensor_snap, sensor_field=sensor_field)
            self._build_matrix_A(count_basis=count_basis)
            self._reconstruct_training_space(self.A[:count_basis + 1, :count_basis + 1])
    # This method keeps track of the bases, sensor fields, and points. It also determines the maximizing position for the sensor. Just for bookkeeping.
    def _keep_the_book(self, count_basis, norm_resid_snaps):
        coord_max = self._find_argmax_snap_index(norm_resid_snaps=norm_resid_snaps)
        field_index, snap_index = coord_max
        if count_basis == 0:
            self.list_bases_snap.append(self.list_chosen_snaps[snap_index])
        else:
            self.list_bases_snap.append(self.list_residual_snaps[snap_index])

        self.list_sensor_to_field.append(self.list_observable_fields[field_index])
        sensor_snap = self.list_bases_snap[count_basis]
        sensor_field = self.list_sensor_to_field[count_basis]
        sensor_point = self._determine_maximizing_position(sensor_snap, sensor_field)
        self.list_points.append(sensor_point)
        return sensor_snap, sensor_field

    # This method finds the index of the maximum value in the norm residual snapshots.
    # It returns the coordinates of the maximum value in the form of a tuple (field_index, snap_index).
    # The maximum value determine the field for which the sensor should be selected.
    def _find_argmax_snap_index(self, norm_resid_snaps):
        index_max_final = np.argmax(norm_resid_snaps)
        coord_max = np.unravel_index(index_max_final, norm_resid_snaps.shape)
        return coord_max
    
    # for a determined field, this method determines the maximizing position in the field.
    # It returns the point in the field where the maximum value is located.

    def _determine_maximizing_position(self, snap, field):
        minima, maxima = linAlg4Foam.internalFieldMinMax(self.virtual_openFoam_directory, [snap], [field])
        point_max, max_at_maximizing_position = maxima[snap][field] 
        point_min, min_at_minimizing_position = minima[snap][field]

        max_mag = float(max_at_maximizing_position)
        point = point_max
        
        if np.abs(max_mag) < np.abs(float(min_at_minimizing_position)):
            point = point_min
            max_mag = float(min_at_minimizing_position)
        self.scaling_factor.append(max_mag)
        point = self._string_to_float_tuple(point)
        return point
    
    # This method converts a string representation of a point (e.g., "(1.0 2.0 3.0)") into a tuple of floats.
    def _string_to_float_tuple(self, point_string):
        # Remove parentheses and split by whitespace
        cleaned = point_string.strip('()')
        numbers = cleaned.split()
        # Convert to floats and return as tuple
        point_tuple = tuple(float(num) for num in numbers)
        return point_tuple

    # This method does the bookkeeping and logistics of the basis generation
    def _generate_a_basis(self, count_basis, sensor_snap, sensor_field):
        for field in self.all_fields:
            region, field_name = split_on_slash(field)
            copy_source = os.path.join(self.symlinked_directory, sensor_snap, field)
            dest_dir = os.path.join(self.bases_directory, str(count_basis + 1), region)
            copy_target = os.path.join(dest_dir, field_name)
            # Ensure directory exists and copy
            os.makedirs(dest_dir, exist_ok=True)
            shutil.copy2(copy_source, copy_target)
        current_basis_path =os.path.join("bases_directory/" + str(count_basis + 1))
        self.list_sensor_to_basis_paths.append(current_basis_path)

    #This method builds the system matrix in each iteration of the GEIM algorithm.
    def _build_matrix_A(self, count_basis):
        for i in range(count_basis + 1):
                for j in range(count_basis + 1):
                    if i == count_basis or j == count_basis:
                        sensor_point_i = self.list_points[i]
                        sensor_field_i = self.list_sensor_to_field[i]
                        sensor_basis_j = self.list_sensor_to_basis_paths[j]
                        sensoring_results = linAlg4Foam.readFromPoints(self.virtual_openFoam_directory, [sensor_basis_j], [sensor_field_i], [sensor_point_i])
                        self.A[i, j] = float(sensoring_results[sensor_basis_j][sensor_field_i][1]) / self.scaling_factor[i]

    # This method reconstructs the training space using the matrix A and the sensor data.
    # It reads the sensor data from the already determined points and computes the coefficients to reconstruct the snapshots.
    def _reconstruct_training_space(self, mat_A):
        [n_rows, n_columns] = mat_A.shape
        scaled_dirac_measure_data = np.zeros((n_rows, len(self.list_chosen_snaps)))
        for i in range(n_rows):
            sensor_point = self.list_points[i]
            sensor_field = self.list_sensor_to_field[i]
            sensoring_results = linAlg4Foam.readFromPoints(self.virtual_openFoam_directory, self.list_chosen_snaps, [sensor_field], [sensor_point])
            for j, snap in enumerate(self.list_chosen_snaps):
                scaled_dirac_measure_data[i,j] = float(sensoring_results[snap][sensor_field][1]) / self.scaling_factor[i]
        coeffs = np.linalg.solve(mat_A, scaled_dirac_measure_data)
        for i, snap in enumerate(self.list_chosen_snaps):
            coeffs_list = [float(x) for x in coeffs[:,i].flatten()]
            reconstructed_snap = self.list_reconstructed_snaps[i]
            for field in self.all_fields:
                region, field_name = split_on_slash(field)
                linAlg4Foam.linearCombination(self.virtual_openFoam_directory, [self.list_sensor_to_basis_paths], [field], [coeffs_list], [os.path.join("../symlinked_cases", reconstructed_snap, region)])
    # This method determines the residual by subtracting the reconstructed snapshots from the original snapshots.
    def _determine_residual_snaps(self):
        for i, snap in enumerate(self.list_chosen_snaps):
                reconstructed_snap = self.list_reconstructed_snaps[i]
                residual_snap = self.list_residual_snaps[i]
                for field in self.all_fields:
                    region, field_name = split_on_slash(field)
                    linAlg4Foam.linearCombination(self.virtual_openFoam_directory, [[snap, reconstructed_snap]], [field], [[1, -1]], [os.path.join("../symlinked_cases", residual_snap, region)])

# This class is used to reconstruct the snapshots online using the GEIM algorithm.
class GeimFOAM_online:
    def __init__(self, geim_offline_object, snaps, rank_reconstruct = None):
        self.geim_offline = geim_offline_object
        self.snaps = snaps
        if rank_reconstruct is None:
            self.rank_reconstruct = geim_offline_object.rank
        else:
            self.rank_reconstruct = rank_reconstruct

        self.all_fields = self.geim_offline.all_fields
        self.list_points = self.geim_offline.list_points
        self.scaling_factor = self.geim_offline.scaling_factor
        self.list_sensor_to_field = self.geim_offline.list_sensor_to_field
        self.list_sensor_to_basis_paths = self.geim_offline.list_sensor_to_basis_paths
        self.virtual_openFoam_directory =  self.geim_offline.virtual_openFoam_directory
        self.A = self.geim_offline.A[:self.rank_reconstruct, :self.rank_reconstruct]

        # We create a directory for each snap in the symlinked directory. Reconstruted snapshots are named as shown.
        self.list_reconstructed_snaps = []
        for snap in self.snaps:
            case, time = split_on_slash(snap)
            self.list_reconstructed_snaps.append(case+"_online_Reconstructed/"+time)
    # For a list of snapshots, this method reconstructs each snapshot using the coefficients obtained from the sensor data and the bases. The coefficients are obtained by solving the linear system defined 
    # by the system matrix and the sensor data.
    def reconstruct_snaps(self):
        scaled_dirac_measure_data = np.zeros((self.rank_reconstruct, len(self.snaps)))
        for i in range(self.rank_reconstruct):
            sensor_point = self.list_points[i]
            sensor_field = self.list_sensor_to_field[i]
            sensoring_results = linAlg4Foam.readFromPoints(self.virtual_openFoam_directory, self.snaps, [sensor_field], [sensor_point])
            for j, snap in enumerate(self.snaps):
                scaled_dirac_measure_data[i,j] = float(sensoring_results[snap][sensor_field][1]) / self.scaling_factor[i]
        coeffs = np.linalg.solve(self.A, scaled_dirac_measure_data)
        for i, snap in enumerate(self.snaps):
            coeffs_list = [float(x) for x in coeffs[:,i].flatten()]
            reconstructed_snap = self.list_reconstructed_snaps[i]
            for field in self.all_fields:
                region, field_name = split_on_slash(field)
                linAlg4Foam.linearCombination(self.virtual_openFoam_directory, [self.list_sensor_to_basis_paths[:self.rank_reconstruct]], [field], [coeffs_list], [os.path.join("../symlinked_cases", reconstructed_snap, region)])
