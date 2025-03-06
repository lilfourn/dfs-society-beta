import requests
import subprocess
import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add the project root to the path to import from other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), '.env'))

def get_nba_injuries(days=3):
    """
    Fetch NBA injury data from the Tank01 Fantasy Stats API
    
    Args:
        days (int): Number of days to look ahead for injuries
        
    Returns:
        dict: JSON response from the API
    """
    url = "https://tank01-fantasy-stats.p.rapidapi.com/getNBAInjuryList"
    
    querystring = {"numberOfDays": str(days)}
    
    # Get API credentials from environment variables
    api_key = os.getenv('RAPIDAPI_KEY')
    api_host = os.getenv('RAPIDAPI_HOST')
    
    if not api_key or not api_host:
        print("Error: API credentials not found in environment variables")
        print("Please ensure RAPIDAPI_KEY and RAPIDAPI_HOST are set in the .env file")
        return None
    
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": api_host
    }
    
    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching injury data: {e}")
        return None

def get_player_from_db(player_id):
    """
    Query the database for a player with the given ID using Prisma
    
    Args:
        player_id (str): The player ID to look up
        
    Returns:
        dict: Player information if found, None otherwise
    """
    # Create a temporary Node.js script to query the database
    temp_script_path = os.path.join(os.path.dirname(__file__), 'temp_query_player.js')
    
    script_content = f"""
    const {{ PrismaClient }} = require('@prisma/client');
    const prisma = new PrismaClient();
    
    async function getPlayer() {{
        try {{
            const player = await prisma.nbaPlayer.findUnique({{
                where: {{ playerID: "{player_id}" }}
            }});
            
            console.log(JSON.stringify(player));
        }} catch (error) {{
            console.error(error);
            process.exit(1);
        }} finally {{
            await prisma.$disconnect();
        }}
    }}
    
    getPlayer();
    """
    
    try:
        # Write the temporary script
        with open(temp_script_path, 'w') as f:
            f.write(script_content)
        
        # Execute the script
        result = subprocess.run(['node', temp_script_path], 
                               capture_output=True, 
                               text=True, 
                               cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
        
        # Remove the temporary script
        os.remove(temp_script_path)
        
        if result.returncode != 0:
            print(f"Error querying database: {result.stderr}")
            return None
        
        # Parse the output as JSON
        player_data = json.loads(result.stdout.strip())
        return player_data
    
    except Exception as e:
        print(f"Error getting player from database: {e}")
        if os.path.exists(temp_script_path):
            os.remove(temp_script_path)
        return None

def get_player_projections(player_name):
    """
    Query the database for projections for a player with the given name
    
    Args:
        player_name (str): The player name to look up
        
    Returns:
        list: List of projections if found, empty list otherwise
    """
    # Create a temporary Node.js script to query the database
    temp_script_path = os.path.join(os.path.dirname(__file__), 'temp_query_projections.js')
    
    script_content = f"""
    const {{ PrismaClient }} = require('@prisma/client');
    const prisma = new PrismaClient();
    
    async function getProjections() {{
        try {{
            // Get projections for the player that have a future start time
            const projections = await prisma.projection.findMany({{
                where: {{ 
                    playerName: "{player_name}",
                    startTime: {{
                        gte: new Date()
                    }}
                }}
            }});
            
            console.log(JSON.stringify(projections));
        }} catch (error) {{
            console.error(error);
            process.exit(1);
        }} finally {{
            await prisma.$disconnect();
        }}
    }}
    
    getProjections();
    """
    
    try:
        # Write the temporary script
        with open(temp_script_path, 'w') as f:
            f.write(script_content)
        
        # Execute the script
        result = subprocess.run(['node', temp_script_path], 
                               capture_output=True, 
                               text=True, 
                               cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
        
        # Remove the temporary script
        os.remove(temp_script_path)
        
        if result.returncode != 0:
            print(f"Error querying projections: {result.stderr}")
            return []
        
        # Parse the output as JSON
        projections_data = json.loads(result.stdout.strip())
        return projections_data
    
    except Exception as e:
        print(f"Error getting projections from database: {e}")
        if os.path.exists(temp_script_path):
            os.remove(temp_script_path)
        return []

def connect_injuries_with_players():
    """
    Connect NBA injury data with player information from our database
    
    Returns:
        list: List of dictionaries containing player name and injury status
    """
    # Get injury data
    injury_data = get_nba_injuries()
    
    if not injury_data or 'statusCode' not in injury_data or injury_data['statusCode'] != 200:
        print("Failed to fetch injury data or invalid response")
        return []
    
    # Extract the list of injured players
    injured_players = injury_data.get('body', [])
    
    # Create a dictionary to store unique player injuries (using the most recent entry)
    unique_player_injuries = {}
    
    # Process each injury entry
    for injury in injured_players:
        player_id = injury.get('playerID')
        
        # Skip entries without player ID
        if not player_id:
            continue
        
        # Store or update the injury info (will keep the latest entry for each player)
        unique_player_injuries[player_id] = {
            'designation': injury.get('designation', 'Unknown'),
            'description': injury.get('description', ''),
            'injDate': injury.get('injDate', ''),
            'injReturnDate': injury.get('injReturnDate', '')
        }
    
    # Connect with player data from database
    result = []
    
    for player_id, injury_info in unique_player_injuries.items():
        # Get player data from database
        player_data = get_player_from_db(player_id)
        
        if player_data:
            # Format dates if available
            inj_date = injury_info.get('injDate', '')
            return_date = injury_info.get('injReturnDate', '')
            
            if inj_date and len(inj_date) == 8:
                inj_date = f"{inj_date[:4]}-{inj_date[4:6]}-{inj_date[6:8]}"
            
            if return_date and len(return_date) == 8:
                return_date = f"{return_date[:4]}-{return_date[4:6]}-{return_date[6:8]}"
            
            # Get player projections
            player_name = player_data.get('playerName', '')
            projections = get_player_projections(player_name) if player_name else []
            
            # Create a formatted entry
            entry = {
                'playerName': player_name or 'Unknown Player',
                'team': player_data.get('team', 'Unknown Team'),
                'position': player_data.get('position', 'Unknown Position'),
                'status': injury_info.get('designation', 'Unknown'),
                'description': injury_info.get('description', ''),
                'injuryDate': inj_date,
                'expectedReturnDate': return_date,
                'hasProjections': len(projections) > 0,
                'projections': projections
            }
            
            result.append(entry)
        else:
            print(f"Player with ID {player_id} not found in database")
    
    return result

def print_injury_report():
    """
    Print a formatted injury report
    """
    injury_data = connect_injuries_with_players()
    
    if not injury_data:
        print("No injury data available")
        return
    
    print("\n===== NBA INJURY REPORT =====")
    print(f"Report generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total players with injuries: {len(injury_data)}\n")
    
    # Group by status
    status_groups = {}
    for player in injury_data:
        status = player['status']
        if status not in status_groups:
            status_groups[status] = []
        status_groups[status].append(player)
    
    # Print by status group
    for status, players in status_groups.items():
        print(f"\n== {status} ({len(players)}) ==")
        
        for player in players:
            has_projections = player.get('hasProjections', False)
            projections_marker = "⚠️ HAS PROJECTIONS" if has_projections else ""
            
            print(f"{player['playerName']} ({player['team']} - {player['position']}) {projections_marker}")
            print(f"  Return: {player['expectedReturnDate'] or 'Unknown'}")
            print(f"  Info: {player['description']}")
            
            # Print projection details if available
            if has_projections and 'projections' in player:
                print("  Projections:")
                for proj in player['projections']:
                    game_time = datetime.fromisoformat(proj.get('startTime', '').replace('Z', '+00:00'))
                    formatted_time = game_time.strftime('%Y-%m-%d %H:%M')
                    stat_type = proj.get('statType', 'Unknown')
                    line_score = proj.get('lineScore', 0)
                    opponent = proj.get('opponent', 'Unknown')
                    print(f"    - {stat_type}: {line_score} vs {opponent} ({formatted_time})")
            
            print()

def print_projections_affected_by_injuries():
    """
    Print a report of projections affected by injuries
    """
    injury_data = connect_injuries_with_players()
    
    if not injury_data:
        print("No injury data available")
        return
    
    # Filter players with projections
    players_with_projections = [p for p in injury_data if p.get('hasProjections', False)]
    
    if not players_with_projections:
        print("\nNo projections affected by injuries")
        return
    
    print("\n===== PROJECTIONS AFFECTED BY INJURIES =====")
    print(f"Report generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total players with projections and injuries: {len(players_with_projections)}\n")
    
    # Group by status
    status_groups = {}
    for player in players_with_projections:
        status = player['status']
        if status not in status_groups:
            status_groups[status] = []
        status_groups[status].append(player)
    
    # Print by status group
    for status, players in sorted(status_groups.items()):
        print(f"\n== {status} ({len(players)}) ==")
        
        for player in players:
            print(f"{player['playerName']} ({player['team']} - {player['position']})")
            print(f"  Return: {player['expectedReturnDate'] or 'Unknown'}")
            print(f"  Info: {player['description']}")
            
            # Print projection details
            print("  Projections:")
            for proj in player.get('projections', []):
                game_time = datetime.fromisoformat(proj.get('startTime', '').replace('Z', '+00:00'))
                formatted_time = game_time.strftime('%Y-%m-%d %H:%M')
                stat_type = proj.get('statType', 'Unknown')
                line_score = proj.get('lineScore', 0)
                opponent = proj.get('opponent', 'Unknown')
                print(f"    - {stat_type}: {line_score} vs {opponent} ({formatted_time})")
            
            print()

if __name__ == "__main__":
    # If run directly, print the injury report and projections affected by injuries
    print_injury_report()
    print_projections_affected_by_injuries()