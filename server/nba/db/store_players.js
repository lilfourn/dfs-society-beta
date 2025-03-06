// Script to store NBA players in the database using Prisma
const { PrismaClient } = require('@prisma/client');
const fs = require('fs');
const path = require('path');

// Initialize Prisma client
const prisma = new PrismaClient();

async function storePlayers() {
  try {
    // Get the file path from command line arguments
    const filePath = process.argv[2];
    
    if (!filePath) {
      console.error('No file path provided');
      process.exit(1);
    }
    
    // Read the JSON file
    const rawData = fs.readFileSync(filePath, 'utf8');
    const players = JSON.parse(rawData);
    
    console.log(`Processing ${players.length} NBA players...`);
    
    // Store each player in the database
    const results = await Promise.all(
      players.map(async (player) => {
        try {
          // Create or update the player in the database
          const result = await prisma.nbaPlayer.upsert({
            where: { 
              playerID: player.playerID 
            },
            update: {
              position: player.position,
              team: player.team,
              playerName: player.playerName,
              teamID: player.teamID
            },
            create: {
              playerID: player.playerID,
              position: player.position,
              team: player.team,
              playerName: player.playerName,
              teamID: player.teamID
            }
          });
          
          return { success: true, id: player.playerID };
        } catch (error) {
          console.error(`Error storing player ${player.playerName}:`, error);
          return { success: false, error: error.message, player: player.playerName };
        }
      })
    );
    
    // Count successful operations
    const successCount = results.filter(r => r.success).length;
    console.log(`Successfully stored ${successCount} out of ${players.length} NBA players`);
    
    // Log any errors
    const errors = results.filter(r => !r.success);
    if (errors.length > 0) {
      console.log(`Failed to store ${errors.length} players:`);
      errors.forEach(e => console.log(`- Player ${e.player}: ${e.error}`));
    }
    
  } catch (error) {
    console.error('Error processing players:', error);
    process.exit(1);
  } finally {
    // Disconnect from the database
    await prisma.$disconnect();
  }
}

// Run the function
storePlayers()
  .catch(e => {
    console.error(e);
    process.exit(1);
  });
