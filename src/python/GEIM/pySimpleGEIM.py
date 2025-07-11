## MOST OF THE DEPENDENCIES ARE MISSING FOR NOW
import numpy as np
import ...

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
