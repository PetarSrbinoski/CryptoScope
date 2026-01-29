# Cryptoscope

Welcome to Cryptoscope! This is a cryptocurrency analysis platform that brings together machine learning, blockchain insights, and technical analysis to help you understand and navigate the crypto market better.

## What's This About?

Ever wish you had a crystal ball for crypto prices? While we can't quite guarantee that, Cryptoscope gets pretty close. We use LSTM neural networks to spot trends, monitor on-chain activity for market sentiment, and apply traditional technical analysis to give you trading signals worth paying attention to. It's like having a financial analyst that works 24/7 without needing coffee.

## How It's Built

The platform is split into separate pieces that work together seamlessly:

**Microservices**
- **LSTM Service**: Powers our neural network magic for predicting price movements
- **Technical Service**: Handles all those candlestick patterns and indicators traders love

**Backend** (`tech_prototype/backend/`)
- A collection of REST API endpoints that feed data to the frontend
- An automated pipeline that keeps our data fresh and accurate
- Database management so everything runs smoothly

**Frontend** (`tech_prototype/frontend/`)
- A sleek dashboard where you can watch your favorite coins
- Real-time price updates and signal alerts
- Beautiful charts to visualize market trends

## Features

- 📊 **LSTM Analysis**: Neural network-based trend prediction
- 🔗 **On-Chain Sentiment**: Blockchain activity analysis
- 📈 **Technical Indicators**: Multiple technical analysis tools
- 🎯 **Trading Signals**: Actionable market signals
- 🔄 **Automated Pipeline**: Continuous data collection and updates
- 🌐 **REST API**: Comprehensive API for data access

## Deployment

**Live Demo**: https://cryptoscope-frontend.azurewebsites.net/

The platform is hosted on Microsoft Azure using the Student Plan.

## Getting Started

### Requirements
- Python 3.8+
- Docker & Docker Compose
- PostgreSQL

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment variables in `tech_prototype/backend/core/config.py`
4. Initialize the database:
   ```bash
   python tech_prototype/backend/db/init_db.py
   ```

### Running Locally

```bash
docker-compose up
```

## Project Structure

```
cryptoscope/
├── microservices/          # Independent microservices
│   ├── lstm_ms/           # LSTM analysis service
│   └── technical_ms/      # Technical analysis service
└── tech_prototype/        # Main application
    ├── backend/           # Python FastAPI backend
    │   ├── api/           # Route definitions
    │   ├── pipeline/      # Data processing pipeline
    │   ├── services/      # Business logic
    │   └── db/            # Database management
    └── frontend/          # HTML/CSS/JS frontend
        └── js/            # Client-side logic
```

## Contributing

Contributions are welcome! Please ensure all code follows project conventions and includes appropriate documentation.

## License

This project is part of an academic initiative.
