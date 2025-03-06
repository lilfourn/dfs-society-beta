// Script to update projections with game odds data
const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

/**
 * Update projections with game odds data
 * @param {string} gameId - The database game ID
 * @param {Object} oddsData - The odds data to update
 */
async function updateProjectionsWithOdds(gameId, oddsData) {
  try {
    console.error(`Updating projections for game ID: ${gameId}`);
    console.error(`Odds data: ${JSON.stringify(oddsData, null, 2)}`);

    // First check if this game ID exists in our database
    const projections = await prisma.projection.findMany({
      where: {
        gameId: gameId
      }
    });

    if (projections.length === 0) {
      console.log(`No projections found for game ID: ${gameId}`);
      return { success: false, message: 'No projections found for this game ID' };
    }

    // Update all projections for this game with the odds data
    const updateResult = await prisma.projection.updateMany({
      where: {
        gameId: gameId
      },
      data: {
        homeTeam: oddsData.homeTeam,
        awayTeam: oddsData.awayTeam,
        homeSpread: parseFloat(oddsData.homeSpread) || null,
        awaySpread: parseFloat(oddsData.awaySpread) || null,
        totalOver: parseFloat(oddsData.totalOver) || null,
        totalUnder: parseFloat(oddsData.totalUnder) || null,
        homeMoneyline: oddsData.homeMoneyline,
        awayMoneyline: oddsData.awayMoneyline,
        oddsProvider: oddsData.oddsProvider,
        oddsLastUpdated: oddsData.lastUpdated ? new Date(oddsData.lastUpdated * 1000) : new Date()
      }
    });

    console.error(`Updated ${updateResult.count} projections with odds data`);
    return { success: true, count: updateResult.count };
  } catch (error) {
    console.error(`Error updating projections with odds: ${error.message}`);
    return { success: false, error: error.message };
  } finally {
    // Always disconnect from Prisma client
    await prisma.$disconnect();
  }
}

// If this script is called directly from command line
if (require.main === module) {
  // Parse command line arguments
  const args = process.argv.slice(2);
  if (args.length < 2) {
    console.error('Usage: node update_projections_with_odds.js <gameId> <oddsDataJson>');
    process.exit(1);
  }

  const gameId = args[0];
  let oddsData;
  
  try {
    oddsData = JSON.parse(args[1]);
  } catch (error) {
    console.error(`Error parsing odds data JSON: ${error.message}`);
    process.exit(1);
  }

  // Call the update function
  updateProjectionsWithOdds(gameId, oddsData)
    .then(result => {
      console.log(JSON.stringify(result));
      process.exit(result.success ? 0 : 1);
    })
    .catch(error => {
      console.error(`Unhandled error: ${error.message}`);
      process.exit(1);
    });
} else {
  // Export the function if this script is required as a module
  module.exports = { updateProjectionsWithOdds };
}
