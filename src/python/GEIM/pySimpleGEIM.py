## MOST OF THE DEPENDENCIES ARE MISSING FOR NOW
import numpy as np
import copy
def split_on_slash(input_string):
        if '/' in input_string:
            before, after = input_string.split('/', 1)
        else:
            before = ''
            after = input_string
        return before, after


def define_norm_func(func):
    def definition(self, field_values, region):
        if self.norm_type == "L2":
            volumes = self.dict_centroids_and_volumes_by_region[region][1]
            return np.sqrt(np.sum(field_values ** 2 * volumes))
        elif self.norm_type == "Linf":
            return np.max(np.abs(field_values))
        else:
            raise ValueError(f"Unsupported norm type: {self.norm_type}")
    
    return definition
    
            
       
class pyGEIM_offline:

    def __init__(self, snaps_obj, rank, list_observable_fields, norm_type="L2"):
        self.snaps_obj = snaps_obj
        self.tot_cells_per_snap = self.snaps_obj.tot_cells_per_snap
        snaps_array = np.asarray(self.snaps_obj.snapshot_matrix_2D_training).copy()
    
        self.__snaps = snaps_array
        self.rank = rank
        self.list_fields = self.snaps_obj.list_fields_paths
        self.list_observable_fields = list_observable_fields
        self.list_indices_observable_fields = [self.list_fields.index(elem) for elem in self.list_observable_fields  if elem in self.list_fields ]
        self.list_non_observable_fields = list(set(self.list_fields) - set(self.list_observable_fields))
        self.list_indices_non_observable_fields = [self.list_fields.index(elem) for elem in self.list_non_observable_fields  if elem in self.list_fields ]
        self.list_field_to_range_cells = self.snaps_obj.list_field_to_range_cells
        self.Nsnaps = snaps_obj.Nsnapshots_training
        self.Nfields = len(self.list_fields)
        self.Nobs = len(self.list_observable_fields)

        self.dict_centroids_and_volumes_by_region = self.snaps_obj.dict_centroids_and_volumes_by_region
        self.norm_type = norm_type
        #approximation
        self.__J = np.zeros((self.tot_cells_per_snap, self.Nsnaps))
        self.norm_snaps = np.zeros((self.Nobs, self.Nsnaps))
        self.normalized_norm_residual_snaps = np.zeros((self.Nobs, self.Nsnaps))
        self.A = np.zeros((self.rank, self.rank))
        self.__residual_snaps =  np.zeros(self.__snaps.shape)
        self.indices_sensor_fields = np.zeros(self.rank, dtype=int)
        self.indices_sensor_snaps = np.zeros(self.rank, dtype=int)
        self.matrix_holding_bases = np.zeros((self.tot_cells_per_snap, self.rank))
        self.indices_position_sensors = np.zeros((self.rank), dtype=int)
        self.array_indices_maximizing_position = np.zeros((self.rank), dtype=int)
        self.scaling_factor = np.zeros((self.rank), dtype=float)
            
    def run_algorithm(self):
        for count_basis in range(self.rank):
            self.__residual_snaps = self.__snaps - self.__J
            self.__generate_norm_snaps(residual=False if count_basis==0 else True)
            self.__keep_the_book(count_basis=count_basis, norm_resid_snaps=self.norm_snaps if count_basis==0 else self.normalized_norm_residual_snaps)
            self.__build_A(count_basis=count_basis)
            self.__reconstruct_training_space(count_basis=count_basis)
    
    @define_norm_func 
    def __determine_norm_field(self, field_values, region):
        pass

    def __generate_norm_snaps(self, residual=True):
        for ii, field in enumerate(self.list_observable_fields):
            region, field_name = split_on_slash(field)
            index_field = self.list_indices_observable_fields[ii]
            (index_start, index_end) = self.list_field_to_range_cells[index_field]
            for jj in range(self.Nsnaps):
                if residual is False:
                    field_values = self.__snaps[index_start : index_end + 1, jj]
                    self.norm_snaps[ii, jj] = self.__determine_norm_field(field_values=field_values, region=region)
                else:
                    field_values = self.__residual_snaps[index_start : index_end + 1, jj]
                    self.normalized_norm_residual_snaps[ii, jj] = self.__determine_norm_field(field_values=field_values, region=region) / self.norm_snaps[ii, jj]

    def __keep_the_book(self, count_basis, norm_resid_snaps):
        (sensor_field_index, basis_snap_index) = self.__coord_maximizing_snap_finder(norm_resid_snaps)
        self.matrix_holding_bases[:, count_basis] = copy.deepcopy(self.__snaps[:, basis_snap_index])
        self.matrix_holding_bases[:, count_basis] = copy.deepcopy(self.__residual_snaps[:, basis_snap_index])
        (index_start, index_end) = self.list_field_to_range_cells[sensor_field_index]
        index_maximizing_position = np.argmax(np.abs(self.matrix_holding_bases[index_start : index_end + 1, count_basis]))
        self.array_indices_maximizing_position[count_basis] = int(index_maximizing_position + index_start)
        self.indices_position_sensors[count_basis] = index_maximizing_position
        self.indices_sensor_fields[count_basis] = sensor_field_index
        self.indices_sensor_snaps[count_basis] = basis_snap_index
        self.scaling_factor[count_basis] = self.matrix_holding_bases[self.array_indices_maximizing_position[count_basis], count_basis]

    def __build_A(self, count_basis):
        for i in range(count_basis + 1):
                for j in range(count_basis + 1):
                    if i == count_basis or j == count_basis:
                        self.A[i, j] = self.matrix_holding_bases[self.array_indices_maximizing_position[i], j] / self.scaling_factor[i]

    def __coord_maximizing_snap_finder(self, norms):
        index_obs_field, index_snap = np.unravel_index(np.argmax(norms), norms.shape)
        index_field = self.list_indices_observable_fields[index_obs_field]
        return (index_obs_field, index_snap)
  
    def __reconstruct_training_space(self, count_basis):
        mat_A = self.A[:count_basis + 1, :count_basis + 1]
        for index_snap in range(self.Nsnaps):
            b = np.asarray(self.__snaps[self.array_indices_maximizing_position[:count_basis + 1], index_snap]) / self.scaling_factor[:count_basis + 1]
            d_i = np.linalg.solve(mat_A, b)
            self.__J[:, index_snap] = self.matrix_holding_bases[:, :count_basis + 1] @ d_i
    
class pyGEIM_online:
    def __init__(self, offline_object, snaps_object, rank_upto):
        self.offline_object = offline_object
        self.A = self.offline_object.A
        self.array_indices_maximizing_position = self.offline_object.array_indices_maximizing_position
        self.rank_upto = rank_upto
        self.scaling_factor = self.offline_object.scaling_factor
        self.matrix_holding_bases = self.offline_object.matrix_holding_bases
        self.snaps_object = snaps_object
        self.snapshot_testing = self.snaps_object.snapshot_matrix_2D_testing
        self.Nsnaps = self.snapshot_testing.shape[1]
        self.J = np.zeros(self.snapshot_testing.shape)
        self.reconstruct_test_space()
        
    def reconstruct_test_space(self):
        for index_snap in range(self.Nsnaps):
            b = np.asarray(self.snapshot_testing[self.array_indices_maximizing_position[:self.rank_upto], index_snap]) / self.scaling_factor[:self.rank_upto]
            d_i = np.linalg.solve(self.A, b)
            self.J[:, index_snap] = self.matrix_holding_bases[:, :self.rank_upto] @ d_i
    


# Initialise the snapshot manager:
project_dir = "../DAFOAM/project_check_geim_foam"
source_dir = "../DAFOAM/examples/td_2D_MSFR/pumpPowerVariation/case_space"
sm_obj = sm.Snapshot_manager(source_dir, project_dir)  
sm_obj.set_environment()

# Define list of fields of interest and list of observable fields, identify the index of the observable fields within the list of fields of interest:
all_fields = ['fluidRegion/p','fluidRegion/T','neutroRegion/TFuel','neutroRegion/flux0','neutroRegion/flux1','neutroRegion/flux2','neutroRegion/flux3','neutroRegion/flux4','neutroRegion/flux5','neutroRegion/prec0','neutroRegion/prec1','neutroRegion/prec2','neutroRegion/prec3','neutroRegion/prec4','neutroRegion/prec5','neutroRegion/powerDensity']
obs_fields = ['fluidRegion/p', 'fluidRegion/T', 'neutroRegion/flux5']
obs_idx = [all_fields.index(field) for field in obs_fields]

# Assemble training array (3D array with snapshots, fields and locations):
asd = Snapshot_matrix_builder(sm_obj, all_fields)
training_array = np.array(asd.snapshot_matrix_3D)

# Identify the field with the maximum absolute value in the training matrix for the specified observation fields:
snp_idx, fld_idx, loc_idx = np.unravel_index(np.argmax(np.abs(training_array[:, obs_idx, :])), training_array[:, obs_idx, :].shape)

# Initialise sensors, scaling factors and basis:
list_magic_fields = [obs_idx[fld_idx]]
list_magic_points = [loc_idx]
list_scaling_factors = [training_array[snp_idx, obs_idx[fld_idx], loc_idx]]
basis = training_array[snp_idx:snp_idx+1, :, :]

# Determine number of pasis to be computed and enter GEIM main loop:
N_basis = 28
for ii in range(1, N_basis):

    #  Compute combination coefficients for the current basis and training matrix:
    training_measurements = np.array([training_array[:, list_magic_fields[rr], list_magic_points[rr]] / list_scaling_factors[rr] for rr in range(ii)])
    basis_measurements = np.array([[basis[rr, list_magic_fields[kk], list_magic_points[kk]] / list_scaling_factors[kk] for rr in range(ii)] for kk in range(ii)])
    linear_combination_coefficients = np.linalg.solve(basis_measurements, training_measurements)

    # Construct the interpolation residuals:
    residual = training_array - np.einsum('ir,ijk->rjk', linear_combination_coefficients, basis)

    # Identify maximum of the absolute value of the observable residuals:
    snp_idx, fld_idx, loc_idx = np.unravel_index(np.argmax(np.abs(residual[:, obs_idx, :])), residual[:, obs_idx, :].shape)

    # Append new sensor, scaling factor and basis:
    list_magic_fields.append(obs_idx[fld_idx])
    list_magic_points.append(loc_idx)
    list_scaling_factors.append(residual[snp_idx, obs_idx[fld_idx], loc_idx])
    basis = np.concatenate((basis, residual[snp_idx:snp_idx+1, :, :]), axis=0)

