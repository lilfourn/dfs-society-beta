// Script to query projections from the database
const prisma = require('../../../db');

// Helper function to format date in the original timezone
function formatDateInOriginalTimezone(date) {
  if (!date) return 'Unknown';
  
  // Convert the UTC date back to the original timezone (US Central Time, -05:00)
  // This ensures we display the date as it was in the original API response
  const utcDate = new Date(date);
  
  // Get the date in the original timezone (US Central Time)
  // We know the games are in US Central Time (-05:00 or -06:00 depending on DST)
  // For NBA games, we want to show the date when the game is played in the US
  
  // Create a formatter that will use the US Central timezone
  const options = { 
    timeZone: 'America/Chicago',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  };
  
  // Format the date in US Central Time
  const formatter = new Intl.DateTimeFormat('en-US', options);
  const formattedDate = formatter.format(utcDate);
  
  // Convert MM/DD/YYYY to YYYY-MM-DD
  const [month, day, year] = formattedDate.split('/');
  return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
}

async function getProjections() {
  try {
    const projections = await prisma.projection.findMany({
      select: {
        projectionId: true,
        playerName: true,
        startTime: true,
        gameId: true,
        team: true,
        opponent: true
      }
    });
    
    // Print some debug information before returning the full JSON
    console.error(`Found ${projections.length} projections`);
    
    if (projections.length > 0) {
      // Group projections by gameId
      const gameIdMap = {};
      projections.forEach(proj => {
        if (!gameIdMap[proj.gameId]) {
          gameIdMap[proj.gameId] = [];
        }
        gameIdMap[proj.gameId].push(proj);
      });
      
      console.error('Game IDs in projections:');
      Object.keys(gameIdMap).forEach(gameId => {
        const count = gameIdMap[gameId].length;
        const sample = gameIdMap[gameId][0];
        
        // Use our helper function to get the date in the original timezone
        const gameDate = formatDateInOriginalTimezone(sample.startTime);
        
        // Also show the raw UTC date for comparison
        const utcDate = new Date(sample.startTime).toISOString().split('T')[0];
        
        console.error(`- ${gameId} (${count} projections) - Teams: ${sample.team} vs ${sample.opponent}, Date: ${gameDate} (UTC: ${utcDate})`);
        
        // Debug the first few games
        if (Object.keys(gameIdMap).indexOf(gameId) < 2) {
          console.error(`  Debug - Raw startTime: ${sample.startTime}`);
          console.error(`  Debug - Formatted in original timezone: ${gameDate}`);
          console.error(`  Debug - UTC date: ${utcDate}`);
        }
      });
    }
    
    // Output the full JSON for the Python script to parse
    console.log(JSON.stringify(projections));
    return projections;
  } catch (error) {
    console.error('Error querying projections:', error);
    process.exit(1);
  } finally {
    await prisma.$disconnect();
  }
}

// Execute if called directly
if (require.main === module) {
  getProjections();
}

module.exports = { getProjections };
