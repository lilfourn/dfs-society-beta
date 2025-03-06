import subprocess
import json
import os
import requests
import logging
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), '.env'))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to fetch game odds from the API
def fetch_game_odds(game_date):
    url = "https://tank01-fantasy-stats.p.rapidapi.com/getNBABettingOdds"
    
    querystring = {"gameDate": game_date, "itemFormat": "map"}
    
    # Get API credentials from environment variables
    api_key = os.getenv('RAPIDAPI_KEY')
    api_host = os.getenv('RAPIDAPI_HOST')
    
    if not api_key or not api_host:
        print(f"Error: API credentials not found in environment variables for date {game_date}")
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
        print(f"Error fetching game odds for date {game_date}: {str(e)}")
        return None

# Function to update projections with odds data
def update_projections_with_odds(db_game_id, game_info, api_game_id):
    """
    Update projections with odds data for a specific game
    
    Args:
        db_game_id (str): The database game ID
        game_info (dict): The game information from the API
        api_game_id (str): The API game ID
    """
    try:
        # Extract the odds data we want to store
        home_team = game_info.get('homeTeam', '')
        away_team = game_info.get('awayTeam', '')
        
        # Get the best odds provider (prefer DraftKings if available)
        odds_provider = 'draftkings'
        if odds_provider not in game_info:
            # Fallback to another provider
            for provider in ['fanduel', 'betmgm', 'bet365']:
                if provider in game_info:
                    odds_provider = provider
                    break
        
        if odds_provider not in game_info:
            logging.warning(f"No odds provider found for game {api_game_id}")
            return
        
        provider_data = game_info[odds_provider]
        
        # Create the odds data object
        odds_data = {
            'homeTeam': home_team,
            'awayTeam': away_team,
            'homeSpread': provider_data.get('homeTeamSpread', '0'),
            'awaySpread': provider_data.get('awayTeamSpread', '0'),
            'totalOver': provider_data.get('totalOver', '0'),
            'totalUnder': provider_data.get('totalUnder', '0'),
            'homeMoneyline': provider_data.get('homeTeamMLOdds', '0'),
            'awayMoneyline': provider_data.get('awayTeamMLOdds', '0'),
            'oddsProvider': odds_provider,
            'lastUpdated': game_info.get('last_updated_e_time', '')
        }
        
        # Convert the odds data to JSON
        odds_data_json = json.dumps(odds_data)
        
        # Path to the Node.js script
        update_script_path = os.path.join(os.path.dirname(__file__), 'db', 'update_projections_with_odds.js')
        
        # Run the Node.js script to update projections
        logging.info(f"Updating projections for game {db_game_id} with odds data")
        result = subprocess.run(['node', update_script_path, db_game_id, odds_data_json], 
                               capture_output=True, text=True)
        
        if result.returncode != 0:
            logging.error(f"Error updating projections: {result.stderr}")
            return
        
        # Parse the result
        try:
            update_result = json.loads(result.stdout)
            if update_result.get('success', False):
                logging.info(f"Successfully updated {update_result.get('count', 0)} projections for game {db_game_id}")
            else:
                logging.warning(f"Failed to update projections: {update_result.get('message', 'Unknown error')}")
        except json.JSONDecodeError:
            logging.error(f"Error parsing update result: {result.stdout}")
    
    except Exception as e:
        logging.error(f"Error updating projections with odds: {str(e)}")

# Function to map API game IDs to our database game IDs
def map_game_ids(api_game_id, team_to_game_id, game_teams):
    # Extract teams from API game ID (format: YYYYMMDD_AWAY@HOME)
    parts = api_game_id.split('_')
    if len(parts) != 2:
        return False, None
    
    matchup = parts[1].split('@')
    if len(matchup) != 2:
        return False, None
    
    away_team, home_team = matchup
    
    # Team abbreviation mappings (in case there are differences)
    team_mappings = {
        'PHX': ['PHO', 'PHOENIX', 'SUNS'],
        'GSW': ['GS', 'GOLDEN', 'WARRIORS'],
        'SAC': ['SACRAMENTO', 'KINGS'],
        'LAL': ['LA', 'LAKERS', 'LOS ANGELES L'],
        'LAC': ['LA', 'CLIPPERS', 'LOS ANGELES C'],
        'NYK': ['NY', 'KNICKS', 'NEW YORK'],
        'BKN': ['BRK', 'BROOKLYN', 'NETS'],
        'NOP': ['NO', 'PELICANS', 'NEW ORLEANS'],
        'SAS': ['SA', 'SPURS', 'SAN ANTONIO'],
        'CHI': ['CHICAGO', 'BULLS'],
        'CLE': ['CLEVELAND', 'CAVALIERS', 'CAVS'],
        'DET': ['DETROIT', 'PISTONS'],
        'IND': ['INDIANA', 'PACERS'],
        'MIL': ['MILWAUKEE', 'BUCKS'],
        'ATL': ['ATLANTA', 'HAWKS'],
        'CHA': ['CHARLOTTE', 'HORNETS'],
        'MIA': ['MIAMI', 'HEAT'],
        'ORL': ['ORLANDO', 'MAGIC'],
        'WAS': ['WASHINGTON', 'WIZARDS'],
        'DEN': ['DENVER', 'NUGGETS'],
        'MIN': ['MINNESOTA', 'TIMBERWOLVES'],
        'OKC': ['OKLAHOMA', 'THUNDER'],
        'POR': ['PORTLAND', 'TRAIL BLAZERS'],
        'UTA': ['UTAH', 'JAZZ'],
        'BOS': ['BOSTON', 'CELTICS'],
        'PHI': ['PHILADELPHIA', '76ERS', 'SIXERS'],
        'TOR': ['TORONTO', 'RAPTORS'],
        'DAL': ['DALLAS', 'MAVERICKS', 'MAVS'],
        'HOU': ['HOUSTON', 'ROCKETS'],
        'MEM': ['MEMPHIS', 'GRIZZLIES']
    }
    
    # Get possible variations of team abbreviations
    home_variations = [home_team.upper()]
    away_variations = [away_team.upper()]
    
    for team, variations in team_mappings.items():
        if team.upper() == home_team.upper() or home_team.upper() in variations:
            home_variations.extend([team] + variations)
        if team.upper() == away_team.upper() or away_team.upper() in variations:
            away_variations.extend([team] + variations)
    
    # First try to find an exact match for both teams
    for team_abbr, game_id in team_to_game_id.items():
        if team_abbr in home_variations or team_abbr in away_variations:
            # Found a team, now check if the other team is in the same game
            other_teams = game_teams.get(game_id, set())
            
            # Check if any of the other teams in this game match the other team in the API game
            if team_abbr in home_variations and any(t in away_variations for t in other_teams):
                return True, game_id
            if team_abbr in away_variations and any(t in home_variations for t in other_teams):
                return True, game_id
    
    return False, None

# Path to the Node.js script
script_path = os.path.join(os.path.dirname(__file__), 'db', 'query_projections.js')

# Run the Node.js script to query projections
result = subprocess.run(['node', script_path], capture_output=True, text=True)

# Check if there was an error
if result.stderr and not result.stdout:
    print(f"Error querying projections: {result.stderr}")
    exit(1)

# Parse the JSON output
try:
    projections = json.loads(result.stdout)
    
    # Check if we have any projections
    if not projections:
        print("No projections found in the database.")
        exit(0)
    
    # Get unique dates from projections and also add today's date
    unique_dates = set()
    date_to_games = defaultdict(set)  # To store game IDs for each date
    
    # Create a mapping of teams to game IDs
    team_to_game_id = {}
    game_teams = {}  # Store both teams for each game ID
    
    # Add today's date to check for current games
    today_date = datetime.now().strftime("%Y%m%d")
    unique_dates.add(today_date)
    
    # Debug information
    print("\nDebug - Processing projections:")
    
    for projection in projections:
        # Parse the start time with timezone handling
        # The startTime in the database is stored in UTC
        # We need to convert it back to US Central Time for proper date matching
        start_time_str = projection['startTime']
        
        try:
            # Parse the date from the database (in UTC)
            if 'Z' in start_time_str:
                # ISO format with Z (UTC)
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            elif '+' in start_time_str or '-' in start_time_str and 'T' in start_time_str:
                # ISO format with explicit timezone
                start_time = datetime.fromisoformat(start_time_str)
            else:
                # JavaScript Date object string format
                # Example: "Thu Mar 06 2025 18:40:00 GMT-0600 (Central Standard Time)"
                # Extract the date components
                date_parts = start_time_str.split(' ')
                if len(date_parts) >= 4:
                    month_map = {
                        'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
                        'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
                        'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
                    }
                    month = month_map.get(date_parts[1], '01')
                    day = date_parts[2].zfill(2)
                    year = date_parts[3]
                    
                    # Format as YYYY-MM-DD
                    formatted_date = f"{year}{month}{day}"
                    
                    # Debug the first few projections
                    if len(unique_dates) < 3:
                        print(f"  JS Date format - Raw: {start_time_str}")
                        print(f"  JS Date format - Parsed: {year}-{month}-{day}")
                        print(f"  JS Date format - Formatted: {formatted_date}")
                    
                    unique_dates.add(formatted_date)
                    
                    # Store game ID for this date
                    if projection['gameId'] != 'N/A':
                        date_to_games[formatted_date].add(projection['gameId'])
                    
                    # Skip to the next projection
                    continue
            
            # For ISO format dates, convert to US Central Time
            # NBA games are typically listed in US Central Time
            # This ensures we get the correct date for the game
            
            # Format the date as YYYYMMDD
            formatted_date = start_time.strftime("%Y%m%d")
            
            # Debug the first few projections
            if len(unique_dates) < 3:
                print(f"  ISO format - Raw: {start_time_str}")
                print(f"  ISO format - Parsed: {start_time}")
                print(f"  ISO format - Formatted: {formatted_date}")
            
            unique_dates.add(formatted_date)
            
            # Also add the previous day to handle timezone differences
            # This ensures we don't miss games due to timezone conversion
            prev_day = (start_time - timedelta(days=1)).strftime("%Y%m%d")
            unique_dates.add(prev_day)
            
            # Store game ID for both dates to ensure matching
            if projection['gameId'] != 'N/A':
                date_to_games[formatted_date].add(projection['gameId'])
                date_to_games[prev_day].add(projection['gameId'])
                
                # Store team abbreviation to game ID mapping
                if 'team' in projection and projection['team']:
                    team_abbr = projection['team'].upper()
                    team_to_game_id[team_abbr] = projection['gameId']
                    
                    # Store both teams for each game
                    if projection['gameId'] not in game_teams:
                        game_teams[projection['gameId']] = set()
                    game_teams[projection['gameId']].add(team_abbr)
                
        except Exception as e:
            print(f"Error parsing date '{start_time_str}': {str(e)}")
            # Use today's date as a fallback
            if projection['gameId'] != 'N/A':
                date_to_games[today_date].add(projection['gameId'])
    
    print(f"Found {len(unique_dates)} unique dates in projections.")
    print(f"Game IDs in our database: {', '.join(list(date_to_games.get(list(unique_dates)[0], set()))[:5])}...")
    
    # First, test the API with today's date to see the response format
    test_date = today_date
    print(f"\nTesting API with today's date: {test_date}")
    
    test_response = fetch_game_odds(test_date)
    if test_response:
        print("\nAPI Response Format:")
        print(json.dumps(test_response, indent=2)[:1000] + "...")
        
        # Now fetch and process odds for each unique date
        print("\n" + "=" * 50)
        print("FETCHING ODDS FOR ALL UNIQUE DATES")
        print("=" * 50)
        
        for game_date in unique_dates:
            print(f"\nProcessing date: {game_date}")
            odds_response = fetch_game_odds(game_date)
            
            if not odds_response or odds_response.get('statusCode') != 200:
                print(f"No odds data available for {game_date}")
                continue
            
            games_data = odds_response.get('body', {})
            
            # Check if there's an error message
            if odds_response.get('error'):
                print(f"API Error for {game_date}: {odds_response.get('error')}")
                
            if not games_data:
                print(f"No games found for {game_date}")
                continue
            
            print(f"Found {len(games_data)} games with odds data:")
            
            # Print information about the teams we have in our database
            print(f"Looking for matches between API games and our database games:")
            print(f"Teams in our database: {', '.join(list(team_to_game_id.keys())[:10])}...")
            print(f"Games with multiple teams: {sum(1 for teams in game_teams.values() if len(teams) > 1)}")
            
            # Sort games to show games with projections first
            sorted_games = []
            for game_id, game_info in games_data.items():
                # Extract team information for better matching
                home_team = game_info.get('homeTeam', '')
                away_team = game_info.get('awayTeam', '')
                
                # Check if any of our database teams match this game
                has_projections, matched_game_id = map_game_ids(game_id, team_to_game_id, game_teams)
                
                # Print debug info for each API game
                print(f"API Game: {game_id} ({away_team} @ {home_team}) - Has projections: {has_projections}")
                if has_projections:
                    print(f"  Matched with database game ID: {matched_game_id}")
                    print(f"  Teams in database game: {', '.join(game_teams.get(matched_game_id, []))}")
                    
                    # Update projections with odds data
                    update_projections_with_odds(matched_game_id, game_info, game_id)
                
                sorted_games.append((game_id, game_info, has_projections, matched_game_id if has_projections else None))
            
            # Sort by has_projections (True first)
            sorted_games.sort(key=lambda x: (not x[2], x[0]))
            
            for game_id, game_info, has_projections, matched_db_id in sorted_games:
                # Extract team information
                home_team = game_info.get('homeTeam')
                away_team = game_info.get('awayTeam')
                
                # Get a bookmaker to use for odds (using DraftKings as default if available)
                bookmaker = None
                for bookie in ['draftkings', 'fanduel', 'betmgm', 'caesars_sportsbook']:
                    if bookie in game_info:
                        bookmaker = bookie
                        break
                
                if not bookmaker:
                    print(f"\nGame ID: {game_id}")
                    print(f"Matchup: {away_team} @ {home_team}")
                    print("No odds data available for this game")
                    print("-" * 40)
                    continue
                
                # Get odds from the selected bookmaker
                odds_data = game_info.get(bookmaker, {})
                
                # Get moneyline odds
                home_ml = odds_data.get('homeTeamMLOdds', 'N/A')
                away_ml = odds_data.get('awayTeamMLOdds', 'N/A')
                
                # Get spread odds
                home_spread = odds_data.get('homeTeamSpread', 'N/A')
                home_spread_odds = odds_data.get('homeTeamSpreadOdds', 'N/A')
                away_spread = odds_data.get('awayTeamSpread', 'N/A')
                away_spread_odds = odds_data.get('awayTeamSpreadOdds', 'N/A')
                
                # Get total (over/under)
                total_over = odds_data.get('totalOver', 'N/A')
                over_odds = odds_data.get('totalOverOdds', 'N/A')
                under_odds = odds_data.get('totalUnderOdds', 'N/A')
                
                projection_marker = "[HAS PROJECTIONS] " if has_projections else ""
                
                print(f"\n{projection_marker}Game ID: {game_id}")
                print(f"Matchup: {away_team} @ {home_team}")
                print(f"Odds Source: {bookmaker.capitalize()}")
                print(f"Moneyline: {away_team} {away_ml} | {home_team} {home_ml}")
                print(f"Spread: {away_team} {away_spread} ({away_spread_odds}) | {home_team} {home_spread} ({home_spread_odds})")
                print(f"Total: {total_over} (Over: {over_odds}, Under: {under_odds})")
                print("-" * 40)
            
            # Print a summary of the date's games
            games_with_projections = sum(1 for _, _, has_proj, _ in sorted_games if has_proj)
            print(f"\nSummary for {game_date}: {games_with_projections} of {len(games_data)} games have projections in our database")
            
            if games_with_projections > 0:
                print("Successfully updated projections with odds data!")
    else:
        print("Failed to test API. Please check your API key and connection.")
    
except json.JSONDecodeError:
    print(f"Error parsing JSON output: {result.stdout}")
    exit(1)
except Exception as e:
    logging.error(f"Error processing projections: {str(e)}")
    exit(1)