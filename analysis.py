from shapely.geometry import Point, GeometryCollection, LineString, MultiPolygon
from shapely import union_all
import matplotlib.pyplot as plt
import numpy as np
import os

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

def compute_coverage_stats(boundary, inclusion_bubbles, exclusion_bubbles):
    """
    Computes coverage statistics for a boundary based on inclusion and exclusion bubbles.

    Args:
        boundary: Shapely geometry object representing the boundary
        inclusion_bubbles (list): List of inclusion bubble geometries
        exclusion_bubbles (list): List of exclusion bubble geometries

    Returns:
        dict: Coverage statistics including internal_inclusion, external_inclusion, exclusion, and net coverage percentages
    """
    inclusion_union = union_all(inclusion_bubbles) if inclusion_bubbles else Point(0, 0).buffer(0)
    exclusion_union = union_all(exclusion_bubbles) if exclusion_bubbles else Point(0, 0).buffer(0)
    
    # Calculate internal inclusion area (inclusion bubbles that intersect with boundary)
    internal_inclusion_area = inclusion_union.intersection(boundary).area
    
    # Calculate external inclusion area (inclusion bubbles outside boundary, not covered by exclusion)
    external_inclusion_area = inclusion_union.difference(boundary).difference(exclusion_union).area
    
    # Calculate exclusion area (only the part that intersects with boundary)
    exclusion_area = exclusion_union.intersection(boundary).area
    
    # Calculate coverage percentages
    internal_inclusion_coverage = 100 * internal_inclusion_area / boundary.area
    exclusion_coverage = 100 * exclusion_area / boundary.area
    external_inclusion_coverage = 100 * external_inclusion_area / boundary.area
    
    # Net coverage should be the area within boundary covered by inclusion but NOT exclusion
    net_area_within_boundary = inclusion_union.intersection(boundary).difference(exclusion_union).area
    net_coverage = 100 * net_area_within_boundary / boundary.area
    
    coverage_stats = {
        "internal_inclusion": internal_inclusion_coverage,
        "external_inclusion": external_inclusion_coverage,
        "exclusion": exclusion_coverage,
        "net": net_coverage
    }
    
    return coverage_stats

def write_summary_statistics(statistics_writer, statistics):
    """
    Writes summary statistics for inclusion, exclusion, and net coverage.
    
    Args:
        statistics_writer: CSV writer object
        statistics (list): List of coverage statistics dictionaries
    """
    statistics_writer.writerow(['', '', '', '', ''])
    for stat_type in ['internal_inclusion', 'external_inclusion', 'exclusion', 'net']:
        values = [s[stat_type] for s in statistics]
        statistics_writer.writerow([f'{stat_type}_mean', sum(values) / len(values)])
        statistics_writer.writerow([f'{stat_type}_median', np.median(values)])
        statistics_writer.writerow([f'{stat_type}_min', min(values)])
        statistics_writer.writerow([f'{stat_type}_max', max(values)])
        statistics_writer.writerow([f'{stat_type}_sigma', np.std(values)])


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
    from boundaries import get_output_directory
    from utils import sanitize_filename
    
    jpeg_path = os.path.join(get_output_directory(output_type, 'JPGs'), sanitize_filename(boundary_name) + '.jpg')
    print(jpeg_path)

    fig, ax = plt.subplots(1, 2)
    ax[0].set_aspect('equal', adjustable='box')
    ax[1].set_aspect('equal', adjustable='box')
    fig.suptitle(boundary_name, y=0.98)

    area_sq_km = boundary.area / 1_000_000
    coverage_text = (
        f'Coverage: {coverage_stats["net"]:.0f}%\n'
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