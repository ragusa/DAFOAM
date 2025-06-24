from linAlg4Foam import linAlg4Foam

# Path to virtual OpenFoam directory
virtual_OF_dir = "OpenFoamTestCase/GeN-Foam/virtual_OF"

#To get value of a scalar/vector field at a specific point inside the domain we need to pass the points to the functions. This is an example how the points can be formed. 
# the first, second, third elements of a tuple respectively notifies x, y, and z coordinates of a point 
points = [
    (0, 0.5, -0.6),
    (0, 0.5,  0.0),
    (0, 0.5,  0.6)
]

#We specify the fields for which we want to do operations. Notice that we have combined  the region with the actual field name to get the constructed field name.
fields = ['fluidRegion/T', 'fluidRegion/p_rgh', 'neutroRegion/flux0']

#this field list is for linAlg4Foam.linearCombination
fields_combination = ['fluidRegion/T']
#The portion of string before "/" is the case name. The portion of string after "/" is time name. List of lists of snapshots is for linear combinations (linAlg4Foam.linearCombination). For each list we have to have a corresponding
# list of coefficients and a a output directory.
list_of_lists_of_snapshots = [
    ['1/1', '1/2', '1/3'],
    ['1/4', '1/5']
]

# This coefficients are random. We have put it here to show how the list of lists of coefficients for linearn combination
# can be passed to the linAlg4Foam.linearCombination function.
list_of_lists_of_coefficients = [[0.5, -0.5, 0.5], [10.0, -1.0e-4]]
output_dirs = ['temp_outputs/0', 'temp_outputs/1']

#Snapshot list for different operations
snapshots_list =[
'1/1', '1/2', '1/3', '1/4', '1/5'
]

#This variable is defined for the linAlg4Foam.physicalSensors function. We define two points and a radius for a physical sensor.
sensors = [
    {"point1": (0.0, 0.0, -0.1), "point2": (0.0, 1.9, -0.1), "radius": 0.025},
    {"point1": (0.0, 0.1,  0.1), "point2": (0.0, 2.0,  0.1), "radius": 0.025}
]

## Evaluating fields at the points 
print("\Evaluating fields at the points...")
results = linAlg4Foam.readFromPoints(virtual_OF_dir, snapshots_list, fields, points)
print("Results from the evaluation of linAlg4Foam.readFromPoints.")
for item in results:
    print(item)

## Evaluating fields at the physical sensors
print("\nEvaluating at the physical sensors...")
results = linAlg4Foam.physicalSensors(virtual_OF_dir, snapshots_list, fields, sensors)
print("Results from the evaluation of  linAlg4Foam.physicalSensors")
for item in results:
    print(item)

## Returning minimal and maximal values of a field
print("\nSearching field min and max...")
minima, maxima = linAlg4Foam.fieldMinMax(virtual_OF_dir, snapshots_list, fields)
print("Results from the evaluation of  linAlg4Foam.fieldMinMax")

print("minima:\n")
for item in minima:
    print(item)

print("maxima:\n")
for item in maxima:
    print(item)

## Returning minimal and maximal values of internal field
# internal field means fields inside the domain (excluding the boundary)
# linAlg4Foam.internalFieldMinMax determines field min-max inside the domain 
print("\nSearching internal field min and max...")
minima, maxima = linAlg4Foam.internalFieldMinMax(virtual_OF_dir, snapshots_list, fields)

print("Results from the evaluation of  linAlg4Foam.internalFieldMinMax")
print("minima:\n")
for item in minima:
    print(item)

print("maxima:\n")
for item in maxima:
    print(item)


## Returning L2norm of a field
print("\nCalculating L2norm...")
L2norm = linAlg4Foam.L2norm(virtual_OF_dir, snapshots_list, fields)
print("Results from linAlg4Foam.L2norm")
for item in L2norm:
    print(item)
 
## Linear combination of fields. For each list of fields we get a single linear combination. 
print("\nCalculating linear combination of fields...")
linAlg4Foam.linearCombination(virtual_OF_dir, list_of_lists_of_snapshots, fields_combination, list_of_lists_of_coefficients, output_dirs)

