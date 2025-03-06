import requests
import json
import os
import subprocess
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))

# Fetch players from API
url = "https://tank01-fantasy-stats.p.rapidapi.com/getNBAPlayerList"

# Get API credentials from environment variables
api_key = os.getenv('RAPIDAPI_KEY')
api_host = os.getenv('RAPIDAPI_HOST')

if not api_key or not api_host:
    print("Error: API credentials not found in environment variables")
    print("Please ensure RAPIDAPI_KEY and RAPIDAPI_HOST are set in the .env file")
    exit(1)

headers = {
    "x-rapidapi-key": api_key,
    "x-rapidapi-host": api_host
}

response = requests.get(url, headers=headers)
data = response.json()
players = data['body']

# Filter out players with missing values
filtered_players = []
skipped_count = 0

for player in players:
    # Skip players with missing values
    if not all([
        player.get('playerID'), 
        player.get('pos'), 
        player.get('team'), 
        player.get('longName'), 
        player.get('teamID')
    ]):
        skipped_count += 1
        continue
    
    # Format player data for database
    filtered_players.append({
        "playerID": player['playerID'],
        "position": player['pos'],
        "team": player['team'],
        "playerName": player['longName'],
        "teamID": player['teamID']
    })

# Create a temporary file to store the players data
temp_file = os.path.join(os.path.dirname(__file__), 'temp_players.json')
with open(temp_file, 'w') as f:
    json.dump(filtered_players, f)

# Call the Node.js script to store players in the database
script_path = os.path.join(os.path.dirname(__file__), 'db', 'store_players.js')
result = subprocess.run(['node', script_path, temp_file], capture_output=True, text=True)

# Print the output from the Node.js script
print(result.stdout)
if result.stderr:
    print("Errors:", result.stderr)

# Remove the temporary file
os.remove(temp_file)

print(f"Processed {len(filtered_players)} players (skipped {skipped_count} due to missing values)")