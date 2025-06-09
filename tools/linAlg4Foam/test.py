from linAlg4Foam import linAlg4Foam

# Path to virtual OpenFoam directory
virtual_OF_dir = "OpenFoamTestCase/laplacianFoam/virtual_OF"

points = [
    (0.1, 0.5, 0.05),
    (0.2, 0.5, 0.05),
    (0.4, 0.5, 0.05)
]

fields = ['T', 'DT']

list_of_lists_of_snapshots = [
    ['4/100', '5/100', '6/100'],
    ['1/200', '2/200', '3/200']
]
list_of_lists_of_coefficients = [[0.5, -0.5, 0.5], [10.0, -1.0e-4, 0.1]]
output_dirs = ['temp_outputs/0', 'temp_outputs/1']

snapshots_list =[
'3/5', '3/10', '3/15', '3/20', '3/25', '3/30', '3/35', '3/40', '3/45', '3/50'
]

sensors = [
    {"point1": (0.0, 0.5, 0.0005), "point2": (0.1, 0.5, 0.0005), "radius": 0.1},
    {"point1": (0.2, 0.5, 0.0005), "point2": (0.3, 0.5, 0.0005), "radius": 0.1}
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

## Linear combination of fields
print("\nCalculating linear combination of fields...")
linAlg4Foam.linearCombination(virtual_OF_dir, list_of_lists_of_snapshots, fields, list_of_lists_of_coefficients, output_dirs)


