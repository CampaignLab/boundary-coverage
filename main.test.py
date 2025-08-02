import argparse
import csv
import os
import pyproj

from boundaries import get_boundaries, filter_boundaries, setup_output_directories, setup_output_files, get_output_directory
from bubble_generation import calculate_bubbles
from analysis import compute_coverage_stats, create_boundary_visualization, write_summary_statistics

from main import process_boundary

def single_main(boundary_name):
    """
    Main function that processes a single boundary based on command line arguments.
    Generates bubble visualizations and statistics for the boundary.
    """
    parser = argparse.ArgumentParser(description='Generate bubbles for a single constituency or ward')
    args = parser.parse_args()

    boundaries, output_type = get_boundaries(True)

    if boundary_name not in [b[0] for b in boundaries]:
        print(f"Error: No boundary found with name '{boundary_name}'")
        print(f"Available boundaries: {[b[0] for b in boundaries]}...")
        return

    boundaries = [b for b in boundaries if b[0] == boundary_name]

    setup_output_directories(output_type)
    transformer = pyproj.Transformer.from_crs("epsg:27700", "epsg:4326")

    output_file, statistics_file, output_writer, statistics_writer = setup_output_files(output_type)
    
    try:
        statistics = [
            process_boundary(boundary_item, output_type, transformer, output_writer, statistics_writer)
            for boundary_item in boundaries
        ]
        write_summary_statistics(statistics_writer, statistics)
    finally:
        output_file.close()
        statistics_file.close()

if __name__ == '__main__':
    single_main("E05013671 West Hampstead")