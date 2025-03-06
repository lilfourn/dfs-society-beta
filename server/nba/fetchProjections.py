import requests
import json
import sys
import subprocess
import os
from datetime import datetime
from pprint import pprint

def delete_old_projections():
    """
    Delete projections from the database whose start time has already passed.
    
    Returns:
        dict: The result of the deletion operation
    """
    # Get the path to the script that will use Prisma to delete old projections
    script_path = os.path.join(os.path.dirname(__file__), 'db', 'delete_old_projections.js')
    
    # Run the Node.js script to delete old projections
    try:
        result = subprocess.run(['node', script_path], 
                               capture_output=True, text=True, check=True)
        
        # Parse the JSON result
        result_data = json.loads(result.stdout.strip().split('\n')[-1])
        
        if result_data.get('success'):
            print(f"Successfully deleted {result_data.get('deletedCount', 0)} old projections")
        else:
            print(f"Error deleting old projections: {result_data.get('error', 'Unknown error')}")
        
        return result_data
    except subprocess.CalledProcessError as e:
        print(f"Error running delete_old_projections.js: {e}")
        print(f"Error output: {e.stderr}")
        return {"success": False, "error": str(e)}
    except json.JSONDecodeError as e:
        print(f"Error parsing result from delete_old_projections.js: {e}")
        print(f"Output: {result.stdout}")
        return {"success": False, "error": str(e)}

def fetch_prizepicks_projections():
    """
    Fetch projections data from PrizePicks API and store in the database.
    First removes old projections whose start time has already passed.
    
    Returns:
        dict: The full API response data
    """
    # First, delete old projections
    delete_result = delete_old_projections()
    if not delete_result.get('success'):
        print("Warning: Failed to delete old projections. Continuing with fetch...")
    
    # Current time for logging
    current_time = datetime.now().isoformat()
    print(f"Current time: {current_time}")
    print("Fetching new projections...")
    url = 'https://partner-api.prizepicks.com/projections?league_id=7&per_page=10'
    
    # Set up headers for the request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json'
    }
    
    try:
        # Make the request to the API
        response = requests.get(url, headers=headers)
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Parse the JSON response
        data = response.json()
        
        print(f"Response contains {len(data.get('data', []))} projection entries")
        
        # Print sample start_time values to check date formatting
        print("\nSample start_time values from API:")
        for i, projection in enumerate(data.get('data', [])[:5]):
            start_time = projection['attributes'].get('start_time')
            game_id = projection['attributes'].get('game_id', 'N/A')
            print(f"  {i+1}. Raw start_time: {start_time}")
            
            # Try to parse the date and print it in different formats
            if start_time:
                try:
                    dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    print(f"     Parsed as: {dt}")
                    print(f"     ISO format: {dt.isoformat()}")
                    print(f"     Date only (YYYY-MM-DD): {dt.date()}")
                    print(f"     API format (YYYYMMDD): {dt.strftime('%Y%m%d')}")
                    print(f"     Game ID: {game_id}")
                except Exception as e:
                    print(f"     Error parsing date: {e}")
        
        # Create a lookup dictionary for included items
        included_lookup = {f"{item['type']}_{item['id']}": item for item in data['included']}
        
        # Process each projection and store in database
        projections_data = []
        for projection in data.get('data', []):
            # Default values
            player_name = "N/A"
            team = "N/A"
            position = "N/A"
            average = None
            max_value = None
            image_url = None
            odds_type = None
            
            # Get player data if available
            if 'new_player' in projection['relationships'] and projection['relationships']['new_player']['data']:
                player_ref = projection['relationships']['new_player']['data']
                player_key = f"{player_ref['type']}_{player_ref['id']}"
                if player_key in included_lookup:
                    player = included_lookup[player_key]
                    player_name = player['attributes'].get('display_name', "N/A")
                    team = player['attributes'].get('team', "N/A")
                    position = player['attributes'].get('position', "N/A")
                    image_url = player['attributes'].get('image_url')
            
            # Get stat average data if available
            if 'stat_average' in projection['relationships'] and projection['relationships']['stat_average']['data']:
                stat_ref = projection['relationships']['stat_average']['data']
                stat_key = f"{stat_ref['type']}_{stat_ref['id']}"
                if stat_key in included_lookup:
                    stat = included_lookup[stat_key]
                    average_val = stat['attributes'].get('average')
                    max_val = stat['attributes'].get('max_value')
                    
                    # Convert to float if not None
                    average = float(average_val) if average_val is not None else None
                    max_value = float(max_val) if max_val is not None else None
            
            # Get odds_type from projection attributes
            odds_type = projection['attributes'].get('odds_type')
            
            # Get line_score and convert to float
            line_score_val = projection['attributes'].get('line_score')
            line_score = float(line_score_val) if line_score_val is not None else 0.0
            
            # Get the start_time and parse it correctly
            raw_start_time = projection['attributes'].get('start_time')
            parsed_start_time = datetime.now().isoformat()
            
            if raw_start_time:
                try:
                    # Parse the ISO format date and preserve the original timezone
                    # Important: Keep the original timezone to avoid date shifting
                    dt = datetime.fromisoformat(raw_start_time)
                    
                    # Store the date exactly as it is from the API, preserving timezone
                    # This is critical to avoid UTC conversion issues
                    parsed_start_time = raw_start_time
                    
                    # Print debug info for a few projections
                    if len(projections_data) < 5:
                        print(f"Debug - Game ID: {projection['attributes'].get('game_id', 'N/A')}")
                        print(f"Debug - Raw start time: {raw_start_time}")
                        print(f"Debug - Parsed start time: {parsed_start_time}")
                        print(f"Debug - Date only: {dt.date()}")
                        print(f"Debug - YYYYMMDD format: {dt.strftime('%Y%m%d')}")
                        print(f"Debug - Will be stored as: {parsed_start_time}")
                except Exception as e:
                    print(f"Warning: Error parsing date {raw_start_time}: {e}")
            
            # Format the projection data for database
            projection_data = {
                "projectionId": projection['id'],
                "playerName": player_name,
                "team": team,
                "position": position,
                "statType": projection['attributes'].get('stat_type', "N/A"),
                "lineScore": line_score,
                "average": average,
                "maxValue": max_value,
                "gameId": projection['attributes'].get('game_id', "N/A"),
                "startTime": parsed_start_time,
                "status": projection['attributes'].get('status', "N/A"),
                "description": projection['attributes'].get('description'),
                "imageUrl": image_url,
                "oddsType": odds_type
            }
            
            projections_data.append(projection_data)
        
        # Store projections in database using Prisma
        store_projections_in_db(projections_data)
        
        print(f"Successfully stored {len(projections_data)} projections in the database")
        
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from PrizePicks API: {e}")
        return None

def store_projections_in_db(projections_data):
    """
    Store projections in the database using Prisma.
    
    Args:
        projections_data (list): List of projection data dictionaries
    """
    # Print some debug information about the dates we're storing
    date_counts = {}
    for proj in projections_data:
        start_time = proj.get('startTime')
        if start_time:
            try:
                dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                date_str = dt.strftime('%Y-%m-%d')
                date_counts[date_str] = date_counts.get(date_str, 0) + 1
            except Exception:
                pass
    
    print("\nDates in projections data:")
    for date, count in date_counts.items():
        print(f"  {date}: {count} projections")
    
    # Create a temporary JSON file with the projections data
    temp_file = os.path.join(os.path.dirname(__file__), 'temp_projections.json')
    with open(temp_file, 'w') as f:
        json.dump(projections_data, f)
    
    # Get the path to the script that will use Prisma to store the data
    script_path = os.path.join(os.path.dirname(__file__), 'db', 'store_projections.js')
    
    # Run the Node.js script to store the data
    try:
        result = subprocess.run(['node', script_path, temp_file], 
                               capture_output=True, text=True, check=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error storing projections in database: {e}")
        print(f"Error output: {e.stderr}")
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file):
            os.remove(temp_file)

if __name__ == "__main__":
    # Execute the function when the script is run directly
    fetch_prizepicks_projections()