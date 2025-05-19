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
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.campaign import Campaign


def parse_bubbles(file_path):
    path = file_path

    with open(path, 'r') as f:
        csv_text = f.read()
    reader = csv.DictReader(csv_text.splitlines())
    pattern = re.compile(r'\(\s*([-0-9.]+),\s*([-0-9.]+)\)\s*\+(\d+(?:\.\d+)?)(km|mi)')

    # Group circles by constituency name
    locations_by_name = defaultdict(list)

    # Check if constituency column exists
    fieldnames = reader.fieldnames
    has_constituency_column = 'constituency' in fieldnames

    # If no constituency column, use filename
    if not has_constituency_column:
        constituency_name = os.path.splitext(os.path.basename(file_path))[0]

    for row in reader:
        m = pattern.search(row['bubble'])
        if not m:
            raise ValueError(f"Invalid bubble format: {row['bubble']!r}")
        lat, lng, radius, unit = m.groups()

        # Use constituency from CSV or filename
        if has_constituency_column:
            constituency = row['constituency']
        else:
            constituency = constituency_name

        locations_by_name[constituency].append({
            'latitude': float(lat),
            'longitude': float(lng),
            'radius': float(radius),
            'distance_unit': 'kilometer' if unit == 'km' else 'mile'
        })

    if not locations_by_name:
        print(f"No valid location data found in '{file_path}' or file is empty. Aborting ad set creation.")
        return

    return locations_by_name


def init_ad_account():
    # Retrieve credentials from environment variables
    access_token = os.getenv("FACEBOOK_ACCESS_TOKEN")
    account_id = os.getenv("FACEBOOK_ACCOUNT_ID")
    app_id = os.getenv("FACEBOOK_APP_ID")  # Optional
    app_secret = os.getenv("FACEBOOK_APP_SECRET")  # Optional

    if not access_token or not account_id:
        raise SystemExit(
            "Error: FACEBOOK_ACCESS_TOKEN and FACEBOOK_ACCOUNT_ID must be set."
        )

    # Ensure account_id has 'act_' prefix
    if not account_id.startswith('act_'):
        account_id = f'act_{account_id}'

    # Initialize Facebook Ads API
    try:
        if app_id and app_secret:
            FacebookAdsApi.init(app_id=app_id, app_secret=app_secret, access_token=access_token)
            print("Facebook Ads API initialized successfully (with App ID and App Secret).")
        else:
            FacebookAdsApi.init(access_token=access_token)
            print("Facebook Ads API initialized successfully (with access token only).")
    except Exception as e:
        raise SystemExit(f"Error: Failed to initialize Facebook Ads API: {e}")

    print(f"Using Facebook Account ID: {account_id}")
    return AdAccount(account_id)


def create_ad_sets_with_geo_targeting(locations_by_name, prefix=""):
    account = init_ad_account()

    # First, create a campaign to hold our ad sets
    campaign_params = {
        'name': f'{prefix}Geofence Campaign' if prefix else 'Geofence Campaign',
        'objective': 'OUTCOME_AWARENESS',
        'status': 'PAUSED',
        'special_ad_categories': ['ISSUES_ELECTIONS_POLITICS']  # Political advertising
    }

    try:
        campaign = account.create_campaign(params=campaign_params)
        campaign_id = campaign.get('id')
        print(f"✅ Created Campaign '{campaign_params['name']}' with ID: {campaign_id}")
    except Exception as e:
        print(f"❌ Failed to create campaign: {e}")
        return

    for name, locations in locations_by_name.items():
        # Skip if no locations
        if not locations:
            print(f"Skipping '{name}': no locations found")
            continue

        # Build targeting spec with locations as custom_locations
        targeting_spec = {
            'geo_locations': {
                'location_types': ['home', 'recent'],
                'custom_locations': locations
            }
        }

        ad_set_name = f"{prefix}{name} Geofence" if prefix else f"{name} Geofence"

        ad_set_params = {
            'name': ad_set_name,
            'campaign_id': campaign_id,
            'daily_budget': 1000,  # $10.00 in cents
            'bid_amount': 100,     # $1.00 in cents
            'billing_event': 'IMPRESSIONS',
            'optimization_goal': 'REACH',
            'targeting': targeting_spec,
            'status': 'PAUSED'
        }

        try:
            ad_set = account.create_ad_set(params=ad_set_params)
            print(f"✅ Created Ad Set '{ad_set_name}' with ID: {ad_set.get('id')}")
            print(f"   - {len(locations)} locations")
        except Exception as e:
            print(f"❌ Failed to create ad set for '{name}': {e}")
            print(f"   - Attempted to create ad set with {len(locations)} locations")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create Facebook ad sets with geographic targeting from bubble CSV data")
    parser.add_argument(
        "--file",
        default="output/constituencies/bubbles.csv",
        help="CSV file of bubbles (default: output/constituencies/bubbles.csv)",
    )
    parser.add_argument(
        "--prefix",
        default="",
        help="Optional prefix for ad set names (default: none)",
    )
    args = parser.parse_args()

    locations_data = parse_bubbles(args.file)
    if locations_data:
        create_ad_sets_with_geo_targeting(locations_data, args.prefix)
