# DFS Society: Advanced Sports Analytics Platform

<p align="center">
  <img src="public/DFS SOCIETY.png" alt="DFS Society Logo" width="300"/>
</p>

## Overview

DFS Society is a sophisticated sports analytics platform that leverages machine learning and statistical analysis to predict athlete performance in professional sports, with a primary focus on the NBA. The platform integrates real-time data from multiple sources, including injury reports, game odds, and historical player statistics, to provide accurate projections for sports betting and daily fantasy sports (DFS) optimization.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Next.js](https://img.shields.io/badge/Next.js-13.0+-000000?logo=next.js)](https://nextjs.org/)
[![Prisma](https://img.shields.io/badge/Prisma-4.0+-2D3748?logo=prisma)](https://www.prisma.io/)
[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white)](https://www.python.org/)

## Key Features

- **Real-time NBA Injury Tracking**: Automated pipeline for fetching and analyzing player injury data
- **Game Odds Integration**: Comprehensive collection and analysis of betting lines from major sportsbooks
- **Player Performance Projections**: Statistical models for predicting player performance metrics
- **Historical Data Analysis**: Extensive database of player statistics for trend analysis
- **Secure API Integration**: Environment-based credential management for multiple data providers
- **Cross-language Architecture**: Seamless integration between Python data processing and JavaScript/TypeScript web interface

## System Architecture

DFS Society employs a modern, scalable architecture:

```
├── Frontend (Next.js)
│   ├── React Components
│   ├── TypeScript
│   └── Tailwind CSS
│
├── Backend
│   ├── Data Collection (Python)
│   │   ├── API Integrations
│   │   └── Statistical Processing
│   │
│   ├── Database (PostgreSQL)
│   │   ├── Player Information
│   │   ├── Game Statistics
│   │   ├── Projections
│   │   └── Injury Reports
│   │
│   └── ORM (Prisma)
```

## Data Pipeline

The system's data pipeline consists of several interconnected modules:

1. **Data Acquisition**: Automated scripts fetch data from multiple sources including:
   - Tank01 Fantasy Stats API for player information and injury data
   - PrizePicks API for player projections
   - Various sportsbooks for game odds and betting lines

2. **Data Processing**: Raw data undergoes cleaning, normalization, and enrichment:
   - Player identification and matching across data sources
   - Statistical calculations and trend analysis
   - Injury impact assessment on projections

3. **Data Storage**: Processed data is stored in a PostgreSQL database using Prisma ORM:
   - Structured schema for players, games, projections, and injuries
   - Efficient indexing for rapid query performance
   - Relationship mapping between entities

4. **Data Presentation**: Processed insights are presented through a Next.js web interface

## Technical Implementation

### Backend Components

- **NBA Player Data Pipeline**: Collects and processes player information
- **Game Statistics Module**: Tracks and analyzes player performance metrics
- **Projection System**: Generates performance predictions based on historical data
- **Injury Tracking System**: Monitors player health status and potential impacts
- **Game Odds Integration**: Incorporates betting market data for additional context

### Database Schema

The PostgreSQL database uses a normalized schema with the following key models:

- **NbaPlayer**: Core player information including position, team, and identifiers
- **NbaGameStats**: Comprehensive game-by-game statistics for each player
- **Projection**: Performance projections with associated game context and odds

### Security Features

- Environment-based credential management for all API integrations
- Secure database connection handling
- Input validation and sanitization throughout the data pipeline

## Getting Started

### Prerequisites

- Node.js (v16+)
- Python (v3.8+)
- PostgreSQL database

### Environment Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/dfs-society.git
   cd dfs-society
   ```

2. Install dependencies:
   ```bash
   # Install Node.js dependencies
   yarn install
   
   # Install Python dependencies
   pip3 install -r requirements.txt
   ```

3. Configure environment variables:
   Create a `.env` file with the following variables:
   ```
   DATABASE_URL="postgresql://username:password@localhost:5432/dfs_society"
   RAPIDAPI_KEY="your_rapidapi_key"
   RAPIDAPI_HOST="tank01-fantasy-stats.p.rapidapi.com"
   ```

4. Initialize the database:
   ```bash
   npx prisma migrate dev
   ```

5. Start the development server:
   ```bash
   yarn dev
   ```

6. Open [http://localhost:3000](http://localhost:3000) to view the application

## Data Collection

To populate the database with current NBA data:

```bash
# Fetch player information
python3 server/nba/fetchPlayersList.py

# Fetch player game statistics
python3 server/nba/fetchGameStats.py

# Fetch projections
python3 server/nba/fetchProjections.py

# Fetch injury data
python3 server/utils/nba/connectInj.py
```

## Future Development

- Implementation of advanced machine learning models for projection refinement
- Expansion to additional sports leagues (NFL, MLB, NHL)
- Development of optimization algorithms for lineup construction
- Integration of player news and social media sentiment analysis
- Mobile application development

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Next.js](https://nextjs.org) for the frontend framework
- [Prisma](https://www.prisma.io/) for database ORM
- [Tank01 Fantasy Stats](https://rapidapi.com/tank01/api/tank01-fantasy-stats/) for sports data
- [PrizePicks](https://prizepicks.com/) for projection data

