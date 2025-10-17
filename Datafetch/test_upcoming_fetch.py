#!/usr/bin/env python3
"""
Test script for upcoming races fetcher
Debug why it's returning 0 races
"""

import requests
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Load credentials
CRED_FILE = Path(__file__).parent / "reqd_files" / "cred.txt"
with open(CRED_FILE, "r") as f:
    USERNAME = f.readline().strip()
    PASSWORD = f.readline().strip()

# Calculate dates
today = datetime.now()
yesterday = today - timedelta(days=1)
tomorrow = today + timedelta(days=1)

dates = [
    yesterday.strftime("%Y-%m-%d"),
    today.strftime("%Y-%m-%d"),
    tomorrow.strftime("%Y-%m-%d")
]

print(f"Testing upcoming races fetch for:")
for date in dates:
    print(f"  - {date}")
print()

# Test each date
url = "https://api.theracingapi.com/v1/racecards/pro"

for date in dates:
    print(f"Fetching {date}...")
    params = {'date': date}
    
    try:
        response = requests.get(url, auth=(USERNAME, PASSWORD), params=params, timeout=30)
        
        print(f"  Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            racecards = data.get('racecards', [])
            print(f"  Racecards found: {len(racecards)}")
            
            if racecards:
                # Show first race as sample
                first_race = racecards[0]
                print(f"  Sample race:")
                print(f"    - Course: {first_race.get('course')}")
                print(f"    - Time: {first_race.get('off_time')}")
                print(f"    - Race: {first_race.get('race_name')}")
            else:
                print(f"  No races found for this date")
        else:
            print(f"  Error: {response.text[:200]}")
            
    except Exception as e:
        print(f"  Exception: {e}")
    
    print()

print("Test complete!")

