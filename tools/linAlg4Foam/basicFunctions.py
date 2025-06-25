"""
===============================================================================
    Script Name:       basicFunctions.py
    Description:       This script contains basic file operators which are
                       used in 'linAlg4Foam.py'

    Author:            Rok Krpan (rok.krpan@tamu.edu)
    Date:              2025-05-23
    Version:           1.2
    Usage:             To properly run this script, one should have OpenFOAM
                       intalled on the system and OpenFOAM evironment variables
                       should be properly sourced inside '~/.bashrc'
                       The functions definitions from this script should
                       be imported in 'linAlg4Foam.py' as:
                           'from basicFunctions import *'

===============================================================================
"""

import gzip
import os
import pexpect
import re
import shutil
import subprocess

from attr import field
from itertools import combinations

# Location of OpenFoam function objects
function_objects_dir = os.path.join(os.path.dirname(__file__), 'OpenFoamFunctionObjects')

# Relative path from OpenFoam virtual folder to the snapshots location 
relative_path = "../symlinked_cases/"

class ExecuteFunctionObject:
    def __init__(self, virtual_OF_dir, function, snapshots_list, fields, points = None, list_of_lists_of_coefficients = None, output_dirs = None, sensors = None):
        self.virtual_OF_dir = virtual_OF_dir
        self.function = function
        self.snapshots_list = snapshots_list
        self.fields = fields
        self.points = points
        self.list_of_lists_of_coefficients = list_of_lists_of_coefficients
        self.output_dirs = output_dirs
        self.sensors = sensors

        self.regions = self._check_regions_()
        self.initialize()
        if self.function == "sensors":
            self.setSensors()
        self.execute()

    @staticmethod
    def __list_into_string__(value):
        return str(value if isinstance(value, list) else [value])

    @staticmethod
    def __open_mesh_file__(mesh_file_path):
        gz_path = mesh_file_path + ".gz"
        if os.path.isfile(gz_path):
            return gzip.open(gz_path, 'rt')
        elif os.path.isfile(mesh_file_path):
            return open(mesh_file_path, 'r')
        else:
            raise FileNotFoundError(f"Neither {mesh_file_path} nor {gz_path} found.")


    # Check the existance of the regions in OpenFOAM case and compare their meshes
    def _check_regions_(self):

        if isinstance(self.snapshots_list[0], list):
            snapshots_list = [sublist[0] for sublist in self.snapshots_list if sublist]
        else:
            snapshots_list = self.snapshots_list


        snapshot_path = os.path.join(self.virtual_OF_dir, relative_path, snapshots_list[0])
        with os.scandir(snapshot_path) as entries:
            regions_check = any(entry.is_dir() and "Region" in entry.name for entry in entries)

        # Extract unique regions from fields list
        regions = {field.split('/')[0] for field in self.fields if '/' in field}
        regions = list(regions)


        # Check if both cases or regions use the same mesh
        if regions_check and len(regions) > 1:
            # print(f"Several regions exist: {regions}")
            constant_dir = os.path.abspath(os.path.join(snapshot_path, "../constant"))
            mesh_files = ['points','faces']

            for region1, region2 in combinations(regions, 2):
                for mesh_file in mesh_files:
                    mesh_file1 = os.path.join(constant_dir, region1, "polyMesh", mesh_file)
                    mesh_file2 = os.path.join(constant_dir, region2, "polyMesh", mesh_file)
                    # print(f"Comparing {mesh_file1} vs {mesh_file2}")

                    with self.__open_mesh_file__(mesh_file1) as f1, self.__open_mesh_file__(mesh_file2) as f2:
                        for i in range(50):  # First 50 lines
                            line1 = f1.readline()
                            line2 = f2.readline()

                            if not line1 and not line2:
                                break
                            if not line1 or not line2:
                                raise ValueError(f"{mesh_file}: {region1} and {region2} differ in file length.")
                            if line1.strip() != line2.strip():
                                raise ValueError(f"{mesh_file}: {region1} and {region2} differ at line {i+1}")

        return regions

    def initialize(self):
        os.makedirs(self.virtual_OF_dir + '/system/FOs', exist_ok=True)
        os.makedirs(self.virtual_OF_dir + '/logs', exist_ok=True)

        # Copy 'controlDict' from global FO repo
        shutil.copy2(function_objects_dir + '/controlDict', self.virtual_OF_dir + '/system/controlDict')

        # Modify 'controlDict' to use the specific function object
        command = ["foamDictionary", self.virtual_OF_dir + "/system/controlDict", "-disableFunctionEntries", "-entry", "functions", "-set", "{}" ]
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        command = ["foamDictionary", self.virtual_OF_dir + "/system/controlDict", "-disableFunctionEntries", "-entry", "functions/#include", "-set", f"\"FOs/FO{self.function}\"" ]
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Copy function object if not already there
        FoamFile = f"FO{self.function}"
        FoamFilePath = os.path.join(self.virtual_OF_dir, 'system', 'FOs')
        shutil.copy2(function_objects_dir + f"/FO{self.function}", FoamFilePath)

        # Since the meshes should be the same, there is no difference in the selection of the mesh region.
        # If regions exist, select the appropriate region in the function object definition file
        if self.regions:
            with open(os.path.join(FoamFilePath, FoamFile), "r") as f:
                lines = f.readlines()

            with open(os.path.join(FoamFilePath, FoamFile), "w") as f:
                for line in lines:
                    if "region0" in line:
                        f.write(f"    region        {self.regions[0]};\n")
                    else:
                        f.write(line)

        return

    def setSensors(self):
        """
        This function sets cylindrical cell zone sets in 'topoSetDict' to be used as a sensor volumes.
        """

        # Read topoSetDict template
        with open(function_objects_dir +"/topoSetDict", "r") as template:
            lines = template.readlines()
        template_header = lines[:18]
        template_footer = lines[19:]

        # Create the topoSetDict in the virtual_OF_dir folder
        if self.regions:
            output_file = os.path.join(self.virtual_OF_dir, 'system', self.regions[0], 'topoSetDict')
        else:
            output_file = self.virtual_OF_dir + '/system/topoSetDict'

        # Write topoSetDict
        with open(output_file, "w") as f:
            f.writelines(template_header)
            for i, sensor in enumerate(self.sensors):
                # Construct strings for the points (space-separated values inside parentheses)
                point1_str = "(" + " ".join(str(x) for x in sensor["point1"]) + ")"
                point2_str = "(" + " ".join(str(x) for x in sensor["point2"]) + ")"

                # Construct the dictionary block
                block = (
                    "    {\n"
                    f"        name    sensor{i};\n"
                    "        type    cellZoneSet;\n"
                    "        action  new;\n"
                    "        source  cylinderToCell;\n"
                    f"        point1  {point1_str};\n"
                    f"        point2  {point2_str};\n"
                    f"        radius  {sensor['radius']};\n"
                    "    }\n"
                )
                f.write(block)
            f.writelines(template_footer)

        # Execute 'topoSet' utility
        # command = ["topoSet", "-case", self.virtual_OF_dir]
        command = ["topoSet", "-noFunctionObjects", "-time", "0", "-case", self.virtual_OF_dir]
        if self.regions:
            command += ["-region", self.regions[0]]
        with open(self.virtual_OF_dir + '/logs/topoSet.log', "w") as log_file:
            subprocess.run(command, check=True, stdout=log_file, stderr=log_file)
        return

    def execute(self):
        ## Construct path to snapshots
        if isinstance(self.snapshots_list, list) and all(isinstance(sublist, list) for sublist in self.snapshots_list):
            snapshots_list = [
                [relative_path + snapshot for snapshot in sublist] 
                for sublist in self.snapshots_list
            ]
        else:
            snapshots_list = [relative_path + snapshot for snapshot in self.snapshots_list]

        # Construct the command
        command = ["postProcess -time '0' -case " + self.virtual_OF_dir]
        if self.regions:
            command += [" -region ", self.regions[0]]

        # Set log file.
        log_path = self.virtual_OF_dir + f"/logs/{self.function}.log"

        # List of prompts and responses
        snapshots_iter = iter(snapshots_list)
        fields_iter = iter(self.fields)
        coefficients_iter = iter(self.list_of_lists_of_coefficients) if self.list_of_lists_of_coefficients is not None else None
        output_dirs_iter = iter(self.output_dirs) if self.output_dirs is not None else None

        prompt_handlers = {
            "Enter field name:": lambda: next(fields_iter),
            "Enter list of fields:": lambda: str(self.fields),
            "Enter list of points:": lambda: str(self.points),
            "Enter snapshot path: ": lambda: str(next(snapshots_iter)),
            "Enter list of snapshots:": lambda: self.__list_into_string__(next(snapshots_iter)),
            "Enter list of coefficients:": lambda: self.__list_into_string__(next(coefficients_iter)),
            "Enter output location:": lambda: next(output_dirs_iter)
        }

        # Spawn the process.
        child = pexpect.spawn(" ".join(command), encoding="utf-8", timeout=100)

        with open(log_path, "w") as log_file:
            child.logfile = log_file

            try:
                while True:
                    # Build dynamic regex pattern to match any known prompt
                    prompt_regex = "|".join(map(re.escape, prompt_handlers.keys()))
                    index = child.expect([prompt_regex, pexpect.EOF])

                    if index == 1: # EOF
                        break

                    matched_prompt = child.match.group(0)
                    response_func = prompt_handlers.get(matched_prompt)

                    if response_func:
                        try:
                            response = response_func()
                            child.sendline(response)
                        except StopIteration:
                            # End input if no more data
                            child.sendeof()
                            break

            except Exception as e:
                print(f"An error occurred: {e}")

            child.close()

        return





###############################################################################

if __name__ == "__main__":
    print("Just standing here, doing nothing...") 

