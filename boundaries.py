import fiona
import requests
import zipfile
import io
from shapely.geometry import shape
from shapely.validation import make_valid
import os
import csv

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

def setup_output_files(output_type):
    """
    Sets up and returns the output CSV files and their writers.
    
    Args:
        output_type (str): Type of output (e.g., 'constituencies' or 'wards')
    
    Returns:
        tuple: (output_file, statistics_file, output_writer, statistics_writer)
    """
    output_file = open(f'output/{output_type}/bubbles.csv', 'w')
    statistics_file = open(f'output/{output_type}/statistics.csv', 'w')
    
    output_writer = csv.writer(output_file)
    output_writer.writerow(['bubble', 'name', 'type'])
    
    statistics_writer = csv.writer(statistics_file)
    statistics_writer.writerow(['name', 'internal_inclusion_coverage', 'external_inclusion_coverage', 'exclusion_coverage', 'net_coverage'])
    
    return output_file, statistics_file, output_writer, statistics_writer


