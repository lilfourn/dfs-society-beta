import subprocess
import json
import os

def get_player_ids():
    """
    Retrieves player IDs from the nba_players database table using Prisma.
    
    Returns:
        list: A list of player IDs from the database
    """
    # Path to the script that will query the database
    script_dir = os.path.dirname(os.path.abspath(__file__))
    temp_script_path = os.path.join(script_dir, 'temp_get_players.js')
    
    # Create a temporary Node.js script to query the database
    with open(temp_script_path, 'w') as f:
        f.write('''
// Script to get player IDs from the database using Prisma
const { PrismaClient } = require('@prisma/client');

// Initialize Prisma client
const prisma = new PrismaClient();

async function getPlayerIDs() {
  try {
    // Query the database for all player IDs
    const players = await prisma.nbaPlayer.findMany({
      select: {
        playerID: true
      }
    });
    
    // Output the result as JSON
    console.log(JSON.stringify(players));
    
  } catch (error) {
    console.error('Error retrieving player IDs:', error);
    process.exit(1);
  } finally {
    // Disconnect from the database
    await prisma.$disconnect();
  }
}

// Run the function
getPlayerIDs()
  .catch(e => {
    console.error(e);
    process.exit(1);
  });
''')
    
    try:
        # Run the Node.js script
        result = subprocess.run(['node', temp_script_path], capture_output=True, text=True)
        
        # Parse the output
        if result.stdout:
            players_data = json.loads(result.stdout)
            player_ids = [player['playerID'] for player in players_data]
            return player_ids
        else:
            print("No output from database query")
            if result.stderr:
                print("Error:", result.stderr)
            return []
            
    except Exception as e:
        print(f"Error retrieving player IDs: {e}")
        return []
    finally:
        # Clean up the temporary script
        if os.path.exists(temp_script_path):
            os.remove(temp_script_path)

# Test the function by printing 5 player IDs
if __name__ == "__main__":
    player_ids = get_player_ids()
    print(f"Total player IDs retrieved: {len(player_ids)}")
    print("Sample of 5 player IDs:")
    for i, player_id in enumerate(player_ids[:5]):
        print(f"{i+1}. {player_id}")