// Script to delete old projections from the database using Prisma
const { PrismaClient } = require('@prisma/client');

// Initialize Prisma client
const prisma = new PrismaClient();

async function deleteOldProjections() {
  try {
    // Get current time
    const currentTime = new Date();
    
    console.log(`Deleting projections with start time before ${currentTime.toISOString()}`);
    
    // Delete projections where startTime is in the past
    const result = await prisma.projection.deleteMany({
      where: {
        startTime: {
          lt: currentTime
        }
      }
    });
    
    console.log(`Successfully deleted ${result.count} old projections`);
    
    // Return the result as JSON
    console.log(JSON.stringify({ success: true, deletedCount: result.count }));
    
  } catch (error) {
    console.error('Error deleting old projections:', error);
    console.log(JSON.stringify({ success: false, error: error.message }));
    process.exit(1);
  } finally {
    // Disconnect from the database
    await prisma.$disconnect();
  }
}

// Run the function
deleteOldProjections()
  .catch(e => {
    console.error(e);
    process.exit(1);
  });
