import requests
import json
import os
import time
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess
import tqdm
import random
from urllib3.util import Retry
from requests.adapters import HTTPAdapter
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))

# Add the parent directory to the path so we can import from utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.nba.getPlayerIDs import get_player_ids

def parse_game_id(game_id, player_team):
    """
    Parse the game ID to extract date, opponent, and home status
    
    Args:
        game_id (str): Game ID in format "YYYYMMDD_AWAY@HOME"
        player_team (str): The team abbreviation of the player
        
    Returns:
        tuple: (game_date, opponent, is_home)
            - game_date (datetime): The date of the game
            - opponent (str): The opponent team abbreviation
            - is_home (bool): Whether the player's team was home (True) or away (False)
    """
    # Split the game ID to get the date and teams
    date_part, teams_part = game_id.split('_')
    
    # Parse the date
    game_date = datetime.strptime(date_part, '%Y%m%d')
    
    # Parse the teams
    away_team, home_team = teams_part.split('@')
    
    # Determine if the player's team was home or away
    is_home = player_team == home_team
    
    # Determine the opponent
    opponent = home_team if player_team == away_team else away_team
    
    return game_date, opponent, is_home

# API configuration
# Get API credentials from environment variables
API_KEY = os.getenv('RAPIDAPI_KEY')
API_HOST = os.getenv('RAPIDAPI_HOST')

# Check if API credentials are available
if not API_KEY or not API_HOST:
    print("Error: API credentials not found in environment variables")
    print("Please ensure RAPIDAPI_KEY and RAPIDAPI_HOST are set in the .env file")
    exit(1)
    
BASE_URL = "https://tank01-fantasy-stats.p.rapidapi.com/getNBAGamesForPlayer"
SEASON = "2022"

# Fantasy points configuration
FANTASY_POINTS_CONFIG = {
    "fantasyPoints": "true",
    "pts": "1",
    "reb": "1.25",
    "stl": "3",
    "blk": "3",
    "ast": "1.5",
    "TOV": "-1",
    "mins": "0",
    "doubleDouble": "0",
    "tripleDouble": "0",
    "quadDouble": "0"
}

# Configure session with retry mechanism and connection pooling
session = requests.Session()

# Configure retry strategy with exponential backoff
retry_strategy = Retry(
    total=5,  # Maximum number of retries
    backoff_factor=0.5,  # Exponential backoff factor (0.5 means 0.5, 1, 2, 4, 8... seconds between retries)
    status_forcelist=[429, 500, 502, 503, 504],  # Retry on these status codes
    allowed_methods=["GET"],  # Only retry on GET requests
    respect_retry_after_header=True  # Honor Retry-After headers from the server
)

# Apply retry strategy to both HTTP and HTTPS connections
session.mount("http://", HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10))
session.mount("https://", HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10))

# Track request times to implement rate limiting
request_timestamps = []  
# Maximum requests per minute (adjust based on API limits)
MAX_REQUESTS_PER_MINUTE = 60
# Maximum requests per second (adjust based on API limits)
MAX_REQUESTS_PER_SECOND = 5

def fetch_player_game_stats(player_id):
    """
    Fetch game stats for a specific player ID for the 2025 season
    
    Args:
        player_id (str): The player ID to fetch stats for
        
    Returns:
        dict: The JSON response containing the player's game stats
    """
    # Prepare query parameters
    query_params = {"playerID": player_id, "season": SEASON}
    query_params.update(FANTASY_POINTS_CONFIG)
    
    # Prepare headers
    headers = {
        "x-rapidapi-key": API_KEY,
        "x-rapidapi-host": API_HOST,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"  # Add a user agent to appear more like a browser
    }
    
    # Apply rate limiting
    apply_rate_limit()
    
    try:
        # Make the API request using the session for connection pooling
        response = session.get(BASE_URL, headers=headers, params=query_params)
        
        # Track this request for rate limiting
        request_timestamps.append(time.time())
        
        # Handle rate limiting response
        if response.status_code == 429:  # Too Many Requests
            retry_after = int(response.headers.get('Retry-After', 60))  # Default to 60 seconds if header not present
            print(f"Rate limit exceeded for player {player_id}. Waiting {retry_after} seconds...")
            time.sleep(retry_after)
            # Try again after waiting
            return fetch_player_game_stats(player_id)
            
        # Check if the request was successful
        if response.status_code == 200:
            # Add a small random delay to avoid predictable patterns
            time.sleep(random.uniform(0.1, 0.5))
            return response.json()
        else:
            print(f"Request failed with status code {response.status_code} for player {player_id}")
            return None
    except Exception as e:
        print(f"Exception during request for player {player_id}: {str(e)}")
        return None

def process_and_store_player_stats(player_id):
    """
    Fetch, process, and store game stats for a single player
    
    Args:
        player_id (str): The player ID to process
        
    Returns:
        dict: Result of the operation with success status and game count
    """
    try:
        # Fetch stats for this player
        stats = fetch_player_game_stats(player_id)
        
        if stats and 'body' in stats and stats['body']:
            game_count = len(stats['body'])
            
            # Store the game stats in the database
            store_player_game_stats(player_id, stats['body'])
            
            return {
                "success": True,
                "player_id": player_id,
                "game_count": game_count
            }
        else:
            return {
                "success": False,
                "player_id": player_id,
                "game_count": 0,
                "error": "No game stats found"
            }
    except Exception as e:
        return {
            "success": False,
            "player_id": player_id,
            "game_count": 0,
            "error": str(e)
        }

def apply_rate_limit():
    """
    Apply rate limiting to avoid overwhelming the API and getting banned
    """
    now = time.time()
    
    # Clean up old timestamps (older than 60 seconds)
    global request_timestamps
    request_timestamps = [t for t in request_timestamps if now - t < 60]
    
    # Check if we've exceeded the per-minute limit
    if len(request_timestamps) >= MAX_REQUESTS_PER_MINUTE:
        # Calculate how long to wait
        oldest_timestamp = min(request_timestamps)
        wait_time = 60 - (now - oldest_timestamp) + 1  # Add 1 second buffer
        print(f"Rate limit reached: {len(request_timestamps)} requests in the last minute. Waiting {wait_time:.2f} seconds...")
        time.sleep(wait_time)
        # Clean up timestamps again after waiting
        request_timestamps = [t for t in request_timestamps if time.time() - t < 60]
    
    # Check if we've exceeded the per-second limit
    recent_timestamps = [t for t in request_timestamps if now - t < 1]
    if len(recent_timestamps) >= MAX_REQUESTS_PER_SECOND:
        # Calculate how long to wait
        wait_time = 1.0 + random.uniform(0.1, 0.5)  # Add jitter
        print(f"Second-level rate limit reached: {len(recent_timestamps)} requests in the last second. Waiting {wait_time:.2f} seconds...")
        time.sleep(wait_time)

def fetch_all_player_stats_parallel(player_ids, max_workers=5, batch_size=20):
    """
    Fetch game stats for all player IDs in parallel with optimized performance
    
    Args:
        player_ids (list): List of player IDs to fetch stats for
        max_workers (int): Maximum number of parallel workers
        batch_size (int): Size of batches to process to avoid overwhelming the API
        
    Returns:
        dict: Summary of results
    """
    results = {
        "total_players": len(player_ids),
        "successful_players": 0,
        "failed_players": 0,
        "total_games": 0,
        "errors": []
    }
    
    # Create a single progress bar for all players
    print("Progress Legend: b=batch, s=success rate, g=total games, a=avg games per player")
    with tqdm.tqdm(total=len(player_ids), desc="Fetching Game Stats", 
                   unit="player", ncols=100, position=0, leave=True, 
                   dynamic_ncols=True, ascii=True,
                   bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}{postfix}]') as pbar:
        
        # Process players in batches to avoid overwhelming the API
        for i in range(0, len(player_ids), batch_size):
            batch = player_ids[i:i+batch_size]
            
            # Process the batch in parallel
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_player = {executor.submit(process_and_store_player_stats, player_id): player_id 
                                   for player_id in batch}
                
                # Process results as they complete
                for future in as_completed(future_to_player):
                    player_id = future_to_player[future]
                    try:
                        result = future.result()
                        
                        if result["success"]:
                            results["successful_players"] += 1
                            results["total_games"] += result["game_count"]
                        else:
                            results["failed_players"] += 1
                            results["errors"].append({
                                "player_id": player_id,
                                "error": result.get("error", "Unknown error")
                            })
                        
                        # Update the progress bar
                        pbar.update(1)
                        pbar.set_postfix({
                            'b': f"{i//batch_size + 1}/{(len(player_ids)-1)//batch_size + 1}",
                            's': f"{results['successful_players']}/{pbar.n}",
                            'g': results["total_games"],
                            'a': f"{results['total_games']/max(1, results['successful_players']):.1f}"
                        })
                    except Exception as e:
                        results["failed_players"] += 1
                        results["errors"].append({
                            "player_id": player_id,
                            "error": str(e)
                        })
                        pbar.update(1)
            
            # Add a delay between batches to avoid rate limiting
            if i + batch_size < len(player_ids):
                # Calculate a dynamic delay based on the batch size
                delay = min(5, max(2, batch_size / 10))
                # Add some randomness to avoid predictable patterns
                delay += random.uniform(0.5, 2.0)
                print(f"Waiting {delay:.2f} seconds between batches...")
                time.sleep(delay)
    
    return results

def store_player_game_stats(player_id, games):
    """
    Store player game stats in the database using the Node.js script
    
    Args:
        player_id (str): The player ID
        games (dict): Dictionary of game stats for the player
    """
    # Create a data structure to pass to the Node.js script
    processed_games = {}
    
    for game_id, game_stats in games.items():
        # Get the player's team abbreviation from the game stats
        player_team = game_stats.get('teamAbv')
        
        # Parse the game ID to get date, opponent, and home status
        game_date, opponent, is_home = parse_game_id(game_id, player_team)
        
        # Add the parsed information to the game stats
        game_stats_with_parsed_info = game_stats.copy()
        game_stats_with_parsed_info['game_date'] = game_date.isoformat()
        game_stats_with_parsed_info['opponent'] = opponent
        game_stats_with_parsed_info['is_home'] = is_home
        
        # Add to processed games
        processed_games[game_id] = game_stats_with_parsed_info
    
    data = {
        "playerId": player_id,
        "games": processed_games
    }
    
    # Create a temporary file to store the game stats data
    temp_file = os.path.join(os.path.dirname(__file__), f'temp_game_stats_{player_id}.json')
    with open(temp_file, 'w') as f:
        json.dump(data, f)
    
    try:
        # Call the Node.js script to store game stats in the database
        script_path = os.path.join(os.path.dirname(__file__), 'db', 'store_gameStats.js')
        result = subprocess.run(['node', script_path, temp_file], capture_output=True, text=True)
        
        # We don't need to print output for each player to keep the progress bar clean
        if result.stderr:
            print(f"Error storing game stats for player ID {player_id}: {result.stderr}")
    except Exception as e:
        print(f"Error storing game stats for player ID {player_id}: {e}")
    finally:
        # Remove the temporary file
        if os.path.exists(temp_file):
            os.remove(temp_file)

def save_game_stats(stats, output_dir):
    """
    Save game stats to JSON files
    
    Args:
        stats (dict): Dictionary mapping player IDs to their game stats
        output_dir (str): Directory to save the JSON files
    """
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Save each player's stats to a separate file
    for player_id, player_stats in stats.items():
        output_file = os.path.join(output_dir, f"player_{player_id}_stats.json")
        with open(output_file, 'w') as f:
            json.dump(player_stats, f, indent=2)
    
    print(f"Saved stats for {len(stats)} players to {output_dir}")

if __name__ == "__main__":
    # Get all player IDs from the database
    player_ids = get_player_ids()
    
    if not player_ids:
        print("No player IDs found in the database")
        sys.exit(1)
    
    print(f"Found {len(player_ids)} players in the database")
    
    # For testing, just fetch stats for one player
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_player_id = player_ids[0]
        print(f"Testing with player ID: {test_player_id}")
        
        # Fetch stats for the test player
        player_stats = fetch_player_game_stats(test_player_id)
        
        if player_stats and 'body' in player_stats and player_stats['body']:
            print("Sample game stats for one player:")
            print(json.dumps(player_stats, indent=2))
            
            # Store the game stats in the database
            store_player_game_stats(test_player_id, player_stats['body'])
            
            # The body contains a dictionary of games with game IDs as keys
            game_count = len(player_stats['body'])
            print(f"\nFound {game_count} games for this player")
            
            # Print details of the first game
            if game_count > 0:
                # Get the first game ID
                first_game_id = list(player_stats['body'].keys())[0]
                first_game = player_stats['body'][first_game_id]
                print(f"\nDetails of first game (ID: {first_game_id}):")
                print(json.dumps(first_game, indent=2))
        else:
            print("No game stats found for this player")
    # Test with a small batch of players
    elif len(sys.argv) > 1 and sys.argv[1] == "--small-batch":
        # Take just 10 players for a quick test
        small_batch = player_ids[:10]
        print(f"Testing with a small batch of {len(small_batch)} players")
        
        # Configure the parallel processing with more conservative values for testing
        max_workers = 2  # Use fewer workers for the small batch test
        batch_size = 5   # Process players in smaller batches
        
        # Start the parallel processing with progress bar
        start_time = time.time()
        results = fetch_all_player_stats_parallel(small_batch, max_workers=max_workers, batch_size=batch_size)
        end_time = time.time()
        
        # Print summary
        print("\nSummary:")
        print(f"Total players processed: {results['total_players']}")
        print(f"Successful players: {results['successful_players']}")
        print(f"Failed players: {results['failed_players']}")
        print(f"Total games stored: {results['total_games']}")
        print(f"Total time: {end_time - start_time:.2f} seconds")
    else:
        # Process all players with optimized parallel processing
        print("Fetching game stats for all players...")
        
        # Configure the parallel processing with more conservative values
        max_workers = 3  # Reduced number of workers to limit concurrent connections
        batch_size = 15  # Smaller batch size to avoid overwhelming the API
        
        # Start the parallel processing with progress bar
        start_time = time.time()
        results = fetch_all_player_stats_parallel(player_ids, max_workers=max_workers, batch_size=batch_size)
        end_time = time.time()
        
        # Print summary
        print("\nSummary:")
        print(f"Total players processed: {results['total_players']}")
        print(f"Successful players: {results['successful_players']}")
        print(f"Failed players: {results['failed_players']}")
        print(f"Total games stored: {results['total_games']}")
        print(f"Total time: {end_time - start_time:.2f} seconds")
        
        # Print errors if any
        if results['errors']:
            print(f"\nErrors ({len(results['errors'])} players):")
            for error in results['errors'][:10]:  # Show only first 10 errors to avoid cluttering the output
                print(f"- Player {error['player_id']}: {error['error']}")
            
            if len(results['errors']) > 10:
                print(f"... and {len(results['errors']) - 10} more errors")