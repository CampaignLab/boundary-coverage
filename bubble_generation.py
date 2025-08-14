from shapely.geometry import Point, MultiPolygon
from shapely import minimum_rotated_rectangle, buffer, is_empty
import numpy as np

BUBBLE_LIMIT = 200

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
    is_last_iteration = (
        radius == 1000 or (bubble_length + iteration_bubble_count) > BUBBLE_LIMIT
    )

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

    while radius > 0 and len(inclusion_bubbles) < BUBBLE_LIMIT:
        island_of_possibility = buffer(boundary, -(radius + 30))

        if not is_empty(island_of_possibility):
            print(f'   {radius}')
            polygons = (
                island_of_possibility.geoms
                if isinstance(island_of_possibility, MultiPolygon)
                else [island_of_possibility]
            )

            step = calculate_step(polygons, radius, len(inclusion_bubbles))
            for polygon in polygons:
                for interpolation in np.arange(0, polygon.exterior.length, step):
                    point = polygon.exterior.interpolate(interpolation)
                    bubble = point.buffer(radius)
                    if boundary.contains(bubble):
                        inclusion_bubbles.append(bubble)
                        inclusion_data.append([point.x, point.y, int(radius / 1000)])

        if len(inclusion_bubbles) > 0:
            radius = (radius // 1500) * 1000
        else:
            radius -= 1000

    exclusion_bubbles = []
    exclusion_data = []

    return (
        inclusion_bubbles[:BUBBLE_LIMIT],
        inclusion_data[:BUBBLE_LIMIT],
        exclusion_bubbles,
        exclusion_data,
    )
