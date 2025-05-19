import fiona
import requests
import zipfile
import io
from shapely.geometry import shape
from shapely import Point, GeometryCollection, LineString, MultiPolygon, union_all, minimum_rotated_rectangle, buffer, is_empty
from shapely.validation import make_valid
import os
import matplotlib.pyplot as plt
import numpy as np
import pyproj
import csv
import argparse

BUBBLE_LIMIT = 200

england_shapefile_url = 'https://boundarycommissionforengland.independent.gov.uk/wp-content/uploads/2023/06/984162_2023_06_27_Final_recommendations_England_shp.zip'
scotland_shapefile_url = 'https://www.bcomm-scotland.independent.gov.uk/sites/default/files/2023_review_final/bcs_final_recs_2023_review.zip'
wales_shapefile_url = 'https://bcomm-wales.gov.uk/sites/bcomm/files/review/Shapefiles.zip'

# https://www.data.gov.uk/dataset/0bdfd7a6-e6a4-4d63-a684-b6dda1d86d47/wards-may-2024-boundaries-uk-bsc
wards_shapefile_url = 'https://open-geography-portalx-ons.hub.arcgis.com/api/download/v1/items/b58c65bdad994ed3a33741eea7bb09ab/geoPackage?layers=0'

england_shapefile_filename = '2023_06_27_Final_recommendations_England.shp'
scotland_shapefile_filename = 'All_Scotland_Final_Recommended_Constituencies_2023_Review.shp'
wales_shapefile_filename = 'Final Recs Shapefiles/Final Recommendations_region.shp'

wards_shapefile_filename = 'Wards_May_2024_Boundaries_UK_BSC_8498175397534686318.gpkg'

def download_and_extract(url, path):
    """
    Downloads a zip file from a URL and extracts its contents to a specified path.

    Args:
        url (str): The URL of the zip file to download
        path (str): The relative path where the contents should be extracted
    """
    filepath = os.path.join('data', path)
    if os.path.exists(filepath):
        print(f'{filepath} already exists')
        return

    print(f'Downloading {url}')
    response = requests.get(url)
    print(f'Extracting to {filepath}')
    zip_file = zipfile.ZipFile(io.BytesIO(response.content))
    zip_file.extractall(filepath)

def download_to_file(url, path):
    """
    Downloads a file from a URL and saves it directly to the specified path.

    Args:
        url (str): The URL of the file to download
        path (str): The relative path where the file should be saved
    """
    print(f'Downloading {url} to {path}')
    filepath = os.path.join('data', path)
    if os.path.exists(filepath):
        print(f'{filepath} already exists')
        return

    response = requests.get(url, allow_redirects=True)
    response.raise_for_status()

    with open(filepath, 'wb') as f:
        f.write(response.content)

def create_boundary_list(shapefile_path, key1, key2=None):
    """
    Creates a list of boundary tuples from a shapefile, where each tuple contains a key and its corresponding shape.

    Args:
        shapefile_path (str): Path to the shapefile
        key1 (str): Primary key field name in the shapefile properties
        key2 (str, optional): Secondary key field name to concatenate with key1

    Returns:
        list: List of tuples containing (key, shape) pairs
    """
    boundaries = []
    with fiona.open('data/' + shapefile_path) as boundaries_file:
        for boundary in boundaries_file:
            boundary_shape = make_valid(shape(boundary['geometry']))
            key = boundary.properties[key1]
            if key2:
                key = key + ' ' + boundary.properties[key2]
            boundaries.append((key, boundary_shape))
        return boundaries

def calculate_radius_upper_bound(boundary):
    """
    Calculates the maximum possible radius for bubbles within a boundary based on its minimum rotated rectangle.

    Args:
        boundary: A shapely geometry object representing the boundary

    Returns:
        int: Upper bound radius in meters, rounded to nearest thousand
    """
    mrr = minimum_rotated_rectangle(boundary)
    x, y = mrr.exterior.xy
    edge_lengths = (
        Point(x[0], y[0]).distance(Point(x[1], y[1])),
        Point(x[1], y[1]).distance(Point(x[2], y[2]))
    )

    width = min(edge_lengths)
    return int((width // 2000) * 1000)

def calculate_step(polygons, radius, bubble_length):
    """
    Calculates the step size between bubble centers based on the polygon length and bubble constraints.

    Args:
        polygons (list): List of shapely polygon objects
        radius (float): Current bubble radius
        bubble_length (int): Current number of bubbles

    Returns:
        float: Step size between bubble centers
    """
    total_polygon_length = sum([polygon.exterior.length for polygon in polygons])
    iteration_bubble_count = total_polygon_length / radius
    step = radius
    is_last_iteration = radius == 1000 or (bubble_length + iteration_bubble_count) > BUBBLE_LIMIT

    if is_last_iteration:
        step = total_polygon_length / (BUBBLE_LIMIT - bubble_length)

    return step

def calculate_bubbles(boundary):
    """
    Generate inclusion and exclusion bubbles for a boundary.

    Args:
        boundary: A shapely geometry object representing the boundary

    Returns:
        tuple: (list of inclusion bubble geometries, list of inclusion bubble data [x, y, radius],
               list of exclusion bubble geometries, list of exclusion bubble data [x, y, radius])
    """
    radius = calculate_radius_upper_bound(boundary)
    island_of_possibility = None

    inclusion_bubbles = []
    inclusion_data = []

    padded_boundary = boundary.buffer(500)

    while radius > 0 and len(inclusion_bubbles) < BUBBLE_LIMIT:
        island_of_possibility = buffer(padded_boundary, -(radius + 30))

        if not is_empty(island_of_possibility):
            print(f'   {radius}')
            polygons = island_of_possibility.geoms if isinstance(island_of_possibility, MultiPolygon) else [island_of_possibility]

            step = calculate_step(polygons, radius, len(inclusion_bubbles))
            for polygon in polygons:
                for interpolation in np.arange(0, polygon.exterior.length, step):
                    point = polygon.exterior.interpolate(interpolation)
                    bubble = point.buffer(radius)
                    if padded_boundary.contains(bubble):
                        inclusion_bubbles.append(bubble)
                        inclusion_data.append([point.x, point.y, int(radius / 1000)])

        if len(inclusion_bubbles) > 0:
            radius = (radius // 1500) * 1000
        else:
            radius -= 1000

    # Generate exclusion bubbles around the perimeter
    exclusion_bubbles = []
    exclusion_data = []
    
    # Use a smaller radius for exclusion bubbles
    exclusion_radius = 1000  # 1km radius for exclusion bubbles
    
    # Get the boundary exterior
    padded_boundary = boundary.buffer(1000)
    polygons = padded_boundary.geoms if isinstance(padded_boundary, MultiPolygon) else [padded_boundary]
    print(len(polygons))
    for polygon in polygons:
        if isinstance(polygon, LineString):
            continue
            
        # Calculate step size based on the perimeter length
        perimeter = polygon.exterior.length
        step = exclusion_radius / 4 # Some overlap
        
        # Place exclusion bubbles along the perimeter
        for distance in np.arange(0, perimeter, step):
            point = polygon.exterior.interpolate(distance)
            bubble = point.buffer(exclusion_radius)
            exclusion_bubbles.append(bubble)
            exclusion_data.append([point.x, point.y, int(exclusion_radius / 1000)])

    return (
        inclusion_bubbles[:BUBBLE_LIMIT],
        inclusion_data[:BUBBLE_LIMIT],
        exclusion_bubbles,
        exclusion_data
    )

def get_statistics_row(boundary_name, coverage_percentage, bubblesData):
    """
    Creates a statistics row for a boundary containing coverage and bubble count by radius.

    Args:
        boundary_name (str): Name of the boundary
        coverage_percentage (float): Percentage of boundary covered by bubbles
        bubblesData (list): List of bubble data [x, y, radius]

    Returns:
        list: Statistics row containing boundary name, coverage, and bubble counts
    """
    statistics_row = [boundary_name, coverage_percentage]

    if len(bubblesData) == 0:
        return statistics_row

    bubble_count_by_radius = {}
    for (_, _, radius) in bubblesData:
        if radius in bubble_count_by_radius:
            bubble_count_by_radius[radius] += 1
        else:
            bubble_count_by_radius[radius] = 1

    for radius in range(1, max(bubble_count_by_radius.keys()) + 1):
        if radius in bubble_count_by_radius:
            statistics_row.append(bubble_count_by_radius[radius])
        else:
            statistics_row.append(0)

    return statistics_row

def get_output_directory(output_type, directory_type):
    """
    Returns the directory path for output files.

    Args:
        output_type (str): Type of output (e.g., 'constituencies' or 'wards')
        directory_type (str): Type of directory ('JPGs' or 'CSVs')

    Returns:
        str: Path to the output directory
    """
    return os.path.join(f'output/{output_type}/{directory_type}')

def setup_output_directories(output_type):
    """
    Creates necessary output directories for storing results.

    Args:
        output_type (str): Type of output (e.g., 'constituencies' or 'wards')
    """
    if not os.path.exists(output_type):
        os.makedirs(output_type)
    if not os.path.exists(f'output/{output_type}'):
        os.makedirs(f'output/{output_type}')
    if not os.path.exists(get_output_directory(output_type, 'JPGs')):
        os.makedirs(get_output_directory(output_type, 'JPGs'))
    if not os.path.exists(get_output_directory(output_type, 'CSVs')):
        os.makedirs(get_output_directory(output_type, 'CSVs'))

def get_boundaries(use_wards):
    """
    Retrieves boundary data either for wards or constituencies.

    Args:
        use_wards (bool): If True, retrieves ward boundaries; if False, retrieves constituency boundaries

    Returns:
        tuple: (list of boundary tuples, output type string)
    """
    if use_wards:
        wards_path = 'wards/' + wards_shapefile_filename
        download_to_file(wards_shapefile_url, wards_path)
        return create_boundary_list(wards_path, 'WD24CD', 'WD24NM'), 'wards'
    else:
        download_and_extract(england_shapefile_url, 'england')
        download_and_extract(scotland_shapefile_url, 'scotland')
        download_and_extract(wales_shapefile_url, 'wales')

        england_constituencies = create_boundary_list('england/' + england_shapefile_filename, 'Constituen')
        scotland_constituencies = create_boundary_list('scotland/' + scotland_shapefile_filename, 'NAME')
        wales_constituencies = create_boundary_list('wales/' + wales_shapefile_filename, 'Official_N')

        return england_constituencies + scotland_constituencies + wales_constituencies, 'constituencies'

def write_summary_statistics(statistics_writer, statistics):
    """
    Writes summary statistics for inclusion, exclusion, and net coverage.
    
    Args:
        statistics_writer: CSV writer object
        statistics (list): List of coverage statistics dictionaries
    """
    statistics_writer.writerow(['', '', '', ''])
    for stat_type in ['inclusion', 'exclusion', 'net']:
        values = [s[stat_type] for s in statistics]
        statistics_writer.writerow([f'{stat_type}_mean', sum(values) / len(values)])
        statistics_writer.writerow([f'{stat_type}_median', np.median(values)])
        statistics_writer.writerow([f'{stat_type}_min', min(values)])
        statistics_writer.writerow([f'{stat_type}_max', max(values)])
        statistics_writer.writerow([f'{stat_type}_sigma', np.std(values)])

def setup_output_files(output_type):
    """
    Sets up and returns the output CSV files and their writers.
    
    Args:
        output_type (str): Type of output (e.g., 'constituencies' or 'wards')
    
    Returns:
        tuple: (output_writer, statistics_writer)
    """
    output_file = open(f'output/{output_type}/bubbles.csv', 'w')
    statistics_file = open(f'output/{output_type}/statistics.csv', 'w')
    
    output_writer = csv.writer(output_file)
    output_writer.writerow(['bubble', 'name', 'type'])
    
    statistics_writer = csv.writer(statistics_file)
    statistics_writer.writerow(['name', 'inclusion_coverage', 'exclusion_coverage', 'net_coverage'])
    
    return output_file, statistics_file, output_writer, statistics_writer

def filter_boundaries(boundaries, region):
    """
    Filters boundaries to only include the specified region.
    
    Args:
        boundaries (list): List of boundary tuples
        region (str): Name of region to filter for
    
    Returns:
        list: Filtered list of boundaries
    """
    if not region:
        return boundaries
        
    original_count = len(boundaries)
    filtered = [b for b in boundaries if b[0] == region]
    if not filtered:
        print(f"Error: No region found with name '{region}'")
        print(f"Available regions: {[b[0] for b in boundaries]}...")
        return []
        
    print(f"Processing single region: {region} (filtered from {original_count} regions)")
    return filtered

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

    # Assuming calculate_bubbles now returns both inclusion and exclusion bubbles
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
    inclusion_union = union_all(inclusion_bubbles)
    exclusion_union = union_all(exclusion_bubbles)
    
    # Calculate areas
    inclusion_area = inclusion_union.area
    exclusion_area = exclusion_union.area
    overlap_area = inclusion_union.intersection(exclusion_union).area
    
    # Calculate coverage percentages
    inclusion_coverage = 100 * inclusion_area / boundary.area
    exclusion_coverage = 100 * exclusion_area / boundary.area
    net_coverage = 100 * (inclusion_area - overlap_area) / boundary.area
    
    coverage_stats = {
        "inclusion": inclusion_coverage,
        "exclusion": exclusion_coverage,
        "net": net_coverage
    }
    
    # Write statistics
    statistics_writer.writerow([
        boundary_name,
        inclusion_coverage,
        exclusion_coverage,
        net_coverage
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

def create_boundary_visualization(boundary_name, boundary, inclusion_bubbles, exclusion_bubbles, coverage_stats, output_type):
    """
    Creates and saves a visualization of a boundary and its bubbles.

    Args:
        boundary_name (str): Name of the boundary
        boundary: Shapely geometry object representing the boundary
        inclusion_bubbles (list): List of inclusion bubble geometries
        exclusion_bubbles (list): List of exclusion bubble geometries
        coverage_stats (dict): Dictionary containing coverage statistics
        output_type (str): Type of output (e.g., 'constituencies' or 'wards')
    """
    jpeg_path = os.path.join(get_output_directory(output_type, 'JPGs'), boundary_name.replace('/', '&') + '.jpg')
    print(jpeg_path)

    fig, ax = plt.subplots(1, 2)
    ax[0].set_aspect('equal', adjustable='box')
    ax[1].set_aspect('equal', adjustable='box')
    fig.suptitle(boundary_name, y=0.98)

    area_sq_km = boundary.area / 1_000_000
    coverage_text = (
        f'Inclusion coverage: {coverage_stats["inclusion"]:.0f}%\n'
        f'Exclusion coverage: {coverage_stats["exclusion"]:.0f}%\n'
        f'Net coverage: {coverage_stats["net"]:.0f}%\n'
        f'Area: {area_sq_km:.1f} km²'
    )
    fig.text(0.5, 0.85, coverage_text, ha='center', fontsize=12)

    ax[0].xaxis.set_visible(False)
    ax[0].yaxis.set_visible(False)
    ax[1].xaxis.set_visible(False)
    ax[1].yaxis.set_visible(False)

    plot_boundary(ax, boundary)
    plot_bubbles(ax, inclusion_bubbles, exclusion_bubbles)

    fig.savefig(jpeg_path, dpi=300)
    plt.close(fig)

def plot_boundary(ax, boundary):
    """
    Plots the boundary outline on both subplots.

    Args:
        ax: Matplotlib axes array
        boundary: Shapely geometry object representing the boundary
    """
    polygons = boundary.geoms if isinstance(boundary, GeometryCollection) or isinstance(boundary, MultiPolygon) else [boundary]
    for polygon in polygons:
        if isinstance(polygon, LineString):
            continue
        rings = [polygon.exterior] + [interior for interior in polygon.interiors]
        for ring in rings:
            x, y = ring.xy
            ax[0].plot(x, y, color='blue')
            ax[1].plot(x, y, color='blue')

def plot_bubbles(ax, inclusion_bubbles, exclusion_bubbles):
    """
    Plots inclusion and exclusion bubbles on both subplots.
    
    Args:
        ax: Matplotlib axes array
        inclusion_bubbles (list): List of inclusion bubble geometries
        exclusion_bubbles (list): List of exclusion bubble geometries
    """
    # Plot inclusion bubbles in green
    for bubble in inclusion_bubbles:
        x, y = bubble.exterior.xy
        ax[0].plot(x, y, color='green', linewidth=0.5)
        ax[1].fill(x, y, color='green', alpha=0.5)
    
    # Plot exclusion bubbles in red
    for bubble in exclusion_bubbles:
        x, y = bubble.exterior.xy
        ax[0].plot(x, y, color='red', linewidth=0.5)
        ax[1].fill(x, y, color='red', alpha=0.5)

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
