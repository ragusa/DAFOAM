"""
Random Number Generator with CSV Output

This script generates n random numbers between two specified values and saves them
to a CSV file with columns 'caseName' and 'abs(momentumSource_z)'.

COMMAND LINE USAGE:
    python script.py <start_val> <end_val> <n> [options]

POSITIONAL ARGUMENTS:
    start_val    Starting value (float)
    end_val      Ending value (float)  
    n            Number of values to generate (positive integer)

OPTIONAL ARGUMENTS:
    -o, --output CSV_FILENAME    Output CSV filename (default: data.csv)
    -h, --help                   Show help message and exit

EXAMPLES:
    # Basic usage - generate 10 numbers between 1.0 and 5.0
    python script.py 1.0 5.0 10
    
    # Generate 5 numbers between -2.5 and 3.7
    python script.py -2.5 3.7 5
    
    # Custom output filename
    python script.py 0 1 100 -o my_data.csv
    
    # Using long form of optional argument
    python script.py 10 20 50 --output experiment_results.csv

OUTPUT:
    Creates a CSV file with two columns:
    - caseName: Sequential integers starting from 1
    - abs(momentumSource_z): Generated random values
"""

import numpy as np
import pandas as pd
import argparse
import random

def generate_values(start_val, end_val, n):
    """Generate n numbers between start_val and end_val (inclusive)"""
    if n <= 0:
        raise ValueError("n must be a positive integer")
    if n == 1:
        return [start_val]
    return [random.uniform(min(start_val, end_val), max(start_val, end_val)) for _ in range(n)]

def save_to_csv(values, filename="data.csv"):
    """Save the values to a CSV file"""
    # Create a dataframe with the required columns
    df = pd.DataFrame({
        "caseName": range(1, len(values) + 1),
        "abs(momentumSource_z)": values
    })
    
    # Save to CSV without index
    df.to_csv(filename, index=False)
    print(f"Values saved to {filename}")

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Generate n numbers between two values and save to CSV")
    parser.add_argument("start_val", type=float, help="Starting value")
    parser.add_argument("end_val", type=float, help="Ending value")
    parser.add_argument("n", type=int, help="Number of values to generate")
    parser.add_argument("-o", "--output", default="data.csv", help="Output CSV filename")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Generate values
    try:
        values = generate_values(args.start_val, args.end_val, args.n)
        # Save to CSV
        save_to_csv(values, args.output)
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    main()