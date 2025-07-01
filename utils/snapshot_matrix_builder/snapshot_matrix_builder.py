import numpy as np
import fluidfoam 
import os
import copy

#to get 'regionName' and 'fieldName' from a constructed field name 'regionName/fieldName'
def split_on_slash(input_string):
        if '/' in input_string:
            before, after = input_string.split('/', 1)
        else:
            before = ''
            after = input_string
        return before, after

#This class takes an instance of the snapshot_manager class object (a module/class defined in utils/snapshot_manager) along with
# all the field paths of concern (be that observable or non-observable). It should be noted that the matrices are build at the initialization. Moreover, it creates two sets of matrices 
# one for training and another for testing 
class Snapshot_matrix_builder:
    def __init__(self, snapshot_manager_object, list_fields_paths):
        self.sm_obj = snapshot_manager_object
        self.regions = self.sm_obj.regions
        self.list_chosen_snapshot_paths = self.sm_obj.list_chosen_snapshot_paths
        self.list_unchosen_snapshot_paths = list(set(self.sm_obj.list_snapshot_paths)- set(self.sm_obj.list_chosen_snapshot_paths))
        self.list_fields_paths = list_fields_paths
        self.symlinked_cases_directory = self.sm_obj.symlinked_cases_directory
        self.exemplary_case_directory = os.path.join(self.symlinked_cases_directory, self.sm_obj.list_cases[0])

        self.Nsnapshots_training = len(self.list_chosen_snapshot_paths)
        self.Nsnapshots_testing = len(self.list_unchosen_snapshot_paths)

        self._store_mesh_data()
        self._determine_tot_cells_per_snap()

        #build training matrices
        self.snapshot_matrix_2D_training, self.snapshot_matrix_3D_training = self._build_snapshot_matrices(list_snap_paths=self.list_chosen_snapshot_paths)
        #build testing matrices
        self.snapshot_matrix_2D_testing, self.snapshot_matrix_3D_testing = self._build_snapshot_matrices(list_snap_paths=self.list_unchosen_snapshot_paths)
    

    #This method extracts the necessary mesh data and save it in a dictionary where the keys represent regions.
    def _store_mesh_data(self):
        self.dict_mesh_by_region = {}
        self.dict_centroids_and_volumes_by_region = {}
        self.dict_Ncells_by_region = {}
        self.tot_cells_per_snap = 0
        for region in self.regions if len(self.regions) != 0 else ['']:
            self.dict_mesh_by_region[region] = fluidfoam.readof.readmesh(path= self.exemplary_case_directory,  region=region if region != '' else None )
            # you can access 
            # X = self.self.dict_mesh_by_region[region][0]
            # Y = self.self.dict_mesh_by_region[region][1]
            # Z = self.self.dict_mesh_by_region[region][2]
            self.dict_centroids_and_volumes_by_region[region] =  fluidfoam.readof.getVolumes(path=self.exemplary_case_directory,  region=region if region != '' else None )
            Ncells = self.dict_centroids_and_volumes_by_region[region][0].shape[0]
            self.dict_Ncells_by_region[region] = Ncells 
            # you can access 
            # centroids = self.dict_centroids_and_volumes_by_region[region][0]
            # volumes = self.dict_centroids_and_volumes_by_region[region][1]
    
    # For the initialization of the matrices, we need to determine the cell count for a snap. That is because, each field in the provided list_field_paths may have different mesh. 
    # Moreover, we need to store the start_index and the end_index of a field from how the fields are assigned in the matrix. This index pair for each field serves as the decryption key for this matrix encryption.

    def _determine_tot_cells_per_snap(self):
        self.tot_cells_per_snap = 0
        self.list_field_to_Ncells = []
        self.list_field_to_range_cells =[]
        for index_field, field in enumerate(self.list_fields_paths):
            region, field_name =  split_on_slash(field)
            self.list_field_to_Ncells.append(self.dict_Ncells_by_region[region])
            index_start = self.tot_cells_per_snap
            self.tot_cells_per_snap += self.list_field_to_Ncells[index_field]
            index_end = self.tot_cells_per_snap - 1
            self.list_field_to_range_cells.append((index_start, index_end))
            
    #This method assembles the matrices.
    def _build_snapshot_matrices(self, list_snap_paths):
        snapshot_matrix_2D = np.zeros((self.tot_cells_per_snap, self.Nsnapshots_training))
        snapshot_matrix_3D = []
        for index_snap, snap in enumerate(list_snap_paths):
            case_name, time_name = split_on_slash(snap)
            case_directory = os.path.join(self.symlinked_cases_directory, case_name)
            snapshot_matrix_3D.append([])  
            for index_field, field in enumerate(self.list_fields_paths):
                region, field_name = split_on_slash(field)
                field_values = fluidfoam.readof.readscalar(path=case_directory, time_name=time_name, name=field_name, region=region)
                index_start, index_end = self.list_field_to_range_cells[index_field]
                snapshot_matrix_2D[index_start:index_end + 1, index_snap] = copy.deepcopy(field_values)
                snapshot_matrix_3D[index_snap].append(copy.deepcopy(field_values))
        return copy.deepcopy(snapshot_matrix_2D), copy.deepcopy(snapshot_matrix_3D)
              

         
        
    