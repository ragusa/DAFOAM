## MOST OF THE DEPENDENCIES ARE MISSING FOR NOW
import numpy as np
import ...
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

    def __init__(self, snaps_obj, rank, norm_type="L2"):
        self.snaps_obj = snaps_obj
        snaps_array = np.asarray(self.snaps_obj.snapshot_matrix_2D).copy()
    
        self.__snaps = snaps_array
        self.__rank = rank
        self.list_fields = self.snaps_obj.list_fields_paths
        self.list_field_to_range_cells = self.snaps_obj.list_field_to_range_cells
        self.Nsnaps = snaps_obj.Nsnapshots
        self.Nfields = len(self.list_fields)
        self.dict_centroids_and_volumes_by_region = self.snaps_obj.dict_centroids_and_volumes_by_region
        self.norm_type = norm_type
        #generate norms
        self.__generate_norm_snaps()


        #self.__array_indexes_maximizing_position = np.zeros((self.__rank), dtype=int)
        #self.indexes_position_sensors = np.zeros((self.__rank), dtype=int)
        #self.matrix_holding_bases = np.zeros((self.__Nx_stacked, self.__rank))

        self.A = np.zeros((self.__rank, self.__rank))

        self.index_field_basis = np.zeros(self.__rank, dtype=int)
        
        #this is the primary method that does all the main calculations
        #self.__find_bases()

        #except TypeError as e:
            #print("Type error:", e)
        #except ValueError as e:
            #print("Value error:", e)
            
    
    
    @define_norm_func 
    def __determine_norm_field(self, field_values, region):
        pass
    
    def __generate_norm_snaps(self):
        self.norm_snaps = np.zeros((self.Nfields, self.Nsnaps))
        for ii, field in enumerate(self.list_fields):
            region, field_name = split_on_slash(field)
            print(region, field_name)
            (index_start, index_end) = self.list_field_to_range_cells[ii]

            for jj in range(self.Nsnaps):
                field_values = self.__snaps[index_start : index_end + 1, jj]
                self.norm_snaps[ii, jj] = self.__determine_norm_field(field_values=field_values, region=region)

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
