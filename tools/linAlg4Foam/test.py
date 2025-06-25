from linAlg4Foam import linAlg4Foam

# Path to virtual OpenFoam directory
virtual_OF_dir = "OpenFoamTestCase/laplacianFoam/virtual_OF"

#To get value of a scalar/vector field at a specific point inside the domain we need to pass the points to the functions. This is an example how the points can be formed. 
# the first, second, third elements of a tuple respectively notifies x, y, and z coordinates of a point 
points = [
    (0.1, 0.5, 0.05),
    (0.2, 0.5, 0.05),
    (0.4, 0.5, 0.05)
]

#We specify the fields for which we want to do operations 
fields = ['T', 'DT']

#The portion of string before "/" is the case name. The portion of string after "/" is time name. List of lists of snapshots is for linear combinations (linAlg4Foam.linearCombination). For each list we have to have a corresponding
# list of coefficients and a a output directory.
list_of_lists_of_snapshots = [
    ['4/100', '5/100', '6/100'],
    ['1/200', '2/200', '3/200']
]

# This coefficients are random. We have put it here to show how the list of lists of coefficients for linearn combination
# can be passed to the linAlg4Foam.linearCombination function.
list_of_lists_of_coefficients = [[0.5, -0.5, 0.5], [10.0, -1.0e-4, 0.1]]
output_dirs = ['temp_outputs/0', 'temp_outputs/1']

#Snapshot list for different operations
snapshots_list =[
'3/5', '3/10', '3/15', '3/20', '3/25', '3/30', '3/35', '3/40', '3/45', '3/50'
]

#This variable is defined for the linAlg4Foam.physicalSensors function. We define two points and a radius for a physical sensor.
sensors = [
    {"point1": (0.0, 0.5, 0.0005), "point2": (0.1, 0.5, 0.0005), "radius": 0.1},
    {"point1": (0.2, 0.5, 0.0005), "point2": (0.3, 0.5, 0.0005), "radius": 0.1}
]

## Evaluating fields at the points 
print("\Evaluating fields at the points...")
results = linAlg4Foam.readFromPoints(virtual_OF_dir, snapshots_list, fields, points)
#this shows how the results can be shown.
print("Results from the evaluation of linAlg4Foam.readFromPoints")
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
print("minima:\n")
for item in minima:
    print(item)

print("maxima:\n")
for item in maxima:
    print(item)

## Linear combination of fields. For each list of fields we get a single linear combination. 
print("\nCalculating linear combination of fields...")
linAlg4Foam.linearCombination(virtual_OF_dir, list_of_lists_of_snapshots, fields, list_of_lists_of_coefficients, output_dirs)


