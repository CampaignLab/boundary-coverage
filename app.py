from flask import Flask, render_template, send_from_directory
import csv
import os
import argparse

app = Flask(__name__)

# Global variable to store the region type
region_type = 'constituencies'

def load_statistics():
    statistics = []
    with open(f'output/{region_type}/statistics.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['name'] and row['net_coverage']:  # Skip empty rows and summary stats
                statistics.append({
                    'name': row['name'],
                    'coverage': float(row['net_coverage']),
                    'external_inclusion_coverage': float(row['external_inclusion_coverage'])
                })
    return sorted(statistics, key=lambda x: x['name'])

@app.route('/')
def index():
    statistics = load_statistics()
    region_display_name = 'Wards' if region_type == 'wards' else 'Constituencies'
    return render_template('index.html', regions=statistics, region_type=region_display_name)

@app.route('/images/<path:filename>')
def serve_image(filename):
    return send_from_directory(f'output/{region_type}/JPGs', filename + '.jpg')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run Flask app for constituencies or wards')
    parser.add_argument('--wards', action='store_true', help='Use wards instead of constituencies')
    args = parser.parse_args()
    
    # Set region type based on command line argument
    region_type = 'wards' if args.wards else 'constituencies'
    
    # Create templates directory if it doesn't exist
    if not os.path.exists('templates'):
        os.makedirs('templates')
    app.run(debug=True)
