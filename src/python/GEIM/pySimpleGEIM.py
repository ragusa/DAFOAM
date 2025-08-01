import copy
import numpy as np

def split_on_slash(input_string):
    """Split a string on the first '/' character.
    
    Returns:
        tuple: (before_slash, after_slash) where before_slash is empty if no '/' found
    """
    if '/' in input_string:
        before, after = input_string.split('/', 1)
    else:
        before = ''
        after = input_string
    return before, after


def determine_norm_func(norm_type):
    """Return a norm function based on the specified norm type.
    
    Args:
        norm_type (str): Type of norm ("L2" or "Linf")
        
    Returns:
        function: Norm calculation function
    """
    if norm_type == "L2":
        def definition(instance, field_values, region):
            volumes = instance.dict_centroids_and_volumes_by_region[region][1]
            return np.sqrt(np.sum(field_values ** 2 * volumes))
    elif norm_type == "Linf":
        def definition(instance, field_values, region):
            return np.max(np.abs(field_values))
    else:
        raise ValueError(f"Unsupported norm type: {norm_type}")
    return definition
            
       
class pyGEIM_offline:
    """Offline phase of the Generalized Empirical Interpolation Method (GEIM).
    
    Determine sensor locations and Construct basis functions from training snapshots.
    """

    def __init__(self, snaps_obj, rank, list_observable_fields, norm_type="L2"):
        """Initialize the offline GEIM algorithm.
        
        Args:
            snaps_obj: Snapshot matrix builder object containing training data
            rank (int): Number of basis functions to construct
            list_observable_fields (list): List of observable field names
            norm_type (str): Type of norm to use ("L2" or "Linf")
        """
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
        #define the norm detrmining method based on the norm type
        self.__determine_norm_field = determine_norm_func(norm_type=self.norm_type)
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
        """Execute the offline GEIM algorithm to construct basis functions and sensor locations."""
        for count_basis in range(self.rank):
            self.__residual_snaps = self.__snaps - self.__J
            self.__generate_norm_snaps(residual=False if count_basis==0 else True)
            self.__keep_the_book(count_basis=count_basis, norm_resid_snaps=self.norm_snaps if count_basis==0 else self.normalized_norm_residual_snaps)
            self.__build_A(count_basis=count_basis)
            self.__reconstruct_training_space(count_basis=count_basis)

    def __generate_norm_snaps(self, residual=True):
        """Compute norms of snapshot fields or residuals."""
        for ii, field in enumerate(self.list_observable_fields):
            region, field_name = split_on_slash(field)
            index_field = self.list_indices_observable_fields[ii]
            (index_start, index_end) = self.list_field_to_range_cells[index_field]
            for jj in range(self.Nsnaps):
                if residual is False:
                    field_values = self.__snaps[index_start : index_end + 1, jj]
                    self.norm_snaps[ii, jj] = self.__determine_norm_field(self, field_values=field_values, region=region)
                else:
                    field_values = self.__residual_snaps[index_start : index_end + 1, jj]
                    self.normalized_norm_residual_snaps[ii, jj] = self.__determine_norm_field(self, field_values=field_values, region=region) / self.norm_snaps[ii, jj]

    def __keep_the_book(self, count_basis, norm_resid_snaps):
        """Store basis function and sensor information for current iteration."""
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
        """Build the System matrix A."""
        for i in range(count_basis + 1):
                for j in range(count_basis + 1):
                    if i == count_basis or j == count_basis:
                        self.A[i, j] = self.matrix_holding_bases[self.array_indices_maximizing_position[i], j] / self.scaling_factor[i]

    def __coord_maximizing_snap_finder(self, norms):
        """Find the field and snapshot indices that maximize the norm."""
        index_obs_field, index_snap = np.unravel_index(np.argmax(norms), norms.shape)
        index_field = self.list_indices_observable_fields[index_obs_field]
        return (index_field, index_snap)
  
    def __reconstruct_training_space(self, count_basis):
        """Reconstruct the training snapshots using current basis functions."""
        mat_A = self.A[:count_basis + 1, :count_basis + 1]
        for index_snap in range(self.Nsnaps):
            b = np.asarray(self.__snaps[self.array_indices_maximizing_position[:count_basis + 1], index_snap]) / self.scaling_factor[:count_basis + 1]
            d_i = np.linalg.solve(mat_A, b)
            self.__J[:, index_snap] = self.matrix_holding_bases[:, :count_basis + 1] @ d_i
    
class pyGEIM_online:
    """Online phase of GEIM for reconstructing test snapshots using precomputed basis."""
    
    def __init__(self, offline_object, snaps_object, rank_upto):
        """Initialize the online GEIM reconstruction.
        
        Args:
            offline_object: Completed offline GEIM object
            snaps_object: Snapshot Matrix Builder object containing test data
            rank_upto (int): Number of basis functions to use for reconstruction
        """
        self.offline_object = offline_object
        self.A = self.offline_object.A[:rank_upto, :rank_upto]
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
        """Reconstruct all test snapshots using the precomputed GEIM basis."""
        for index_snap in range(self.Nsnaps):
            b = np.asarray(self.snapshot_testing[self.array_indices_maximizing_position[:self.rank_upto], index_snap]) / self.scaling_factor[:self.rank_upto]
            d_i = np.linalg.solve(self.A, b)
            self.J[:, index_snap] = self.matrix_holding_bases[:, :self.rank_upto] @ d_i