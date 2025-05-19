import csv
import os
import argparse

try:
    from facebook_business.api import FacebookAdsApi
    from facebook_business.adobjects.adaccount import AdAccount
    from facebook_business.adobjects.savedaudience import SavedAudience
except ImportError as e:
    FacebookAdsApi = None
    AdAccount = None
    SavedAudience = None


def parse_bubbles(path):
    """Parse the CSV file and return a list of location dicts."""
    locations = []
    with open(path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            bubble = row.get("bubble")
            if not bubble:
                continue
            coords, radius_part = bubble.split(" +")
            lat_str, long_str = coords.strip("() ").split(",")
            radius_km = int(radius_part.replace("km", ""))
            locations.append({
                "latitude": float(lat_str),
                "longitude": float(long_str),
                "radius": radius_km,
                "distance_unit": "kilometer",
            })
    return locations


def create_saved_audience(account_id, token, name, locations):
    """Create a saved audience with given locations."""
    FacebookAdsApi.init(access_token=token)
    account = AdAccount(account_id)
    params = {
        "name": name,
        "targeting": {
            "geo_locations": {
                "custom_locations": locations,
            }
        },
    }
    audience = account.create_saved_audience(params=params)
    return audience


def main():
    parser = argparse.ArgumentParser(description="Create a Meta saved audience from bubble CSV data")
    parser.add_argument(
        "--file",
        default="output/constituencies/bubbles.csv",
        help="CSV file of bubbles",
    )
    parser.add_argument(
        "--name",
        default="Boundary bubbles",
        help="Name for the saved audience",
    )
    args = parser.parse_args()

    token = os.getenv("FACEBOOK_ACCESS_TOKEN")
    account_id = os.getenv("FACEBOOK_ACCOUNT_ID")
    if not token or not account_id:
        raise SystemExit("FACEBOOK_ACCESS_TOKEN and FACEBOOK_ACCOUNT_ID must be set")

    locations = parse_bubbles(args.file)

    if FacebookAdsApi is None:
        raise SystemExit("facebook_business SDK is required to run this script")

    audience = create_saved_audience(account_id, token, args.name, locations)
    print("Created audience", audience)


if __name__ == "__main__":
    main()
