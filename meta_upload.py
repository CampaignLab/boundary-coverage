import csv
import re
import os
import argparse
from collections import defaultdict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.exceptions import FacebookRequestError


def parse_bubbles(args):
    path = args.file

    with open(path, 'r') as f:
        csv_text = f.read()
    reader = csv.DictReader(csv_text.splitlines())
    pattern = re.compile(r'\(\s*([-0-9.]+),\s*([-0-9.]+)\)\s*\+(\d+(?:\.\d+)?)(km|mi)')

    # Group circles by constituency name
    locations_by_name = defaultdict(list)

    for row in reader:
        m = pattern.search(row['bubble'])
        if not m:
            raise ValueError(f"Invalid bubble format: {row['bubble']!r}")
        lat, lng, radius, unit = m.groups()
        locations_by_name[row['constituency']].append({
            'latitude':      float(lat),
            'longitude':     float(lng),
            'radius':        float(radius),
            'distance_unit': 'kilometer' if unit == 'km' else 'mile'
        })

    if not locations_by_name:
        print(f"No valid location data found in '{args.file}' or file is empty. Aborting audience creation.")
        return

    return locations_by_name


def init_ad_account():
    # Retrieve credentials from environment variables
    access_token = os.getenv("FACEBOOK_ACCESS_TOKEN")
    account_id = os.getenv("FACEBOOK_ACCOUNT_ID")
    app_id = os.getenv("FACEBOOK_APP_ID")  # Recommended for API initialization
    app_secret = os.getenv("FACEBOOK_APP_SECRET")  # Recommended for API initialization

    if not access_token or not account_id:
        raise SystemExit(
            "Error: FACEBOOK_ACCESS_TOKEN and FACEBOOK_ACCOUNT_ID must be set as environment variables."
        )

    # Initialize Facebook Ads API
    try:
        if app_id and app_secret:
            FacebookAdsApi.init(app_id=app_id, app_secret=app_secret, access_token=access_token)
            print("Facebook Ads API initialized successfully (with App ID and App Secret).")
    except Exception as e:
        raise SystemExit(f"Error: Failed to initialize Facebook Ads API: {e}")

    return AdAccount(account_id)


def create_saved_audience(audiences_by_name):
    account = init_ad_account()

    for name, audience_data in audiences_by_name.items():
        inclusions = audience_data.get('inclusions', [])
        exclusions = audience_data.get('exclusions', [])
        
        # Skip if no locations at all
        if not inclusions and not exclusions:
            print(f"Skipping '{name}': no inclusion or exclusion locations found")
            continue
        
        # Build targeting spec with both inclusions and exclusions
        targeting_spec = {
            'geo_locations': {
                'location_types': ['home', 'recent']
            }
        }
        
        # Add inclusion locations
        if inclusions:
            targeting_spec['geo_locations']['custom_locations'] = inclusions
        
        # Add exclusion locations  
        if exclusions:
            targeting_spec['geo_locations']['excluded_custom_locations'] = exclusions
        
        params = {
            'name': name + ' Geofence',
            'description': f'Geofence for {name} with {len(inclusions)} inclusions and {len(exclusions)} exclusions',
            'targeting_spec': targeting_spec
        }
        
        try:
            audience = account.create_saved_audience(params=params)
            print(f"Created Saved Audience '{name}' with ID: {audience.get('id')}")
            print(f"  - {len(inclusions)} inclusion locations")
            print(f"  - {len(exclusions)} exclusion locations")
        except Exception as e:
            print(f"Failed to create audience for '{name}': {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a Meta saved audience from bubble CSV data")
    parser.add_argument(
        "--file",
        default="output/constituencies/bubbles.csv",
        help="CSV file of bubbles (default: output/constituencies/bubbles.csv)",
    )
    parser.add_argument(
        "--prefix",
        default="",
        help="Optional prefix for audience names (default: none)",
    )
    args = parser.parse_args()

    create_saved_audience(parse_bubbles(args.file))
