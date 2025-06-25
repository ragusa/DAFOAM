"""
===============================================================================
    Script Name:    linAlg4Foam.py
    Description:    This script contains a set of utilites which can be used 
                    in python and perform field operations using OpenFOAM 
                    utilities. It actually acts as an interface which performs
                    field operation on existing OpenFOAM results using OpenFOAM
                    function objects.

    Author:         Rok Krpan (rok.krpan@tamu.edu)
    Date:           2025-05-23
    Version:        1.2
    Usage:          To properly run this script, one should have OpenFOAM
                    installed on the system and OpenFOAM evironment variables
                    should be properly sourced inside '~/.bashrc'. The functions
                    defined in this script should be imported as:
                        'from linAlg4Foam import linAlg4Foam'
                    
                    'virtual_OF_dir' should be a directiory with "constant" and "system"
                    folders (with all included files). Namely, the function objects
                    are executed in this directory and require the basi OpenFOAM
                    case infomation (polyMesh, fvSystem, fvSolution).
    
===============================================================================
"""

from .basicFunctions import *

class linAlg4Foam:

###############################################################################
###
###     Basic utilities
###
###############################################################################

   
    @staticmethod    
    def fieldMinMax(virtual_OF_dir, snapshots_list, fields):
        """
        Returns the minimal and maximal values of the fields along with the location.

        Returns:
            - output file 'fieldMinMax.log' in virtual_OF_dir/logs/
            - a list of dictionaries
        """

        function = 'fieldMinMax'
        ExecuteFunctionObject(virtual_OF_dir=virtual_OF_dir, function=function, snapshots_list=snapshots_list, fields=fields)

        # Extract data from log file    
        log_path = virtual_OF_dir + f"/logs/{function}.log"
        minima = []
        maxima = []
        minimum_pattern = r'Minimum: "([^"]+)", location = \(([^)]+)\), ([\w/\.]+) = ([\d.+-eE]+)'
        maximum_pattern = r'Maximum: "([^"]+)", location = \(([^)]+)\), ([\w/\.]+) = ([\d.+-eE]+)'
    
        with open(log_path, "r") as file:
            for line in file:
                minimum_match = re.search(minimum_pattern, line)
                if minimum_match:
                    min_snapshotID = minimum_match.group(1)
                    min_location = f"({minimum_match.group(2)})"
                    min_field = minimum_match.group(3)
                    min_value = float(minimum_match.group(4))
        
                    minima.append({
                        "snapshotID": min_snapshotID,
                        "field": min_field,
                        "position": min_location,
                        "value": min_value
                    })
    
                maximum_match = re.search(maximum_pattern, line)
                if maximum_match:
                    max_snapshotID = maximum_match.group(1)
                    max_location = f"({maximum_match.group(2)})"
                    max_field = maximum_match.group(3)
                    max_value = float(maximum_match.group(4))
        
                    maxima.append({
                        "snapshotID": max_snapshotID,
                        "field": max_field,
                        "position": max_location,
                        "value": max_value
                    })
    
        return minima,maxima


    @staticmethod
    def internalFieldMinMax(virtual_OF_dir, snapshots_list, fields):
        """
        Returns the minimal and maximal values of the internal fields along
        with the location.

        Returns:
            - output file 'internalFieldMinMax.log' in virtual_OF_dir/logs/
            - a list of dictionaries
        """
        
        function = 'internalFieldMinMax'
        ExecuteFunctionObject(virtual_OF_dir=virtual_OF_dir, function=function, snapshots_list=snapshots_list, fields=fields)
    
        # Extract data from log file
        log_path = os.path.join(virtual_OF_dir, 'logs', f"{function}.log")
        # double dictionary of list initialization
        minima = {}
        maxima = {}
        for snap in snapshots_list:
            minima[snap] = {}
            maxima[snap] = {}
            for field in fields:
                minima[snap][field] = []
                maxima[snap][field] = []


        minimum_pattern = r'Minimum: "([^"]+)", location = \(([^)]+)\), ([\w/\.]+) = ([\d.+-eE]+)'
        maximum_pattern = r'Maximum: "([^"]+)", location = \(([^)]+)\), ([\w/\.]+) = ([\d.+-eE]+)'

        with open(log_path, "r") as file:
            for line in file:
                minimum_match = re.search(minimum_pattern, line)
                if minimum_match:
                    min_snapshotID = minimum_match.group(1)
                    min_location = f"({minimum_match.group(2)})"
                    min_field = minimum_match.group(3)
                    min_value = float(minimum_match.group(4))
                    field_name = min_field.removeprefix('../')
        
                    minima[min_snapshotID][field_name].extend([min_location, min_value])
    
                maximum_match = re.search(maximum_pattern, line)
                if maximum_match:
                    max_snapshotID = maximum_match.group(1)
                    max_location = f"({maximum_match.group(2)})"
                    max_field = maximum_match.group(3)
                    max_value = float(maximum_match.group(4))
                    field_name = max_field.removeprefix('../')

                    maxima[max_snapshotID][field_name].extend([max_location, max_value])
                    
        return minima,maxima
    
    @staticmethod
    def L2norm(virtual_OF_dir, snapshots_list, fields):
        """
        Returns the L2norm of the field.

        Returns:
            - output file 'L2norm.log' in virtual_OF_dir/logs/
            - a list of dictionaries with L2norm values
        """
        
        function = 'L2norm'
        ExecuteFunctionObject(virtual_OF_dir=virtual_OF_dir, function=function, snapshots_list=snapshots_list, fields=fields)
    
        # Extract data from log file
        log_path = os.path.join(virtual_OF_dir, 'logs', f"{function}.log")

          # double dictionary of list initialization
        L2norm = {}
        for snap in snapshots_list:
            L2norm[snap] = {}
            for field in fields:
                L2norm[snap][field] = []
        pattern = r'L2norm: "([^"]+)", (\.\./)?([\w/]+) = ([\d.eE+-]+)'
        
        with open(log_path, "r") as file:
            for line in file:
                match = re.search(pattern, line)
                if match:
                    snapshotID = match.group(1)
                    field = match.group(3)
                    value = float(match.group(4))
                    L2norm[snapshotID][field].extend([value])
    
        return L2norm

    @staticmethod
    def readFromPoints(virtual_OF_dir, snapshots_list, fields, points):
        """
        This function reads field values from the set of points, which are specified as:
        points = [
            (0.1, 0.5, 0.05),
            (0.2, 0.5, 0.05),
            (0.4, 0.5, 0.05)
        ]

        Returns:
            - output file 'sample.log' in virtual_OF_dir/logs/
            - a list of dictionaries
        """
        
        function = 'sample'
        ExecuteFunctionObject(virtual_OF_dir=virtual_OF_dir, function=function, snapshots_list=snapshots_list, fields=fields, points=points)
    
        # Extract data from log file
        log_path = virtual_OF_dir + f"/logs/{function}.log"

        # double dictionary of list initialization
        dirac_delta_evaluation = {}
        for snap in snapshots_list:
            dirac_delta_evaluation[snap] = {}
            for field in fields:
                dirac_delta_evaluation[snap][field] = []

        results = []
        pattern = r'"([^"]+)", point = \(([^)]+)\), ([\w/\.]+) = ([\d.+-eE]+)'
        with open(log_path, "r") as file:
            for line in file:
                match = re.search(pattern, line)
                if match:
                    snapshotID = match.group(1)
                    point = f"({match.group(2)})"
                    field = match.group(3).lstrip("../")
                    value = float(match.group(4))
                    dirac_delta_evaluation[snapshotID][field].extend([point, value])
        
        return dirac_delta_evaluation



    @staticmethod    
    def physicalSensors(virtual_OF_dir, snapshots_list, fields, sensors):
        """
        Extracts minimal, maximal and average value from a 3D cylindrical
        part of the domain. This functionality firstly generates cell zones
        using 'topoSet' and then reads the fields from that specific zones. 
    
        The sensors are listed as a list of dictionaries. Each sensor is 
        defined with two points (on each side of the axis) and a radius: 
        
        sensors = [
            {"point1": (0.0, 0.5, 0.0005), "point2": (0.1, 0.5, 0.0005), "radius": 0.1},
            {"point1": (0.2, 0.5, 0.0005), "point2": (0.3, 0.5, 0.0005), "radius": 0.1}
        ]

        Returns:
            - output file 'physicalSensors.log' in virtual_OF_dir/logs/
            - a list of dictionaries
        """

        function = 'sensors'
        ExecuteFunctionObject(virtual_OF_dir=virtual_OF_dir, function=function, snapshots_list=snapshots_list, fields=fields, sensors=sensors)
    
        # Extract the data from log
        log_path = virtual_OF_dir + f"/logs/{function}.log"
        results = []
        pattern = r'"([^"]+)",\s*(sensor\d+),\s*([\w/\.]+),\s*min = ([\d.+-eE]+),\s*max = ([\d.+-eE]+),\s*average = ([\d.+-eE]+)'

        with open(log_path, "r") as file:
            for line in file:
                match = re.search(pattern, line)
                if match:
                    snapshotID = match.group(1)
                    sensorID = match.group(2)
                    field = match.group(3).lstrip("../")
                    min_val = float(match.group(4))
                    max_val = float(match.group(5))
                    avg_val = float(match.group(6))
        
                    results.append({
                        "snapshotID": snapshotID,
                        "sensor": sensorID,
                        "field": field,
                        "min": min_val,
                        "max": max_val,
                        "average": avg_val
                    })
        
        return results


###############################################################################
###
###     Linear field algebra
###
###############################################################################

    @staticmethod    
    def linearCombination(virtual_OF_dir, list_of_lists_of_snapshots, fields, list_of_lists_of_coefficients, output_dirs):
        """
        Calculates a linear combination of fields:        
            $$
            \sum_{i = 1}^N c_i \psi_i
            $$
        where $c_i$ are the coefficients and $\psi_i$ are the fields.
                
        The inputs are:
        - list of field names (fields),
        - list of lists of snapshot paths (snapshots_list),
        - list of lists of coefficients (coefficients),
        - list of output directories (output_dirs).

        The output directories should be specified in the same order as the
        snapshots, since the function will create a new directory for each 
        output directory and write new fields there.
    
        Returns:
            - output file 'linearCombination.log' in virtual_OF_dir/logs/
            - new fields in output_dirs
        """

        # Check that both lists are lists of lists
        if not (isinstance(list_of_lists_of_snapshots, list) and all(isinstance(elem, list) for elem in list_of_lists_of_snapshots)):
            print("Error: 'snapshots_list' it is not a list of lists.")
            exit(1)
        if not (isinstance(list_of_lists_of_coefficients, list) and all(isinstance(elem, list) for elem in list_of_lists_of_coefficients)):
            print("Error: 'coefficients' it is not a list of lists.")
            exit(1)

        # Check that the lengths of the lists of lists are the same
        assert len(list_of_lists_of_snapshots) == len(list_of_lists_of_coefficients) and all(len(s) == len(c) for s, c in zip(list_of_lists_of_snapshots, list_of_lists_of_coefficients)), "Lists are inconsistent"
        assert len(list_of_lists_of_snapshots) == len(output_dirs), "Number of output directories must match the number of snapshot lists!"

        function = 'linearCombination'
        ExecuteFunctionObject(virtual_OF_dir=virtual_OF_dir, function=function, snapshots_list=list_of_lists_of_snapshots, fields=fields, list_of_lists_of_coefficients=list_of_lists_of_coefficients, output_dirs=output_dirs)


###############################################################################

if __name__ == "__main__":
    print("Just standing here, doing nothing...")
