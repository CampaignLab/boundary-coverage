# Meta API Setup Guide

This guide walks you through setting up Meta (Facebook) API access and
using the `meta_upload.py` script to create Facebook ad sets with
geographic targeting for political advertising.

## Prerequisites

- A Facebook account
- Access to Facebook Ads Manager (either personal or business account)

## 1. Creating a Facebook App and Getting a Long-lived Token

### Steps:

1. Go to [Facebook for Developers](https://developers.facebook.com/)

2. Create a new app:
   - Choose **Business** or **None** → Name your app → Skip optional setup

3. Go to "Tools → Graph API Explorer"

4. **Select your app** in the top right dropdown

5. Click "Get Token" → "Get User Access Token"
   - Select these permissions:
     - `ads_management`
     - `business_management`

6. Click "Generate Access Token"

7. Go to [Access Token Debugger](https://developers.facebook.com/tools/debug/accesstoken/)
   - Paste the token → Click **Debug**
   - Click "Extend Access Token" to get a long-lived token (valid for ~60 days)

Now you can save this long-lived access token in your `.env`
file, and it'll work for your personal ad account or business ad
accounts you manage.

---

## 2. Get Your FACEBOOK_ACCOUNT_ID

### Manual Method:
- Go to [Facebook Ads Manager](https://www.facebook.com/adsmanager/)
- Copy the number from the URL: `act_1234567890` → that's your `FACEBOOK_ACCOUNT_ID` (use just the number part, without `act_`)

---

## 3. Environment Setup

Create a `.env` file in your project root with:

```env
FACEBOOK_ACCESS_TOKEN=your_long_lived_token_here
FACEBOOK_ACCOUNT_ID=1234567890
```

Optional (most users won't need these):

```env
FACEBOOK_APP_ID=your_app_id
FACEBOOK_APP_SECRET=your_app_secret
```

---

## 4. How the Script Works

The `meta_upload.py` script creates:
- **One Facebook Campaign** per execution (marked as political advertising)
- **One Ad Set per constituency/region** with precise geographic targeting using your bubble locations
- **Proper compliance** for political advertising using `ISSUES_ELECTIONS_POLITICS` special ad category

### Usage Examples

```bash
# Upload bubbles for a single constituency
python meta_upload.py --file output/constituencies/CSVs/Aldershot.csv --prefix "UK Election 2024: "

# Upload bubbles for all constituencies
python meta_upload.py --file output/constituencies/bubbles.csv --prefix "UK Election 2024: "
```

This will create ad sets like:
- "UK Election 2024: Aldershot Geofence" (200 locations)
- "UK Election 2024: Birmingham Erdington Geofence" (150 locations)
- etc.

---

## 5. Viewing Your Ad Sets

To view and manage the created ad sets in your Facebook account, go to:

👉 **[Meta Ads Manager – Your Account](https://www.facebook.com/adsmanager/manage/campaigns)**

This will take you to your campaign dashboard, where you can:
- View all created campaigns and ad sets
- Edit targeting, budgets, and bid amounts
- Create ads and attach them to your geographic ad sets
- Activate ad sets when ready to start campaigning
- Monitor performance and adjust settings

All ad sets are created in "PAUSED" status so you can review and configure them before going live.

---

## 6. Inclusion and Exclusion Targeting

The system supports inclusion and exclusion targeting through an optional `type` column in the CSV:

- **inclusion**: Locations that should be targeted (default if type is missing)
- **exclusion**: Locations that should be excluded from targeting

For each constituency/region, the script creates **one ad set** that combines both inclusion and exclusion locations in the same targeting specification:

```python
# Example targeting_spec structure
{
    'geo_locations': {
        'location_types': ['home', 'recent'],
        'custom_locations': [
            # inclusion locations go here
        ],
        'excluded_custom_locations': [
            # exclusion locations go here
        ]
    }
}
```

This approach allows you to use the ad set directly without needing to manage separate inclusion and exclusion targeting.

---

## Troubleshooting

### Common Issues:

1. **"Invalid access token"**
   - Your token may have expired (long-lived tokens last ~60 days)
   - Generate a new long-lived token following step 1

2. **"Insufficient permissions"**
   - Make sure you selected `ads_management` and `business_management` permissions
   - You may need to request additional permissions from your Business Manager admin

3. **"Account not found"**
   - Double-check your `FACEBOOK_ACCOUNT_ID` format (should be just numbers, no `act_` prefix)
   - Ensure you have access to the ad account

4. **"Campaign creation failed"**
   - Ensure you have proper permissions for political advertising
   - The script automatically sets `ISSUES_ELECTIONS_POLITICS` for compliance

### Permission Details:

- `ads_management` - Required to create, read, update, and delete ad objects including campaigns and ad sets
- `business_management` - Required to access your Ad Account and manage business assets
- `ads_read` - Optional, useful for reading existing campaigns and ad sets
- `read_insights` - Optional, only needed for analytics

## Security Notes

- Never commit your `.env` file to version control
- Long-lived tokens expire after ~60 days and will need to be refreshed
- Store tokens securely and limit access to authorized personnel only
- Political advertising may have additional compliance requirements in your jurisdiction
