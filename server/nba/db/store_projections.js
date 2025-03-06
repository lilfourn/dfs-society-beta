// Script to store projections in the database using Prisma
const { PrismaClient } = require('@prisma/client');
const fs = require('fs');
const path = require('path');

// Add a helper function to parse ISO dates with timezone preservation
function parseISODatePreservingTimezone(isoString) {
  // This function takes an ISO date string with timezone info
  // and returns a Date object that preserves the original date
  // regardless of the local timezone of the server
  
  if (!isoString) return new Date();
  
  try {
    // Parse the components from the ISO string
    // Format: YYYY-MM-DDTHH:MM:SS+/-HH:MM
    const match = isoString.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})([+-]\d{2}:\d{2})$/);
    
    if (!match) {
      console.warn(`Warning: Date string doesn't match expected format: ${isoString}`);
      return new Date(isoString);
    }
    
    // Extract the timezone offset
    const [_, year, month, day, hour, minute, second, tzOffset] = match;
    
    // Parse the timezone offset (e.g., "-05:00" -> -300 minutes)
    const tzSign = tzOffset.charAt(0) === '-' ? -1 : 1;
    const tzHours = parseInt(tzOffset.substring(1, 3), 10);
    const tzMinutes = parseInt(tzOffset.substring(4, 6), 10);
    const tzOffsetMinutes = tzSign * (tzHours * 60 + tzMinutes);
    
    // Create a UTC date by adjusting for the timezone
    // This ensures the date is stored correctly in the database
    const date = new Date(Date.UTC(
      parseInt(year, 10),
      parseInt(month, 10) - 1, // Month is 0-indexed
      parseInt(day, 10),
      parseInt(hour, 10),
      parseInt(minute, 10),
      parseInt(second, 10)
    ));
    
    // Adjust for the timezone offset
    // This is the key step that ensures the date is preserved
    date.setUTCMinutes(date.getUTCMinutes() - tzOffsetMinutes);
    
    return date;
  } catch (error) {
    console.error(`Error parsing ISO date: ${error.message}`);
    return new Date(isoString);
  }
}

// Initialize Prisma client
const prisma = new PrismaClient();

async function storeProjections() {
  try {
    // Get the file path from command line arguments
    const filePath = process.argv[2];
    
    if (!filePath) {
      console.error('No file path provided');
      process.exit(1);
    }
    
    // Read the JSON file
    const rawData = fs.readFileSync(filePath, 'utf8');
    const projections = JSON.parse(rawData);
    
    console.log(`Processing ${projections.length} projections...`);
    
    // Store each projection in the database
    const results = await Promise.all(
      projections.map(async (projection) => {
        try {
          // Parse the startTime string to a Date object
          // We need to handle the timezone correctly to avoid date shifting
          const rawStartTime = projection.startTime;
          
          // Use our custom function to parse the date while preserving timezone
          // This ensures the date is stored correctly regardless of the server's timezone
          const parsedStartTime = parseISODatePreservingTimezone(rawStartTime);
          
          // Debug the first few projections
          if (projections.indexOf(projection) < 3) {
            // Extract the original date components for debugging
            const originalDate = rawStartTime.split('T')[0];
            const originalTime = rawStartTime.split('T')[1];
            
            console.log(`Debug - ID: ${projection.projectionId}, Game: ${projection.gameId}`);
            console.log(`Debug - Raw startTime: ${rawStartTime}`);
            console.log(`Debug - Original date: ${originalDate}`);
            console.log(`Debug - Original time: ${originalTime}`);
            console.log(`Debug - Parsed date object: ${parsedStartTime.toISOString()}`);
            console.log(`Debug - Parsed local date: ${parsedStartTime.toLocaleString()}`);
            
            // Verify the date is preserved correctly
            const parsedYear = parsedStartTime.getUTCFullYear();
            const parsedMonth = (parsedStartTime.getUTCMonth() + 1).toString().padStart(2, '0');
            const parsedDay = parsedStartTime.getUTCDate().toString().padStart(2, '0');
            const parsedDateStr = `${parsedYear}-${parsedMonth}-${parsedDay}`;
            
            console.log(`Debug - UTC date components: ${parsedYear}-${parsedMonth}-${parsedDay}`);
            console.log(`Debug - Original date matches parsed date: ${originalDate === parsedDateStr}`);
          }
          
          const result = await prisma.projection.upsert({
            where: { 
              projectionId: projection.projectionId 
            },
            update: {
              playerName: projection.playerName,
              team: projection.team,
              position: projection.position,
              statType: projection.statType,
              lineScore: projection.lineScore,
              average: projection.average,
              maxValue: projection.maxValue,
              gameId: projection.gameId,
              startTime: parsedStartTime,
              status: projection.status,
              opponent: projection.description,
              imageUrl: projection.imageUrl,
              oddsType: projection.oddsType
            },
            create: {
              projectionId: projection.projectionId,
              playerName: projection.playerName,
              team: projection.team,
              position: projection.position,
              statType: projection.statType,
              lineScore: projection.lineScore,
              average: projection.average,
              maxValue: projection.maxValue,
              gameId: projection.gameId,
              startTime: parsedStartTime,
              status: projection.status,
              opponent: projection.description,
              imageUrl: projection.imageUrl,
              oddsType: projection.oddsType
            }
          });
          
          return { success: true, id: projection.projectionId };
        } catch (error) {
          console.error(`Error storing projection ${projection.projectionId}:`, error);
          return { success: false, error: error.message, projection: projection.projectionId };
        }
      })
    );
    
    // Count successful operations
    const successCount = results.filter(r => r.success).length;
    console.log(`Successfully stored ${successCount} out of ${projections.length} projections`);
    
    // Log any errors
    const errors = results.filter(r => !r.success);
    if (errors.length > 0) {
      console.log(`Failed to store ${errors.length} projections:`);
      errors.forEach(e => console.log(`- Projection ${e.projection}: ${e.error}`));
    }
    
  } catch (error) {
    console.error('Error processing projections:', error);
    process.exit(1);
  } finally {
    // Disconnect from the database
    await prisma.$disconnect();
  }
}

// Run the function
storeProjections()
  .catch(e => {
    console.error(e);
    process.exit(1);
  });
