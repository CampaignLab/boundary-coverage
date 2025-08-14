from shapely.geometry import Point, MultiPolygon, LineString
from shapely import minimum_rotated_rectangle, buffer, is_empty, minimum_bounding_circle
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
        Point(x[1], y[1]).distance(Point(x[2], y[2])),
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


def generate_inclusion_bubbles(boundary, initial_radius, padding=0):
    """
    Generate bubbles using the large radius approach (stepping down from initial radius).

    Args:
        boundary: A shapely geometry object representing the boundary
        initial_radius: Starting radius for bubble generation
        padding: Optional padding to apply to the boundary (default: 0)

    Returns:
        tuple: (list of inclusion bubble geometries, list of inclusion bubble data [x, y, radius])
    """
    radius = initial_radius
    inclusion_bubbles = []
    inclusion_data = []
    padded_boundary = boundary.buffer(padding) if padding else boundary

    while radius > 0 and len(inclusion_bubbles) < BUBBLE_LIMIT:
        island_of_possibility = buffer(padded_boundary, -(radius + 30))

        if not is_empty(island_of_possibility):
            print(f"   {radius}")
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
                    if padded_boundary.contains(bubble):
                        inclusion_bubbles.append(bubble)
                        inclusion_data.append([point.x, point.y, int(radius / 1000)])

        if len(inclusion_bubbles) > 0:
            radius = (radius // 1500) * 1000
        else:
            radius -= 1000

    return inclusion_bubbles, inclusion_data


def calculate_bubbles_inclusions_only(boundary):
    """
    Original bubble calculation algorithm - inclusions only.

    Args:
        boundary: A shapely geometry object representing the boundary

    Returns:
        tuple: (list of inclusion bubble geometries, list of inclusion bubble data [x, y, radius],
                list of exclusion bubble geometries, list of exclusion bubble data [x, y, radius])
    """

    radius = calculate_radius_upper_bound(boundary)

    # Generate inclusion bubbles with padding
    inclusion_bubbles, inclusion_data = generate_inclusion_bubbles(
        boundary, radius
    )

    return (
        inclusion_bubbles[:BUBBLE_LIMIT],
        inclusion_data[:BUBBLE_LIMIT],
        [],
        [],
    )


def create_minimum_bounding_circle(boundary):
    """
    Creates the smallest circle that can contain the entire boundary using Shapely's built-in function.

    Args:
        boundary: A shapely geometry object representing the boundary

    Returns:
        tuple: (bubble geometry, bubble data [x, y, radius])
    """
    circle = minimum_bounding_circle(boundary)

    centroid = circle.centroid
    # For a circle, the radius is the distance from center to any point on the boundary
    # We can get this from the circle's bounds
    minx, miny, maxx, maxy = circle.bounds
    radius = (maxx - minx) / 2

    return circle, [centroid.x, centroid.y, int(radius)]


def generate_exclusion_bubbles(boundary):
    """
    Generate exclusion bubbles for a boundary.
    """
    exclusion_bubbles = []
    exclusion_data = []

    # Use a smaller radius for exclusion bubbles
    exclusion_radius = 1000  # 1km radius for exclusion bubbles

    # Get the boundary exterior
    padded_boundary = boundary.buffer(1000)
    polygons = (
        padded_boundary.geoms
        if isinstance(padded_boundary, MultiPolygon)
        else [padded_boundary]
    )

    for polygon in polygons:
        if isinstance(polygon, LineString):
            continue

        # Calculate step size based on the perimeter length
        perimeter = polygon.exterior.length
        step = exclusion_radius / 4  # Some overlap

        # Place exclusion bubbles along the perimeter
        for distance in np.arange(0, perimeter, step):
            point = polygon.exterior.interpolate(distance)
            bubble = point.buffer(exclusion_radius)
            exclusion_bubbles.append(bubble)
            exclusion_data.append([point.x, point.y, int(exclusion_radius / 1000)])

    return exclusion_bubbles, exclusion_data


def calculate_bubbles_with_exclusions(boundary):
    """
    Generate inclusion and exclusion bubbles for a boundary.

    Args:
        boundary: A shapely geometry object representing the boundary

    Returns:
        tuple: (list of inclusion bubble geometries, list of inclusion bubble data [x, y, radius],
                list of exclusion bubble geometries, list of exclusion bubble data [x, y, radius])
    """
    radius = calculate_radius_upper_bound(boundary)

    # Generate inclusion bubbles with padding
    inclusion_bubbles, inclusion_data = generate_inclusion_bubbles(
        boundary, radius, padding=500
    )

    # Use minimum bounding circle as fallback if no bubbles were generated
    if len(inclusion_bubbles) == 0:
        bubble, bubble_data = create_minimum_bounding_circle(boundary)
        inclusion_bubbles = [bubble]
        inclusion_data = [bubble_data]

    # Generate exclusion bubbles using the existing function
    exclusion_bubbles, exclusion_data = generate_exclusion_bubbles(boundary)

    return (
        inclusion_bubbles[:BUBBLE_LIMIT],
        inclusion_data[:BUBBLE_LIMIT],
        exclusion_bubbles,
        exclusion_data,
    )
