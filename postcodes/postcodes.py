#!/usr/bin/python3
#
# Parse postcodes RM's PAF CSV and analyses postcode sectors
# against wards.

import csv
import json
import pprint
import re
import sys
import yaml
from typing import List, Dict, Set, Any

def parse_csv_file(
    file_path: str,
    sectors: Dict[str, Dict[str, List[str]]],
    sectors2: Dict[str, List[str]],
    wards: Set[str]
) -> None:
  with open(file_path, 'r', newline='') as csvfile:
    reader = csv.DictReader(csvfile)

    for i, record in enumerate(reader):
      if i % 1000 == 0:
        print('.', end='', flush=True)

      sector = record['Postcode Sector']
      ward = '%s %s' % (record['Ward Code'], record['Ward Name'])
      postcode = record['Postcode']

      wards.add(ward)
      if sector not in sectors:
        sectors[sector] = {}
        sectors2[sector] = []

      multiple_wards = False
      if ward not in sectors[sector]:
        sectors[sector][ward] = []
        sectors2[sector].append(ward)
        wards_in_sector = len(sectors[sector])
        if wards_in_sector > 1:
          multiple_wards = True

      sectors[sector][ward].append(postcode)
      # if multiple_wards:
      #   out = pprint.pformat(sectors[sector], indent=2, compact=True)
      #   print(f'{sector} now has {wards_in_sector} wards:')
      #   print(re.sub('^', '  ', out, flags=re.MULTILINE))

    print(f'\n{i} postcodes processed')
    print(f'{len(sectors)} postcode sectors')
    print(f'{len(wards)} wards')


def main():
  if len(sys.argv) < 2:
    print("Usage: ./postcodes.py <csv_file> [[csv_file2] ...]", file=sys.stderr)
    sys.exit(1)

  sectors = {}  # Dict[Sector, Dict[Ward, List[postcode]]]
  sectors2 = {} # Dict[Sector, List[Ward]]
  wards = set()

  for file in sys.argv[1:]:
    parse_csv_file(file, sectors, sectors2, wards)

  sectors3 = []  # List[Tuple[Sector, int]]
  for sector, wards in sorted(sectors2.items(), key=lambda x: len(x[1]), reverse=True):
    sectors3.append((sector, len(wards)))

  sectors3.sort(key=lambda x: x[1], reverse=True)

  with open('sectors.json', 'w') as f:
    json.dump(sectors, f, indent=2)

  with open('sectors.yaml', 'w') as f:
    yaml.dump(sectors, f)

  with open('sectors2.json', 'w') as f:
    json.dump(sectors2, f, indent=2)

  with open('sectors2.yaml', 'w') as f:
    yaml.dump(sectors2, f)

  with open('sectors3.json', 'w') as f:
    json.dump(sectors3, f, indent=2)

  with open('sectors3.txt', 'w') as f:
    for sector, ward_count in sectors3:
      f.write(f'{sector}: {ward_count} wards\n')

  with open('sectors-1-ward.csv', 'w') as f:
    f.write('Sector,Ward Code,Ward Name\n')
    for sector, ward_count in sectors3:
      if ward_count == 1:
        ward = sectors2[sector][0].replace(' ', ',', 1)
        f.write(f'{sector},{ward}\n')


if __name__ == '__main__':
  main()
