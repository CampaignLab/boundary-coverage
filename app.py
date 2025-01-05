from flask import Flask, render_template, send_from_directory
import csv
import os

app = Flask(__name__)

def load_statistics():
    statistics = []
    with open('output/wards/statistics.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['name'] and row['coverage']:  # Skip empty rows and summary stats
                statistics.append({
                    'name': row['name'],
                    'coverage': float(row['coverage'])
                })
    return sorted(statistics, key=lambda x: x['name'])

@app.route('/')
def index():
    statistics = load_statistics()
    return render_template('index.html', constituencies=statistics)

@app.route('/images/<path:filename>')
def serve_image(filename):
    return send_from_directory('output/wards/JPGs', filename + '.jpg')

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    if not os.path.exists('templates'):
        os.makedirs('templates')
    app.run(debug=True)
