from linAlg4Foam import linAlg4Foam

# Path to virtual OpenFoam directory
virtual_OF_dir = "OpenFoamTestCase/GeN-Foam/virtual_OF"

points = [
    (0, 0.5, -0.6),
    (0, 0.5,  0.0),
    (0, 0.5,  0.6)
]

fields = ['fluidRegion/T', 'fluidRegion/p_rgh', 'neutroRegion/flux0']

fields_combination = ['fluidRegion/T']
list_of_lists_of_snapshots = [
    ['1/1', '1/2', '1/3'],
    ['1/4', '1/5']
]
list_of_lists_of_coefficients = [[0.5, -0.5, 0.5], [10.0, -1.0e-4]]
output_dirs = ['temp_outputs/0', 'temp_outputs/1']

snapshots_list =[
'1/1', '1/2', '1/3', '1/4', '1/5'
]

sensors = [
    {"point1": (0.0, 0.0, -0.1), "point2": (0.0, 1.9, -0.1), "radius": 0.025},
    {"point1": (0.0, 0.1,  0.1), "point2": (0.0, 2.0,  0.1), "radius": 0.025}
]

## Sampling from points
print("\nSampling from points...")
results = linAlg4Foam.readFromPoints(virtual_OF_dir, snapshots_list, fields, points)
for item in results:
    print(item)

## Physical sensor
print("\nSampling from physical sensors...")
results = linAlg4Foam.physicalSensors(virtual_OF_dir, snapshots_list, fields, sensors)
for item in results:
    print(item)

## Returning minimal and maximal values of a field
print("\nSearching field min and max...")
minima, maxima = linAlg4Foam.fieldMinMax(virtual_OF_dir, snapshots_list, fields)
for item in minima:
    print(item)
for item in maxima:
    print(item)

## Returning minimal and maximal values of internal field
print("\nSearching internal field min and max...")
minima, maxima = linAlg4Foam.internalFieldMinMax(virtual_OF_dir, snapshots_list, fields)
for item in minima:
    print(item)
for item in maxima:
    print(item)

## Returning L2norm of a field
print("\nCalculating L2norm...")
L2norm = linAlg4Foam.L2norm(virtual_OF_dir, snapshots_list, fields)
for item in L2norm:
    print(item)
 
## Linear combination of fields
print("\nCalculating linear combination of fields...")
linAlg4Foam.linearCombination(virtual_OF_dir, list_of_lists_of_snapshots, fields_combination, list_of_lists_of_coefficients, output_dirs)

