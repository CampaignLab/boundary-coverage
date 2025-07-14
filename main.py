import argparse
import csv
import os
import pyproj

from boundaries import get_boundaries, filter_boundaries, setup_output_directories, setup_output_files, get_output_directory
from bubble_generation import calculate_bubbles
from analysis import compute_coverage_stats, create_boundary_visualization, write_summary_statistics

def process_boundary(boundary_item, output_type, transformer, output_writer, statistics_writer):
    """
    Processes a single boundary: generates bubbles, creates visualizations, and writes statistics.

    Args:
        boundary_item (tuple): (boundary name, boundary geometry)
        output_type (str): Type of boundaries being processed
        transformer: Coordinate transformer object
        output_writer: CSV writer for bubble data
        statistics_writer: CSV writer for statistics

    Returns:
        dict: Coverage statistics for this boundary
    """
    boundary_name = boundary_item[0]
    boundary = boundary_item[1]

    inclusion_bubbles, inclusion_data, exclusion_bubbles, exclusion_data = calculate_bubbles(boundary)

    # Write bubble data to CSV
    csv_file = os.path.join(get_output_directory(output_type, 'CSVs'), f'{boundary_name}.csv')
    with open(csv_file, 'w') as csv_output:
        bubbles_writer = csv.writer(csv_output)
        bubbles_writer.writerow(['bubble_type', 'coordinates', 'radius'])
        
        # Write inclusion bubbles
        for (x, y, radius) in inclusion_data:
            lat, long = transformer.transform(x, y)
            bubble_str = f'({lat}, {long}) +{radius}km'
            bubbles_writer.writerow(['inclusion', bubble_str, radius])
            output_writer.writerow([bubble_str, boundary_name, 'inclusion'])
        
        # Write exclusion bubbles
        for (x, y, radius) in exclusion_data:
            lat, long = transformer.transform(x, y)
            bubble_str = f'({lat}, {long}) +{radius}km'
            bubbles_writer.writerow(['exclusion', bubble_str, radius])
            output_writer.writerow([bubble_str, boundary_name, 'exclusion'])

    # Calculate coverage statistics
    coverage_stats = compute_coverage_stats(boundary, inclusion_bubbles, exclusion_bubbles)
    
    # Write statistics
    statistics_writer.writerow([
        boundary_name,
        coverage_stats["internal_inclusion"],
        coverage_stats["external_inclusion"],
        coverage_stats["exclusion"],
        coverage_stats["net"]
    ])

    create_boundary_visualization(
        boundary_name,
        boundary,
        inclusion_bubbles,
        exclusion_bubbles,
        coverage_stats,
        output_type
    )

    return coverage_stats

def main():
    """
    Main function that processes either constituency or ward boundaries based on command line arguments.
    Generates bubble visualizations and statistics for each boundary.
    """
    parser = argparse.ArgumentParser(description='Generate bubbles for constituencies or wards')
    parser.add_argument('--wards', action='store_true', help='Use wards instead of constituencies')
    parser.add_argument('--region', type=str, help='Name of the region to process (exact match)')
    args = parser.parse_args()

    boundaries, output_type = get_boundaries(args.wards)
    boundaries = filter_boundaries(boundaries, args.region)
    if not boundaries:
        return

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
    main()