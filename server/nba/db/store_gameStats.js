// Script to store NBA game stats in the database using Prisma
const { PrismaClient } = require('@prisma/client');
const fs = require('fs');
const path = require('path');

// Initialize Prisma client
const prisma = new PrismaClient();

async function storeGameStats() {
  try {
    // Get the file path from command line arguments
    const filePath = process.argv[2];
    
    if (!filePath) {
      console.error('No file path provided');
      process.exit(1);
    }
    
    // Read the JSON file
    const rawData = fs.readFileSync(filePath, 'utf8');
    const gameStatsData = JSON.parse(rawData);
    
    // Extract player ID and game stats
    const playerId = gameStatsData.playerId;
    const games = gameStatsData.games;
    
    console.log(`Processing ${Object.keys(games).length} games for player ID: ${playerId}`);
    
    // Store each game stat in the database
    const results = await Promise.all(
      Object.entries(games).map(async ([gameId, gameStat]) => {
        try {
          // Convert string values to numbers where needed
          const gameStatData = {
            gameId: gameId,
            playerId: playerId,
            playerName: gameStat.longName,
            team: gameStat.team,
            teamAbbreviation: gameStat.teamAbv,
            teamId: gameStat.teamID,
            // New fields for game information
            gameDate: new Date(gameStat.game_date),
            opponent: gameStat.opponent,
            isHome: gameStat.is_home,
            points: parseFloat(gameStat.pts),
            rebounds: parseFloat(gameStat.reb),
            offensiveRebounds: parseFloat(gameStat.OffReb),
            defensiveRebounds: parseFloat(gameStat.DefReb),
            assists: parseFloat(gameStat.ast),
            steals: parseFloat(gameStat.stl),
            blocks: parseFloat(gameStat.blk),
            turnovers: parseFloat(gameStat.TOV),
            personalFouls: parseFloat(gameStat.PF),
            technicalFouls: parseFloat(gameStat.tech),
            plusMinus: gameStat.plusMinus,
            minutesPlayed: gameStat.mins,
            fieldGoalsMade: parseFloat(gameStat.fgm),
            fieldGoalsAttempted: parseFloat(gameStat.fga),
            fieldGoalPercentage: gameStat.fgp,
            threePointersMade: parseFloat(gameStat.tptfgm),
            threePointersAttempted: parseFloat(gameStat.tptfga),
            threePointPercentage: gameStat.tptfgp,
            freeThrowsMade: parseFloat(gameStat.ftm),
            freeThrowsAttempted: parseFloat(gameStat.fta),
            freeThrowPercentage: gameStat.ftp,
            fantasyPoints: gameStat.fantasyPoints
          };
          
          // Create or update the game stat in the database
          const result = await prisma.nbaGameStats.upsert({
            where: { 
              gameId_playerId: {
                gameId: gameId,
                playerId: playerId
              }
            },
            update: gameStatData,
            create: {
              ...gameStatData,
              id: `${gameId}_${playerId}`
            }
          });
          
          return { success: true, gameId: gameId };
        } catch (error) {
          console.error(`Error storing game stats for game ${gameId}:`, error);
          return { success: false, error: error.message, gameId: gameId };
        }
      })
    );
    
    // Count successful operations
    const successCount = results.filter(r => r.success).length;
    console.log(`Successfully stored ${successCount} out of ${Object.keys(games).length} games for player ID: ${playerId}`);
    
    // Log any errors
    const errors = results.filter(r => !r.success);
    if (errors.length > 0) {
      console.log(`Failed to store ${errors.length} games:`);
      errors.forEach(e => console.log(`- Game ${e.gameId}: ${e.error}`));
    }
    
  } catch (error) {
    console.error('Error processing game stats:', error);
    process.exit(1);
  } finally {
    // Disconnect from the database
    await prisma.$disconnect();
  }
}

// Run the function
storeGameStats()
  .catch(e => {
    console.error(e);
    process.exit(1);
  });
