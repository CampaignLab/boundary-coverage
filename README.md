# Filling constituencies with circles

*Completed bubbles found here*
https://drive.google.com/drive/folders/18DFu78sS90x-3FpQmy7LHtLcuGedilCR?usp=sharing

## What is this?

This project 'fills' the England, Scotland and Wales revised 2023 Westminster constituencies with circles according to the following parameters:
 - The circles' radii are multiples of 1km, with a minimum radius of 1km
 - The circles can overlap
 - A constituency can have at most 200 circles

 ## How can I use the results?

The calculated circles can be found [here](output/constituencies/bubbles.csv).

The percentage coverage achieved for each constituency can be found [here](output/constituencies/statistics.csv).

A visualisation of the circles calculated and coverage achieved for each constituency can be found [here](output/constituencies/JPGs).


## How well does this work?

The average coverage achieved is 86%.

Vale of Glamorgan is the constituency covered most completely:
![Visualisation of the calculated circles and coverage for Vale of Glamorgan](./output/constituencies/JPGs/Vale%20of%20Glamorgan.jpg?raw=true)

Beaconsfield has coverage closest to the average:
![Visualisation of the calculated circles and coverage for Beaconsfield](./output/constituencies/JPGs/Beaconsfield.jpg?raw=true)

Excluding constituencies that have no coverage at all, Southgate and Wood Green has the smallest coverage:
![Visualisation of the calculated circles and coverage for Southgate and Wood Green](./output/constituencies/JPGs/Southgate%20and%20Wood%20Green.jpg?raw=true)

Seven constituencies are small enough and/or awkwardly-shaped enough that they can't even fit any of the smallest 1km radius circles:
 - [Bermondsey and Old Southwark](./output/constituencies/JPGs/Bermondsey%20and%20Old%20Southwark.jpg)
 - [Hackney South and Shoreditch](./output/constituencies/JPGs/Hackney%20South%20and%20Shoreditch.jpg)
 - [Hammersmith and Chiswick](./output/constituencies/JPGs/Hammersmith%20and%20Chiswick.jpg)
 - [Holborn and St Pancras](./output/constituencies/JPGs/Holborn%20and%20St%20Pancras.jpg)
 - [Islington North](./output/constituencies/JPGs/Islington%20North.jpg)
 - [Islington South and Finsbury](./output/constituencies/JPGs/Islington%20South%20and%20Finsbury.jpg)
 - [Queen's Park and Maida Vale](./output/constituencies/JPGs/Queen's%20Park%20and%20Maida%20Vale.jpg)

## How can I run this myself?

  - Clone the repository
  - Change directory into the repository
  - Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if you haven't already
  - Install the dependencies:

      uv sync --all-extras

  - Run `uv run python main.py`, which will:
    - Download and fetch shapefiles for constituencies into `data/`
    - Write images showing bubble coverage into `output/constituencies/JPGs`
    - Write `output/constituencies/bubbles.csv` with one bubble per record
    - Write `output/constituencies/statistics.csv` with one constituency per record

  - Run `uv run python app.py` and view http://localhost:5000/

## Uploading bubbles to Meta

The `meta_upload.py` script creates Facebook ad sets with geographic
targeting for political advertising using your bubble data.

**📋 Complete setup guide:** [`docs/meta-api-setup.md`](docs/meta-api-setup.md)

### Quick Start

1. **Setup**: Follow the [Meta API Setup Guide](docs/meta-api-setup.md) to get your access token and account ID
2. **Create `.env` file**:
   ```
   FACEBOOK_ACCESS_TOKEN=your_token_here
   FACEBOOK_ACCOUNT_ID=your_account_id
   ```
3. **Run the script**:
   ```bash
   python meta_upload.py --file output/constituencies/CSVs/Aldershot.csv --prefix "UK Election 2024: "
   ```
4. **View results**: Go to [Meta Ads Manager](https://www.facebook.com/adsmanager/manage/campaigns) to see your campaigns and ad sets

The script creates Facebook campaigns and ad sets with precise geographic targeting, properly marked for political advertising compliance.

## Was this done for the current/old/pre-2024 constituencies?

Yes!

The calculated circles for the **old** constituencies can be found [here](https://github.com/12v/boundary-bubbler/blob/old_constituencies/output/old-bubbles.csv).

The percentage coverage achieved for each **old** constituency can be found [here](https://github.com/12v/boundary-bubbler/blob/old_constituencies/output/old-statistics.csv).

A visualisation of the circles calculated and coverage achieved for each **old** constituency can be found [here](https://github.com/12v/boundary-bubbler/tree/old_constituencies/output/constituencies/JPGs).
