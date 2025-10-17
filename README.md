# QE2 - Racing Data Analysis Platform

A comprehensive platform for collecting, storing, and analyzing horse racing data using The Racing API.

## Overview

This project provides tools and infrastructure for:
- Fetching historical and real-time racing data from The Racing API
- Storing data in SQLite databases with optimized schemas
- Processing and analyzing racing statistics
- Building predictive models for racing outcomes

## Features

- **API Integration**: Seamless connection to The Racing API with rate limiting and error handling
- **Database Management**: SQLite-based storage with optimized schemas for races and runners
- **Data Processing**: Comprehensive data cleaning and transformation pipelines
- **Historical Data**: Bulk collection of historical racing results
- **Real-time Updates**: Incremental data updates to keep database current
- **Error Handling**: Robust error handling with retry mechanisms and logging

## Project Structure

```
QE2/
├── Datafetch/                 # Data collection and processing
│   ├── data_pull.ipynb       # Main data collection notebook
│   ├── data_pull_db.ipynb    # Database-focused data collection
│   ├── csv_exports/          # Exported CSV files
│   ├── reqd_files/           # Configuration files (credentials)
│   └── racing_data.db        # SQLite database (generated)
├── venv/                     # Python virtual environment
├── requirements.txt          # Python dependencies
├── .gitignore               # Git ignore rules
└── README.md                # This file
```

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/darcy5d/QE2.git
cd QE2
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure API Credentials

Create a `Datafetch/reqd_files/cred.txt` file with your The Racing API credentials:
```
your_username
your_password
```

**⚠️ IMPORTANT**: Never commit this file to version control. It's already included in `.gitignore`.

## Usage

### Basic API Connection Test

```python
# Run the test in data_pull_db.ipynb
# This will verify your API credentials and fetch course data
```

### Data Collection

The project includes two main approaches:

1. **CSV-based Collection** (`data_pull.ipynb`):
   - Collects data and exports to CSV files
   - Good for one-time bulk downloads
   - Includes sampling and error handling

2. **Database Collection** (`data_pull_db.ipynb`):
   - Stores data directly in SQLite database
   - Optimized for incremental updates
   - Better for ongoing data collection

### Database Schema

The SQLite database includes two main tables:

- **races**: Race-level information (date, course, conditions, etc.)
- **runners**: Individual horse/runner data (position, odds, jockey, etc.)

## API Endpoints Used

- `/v1/courses` - Course information
- `/v1/results` - Historical race results
- `/v1/racecards/pro` - Professional racecards

## Rate Limiting

The API client includes built-in rate limiting (0.69s between requests) to respect The Racing API's limits.

## Error Handling

- Automatic retry with exponential backoff for 503 errors
- Comprehensive logging of errors and progress
- Graceful handling of missing data dates
- Transaction-based database operations

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## API Documentation

The project uses The Racing API. For detailed API documentation, see the provided `openapi.json` file.

## Security Notes

- API credentials are stored locally and never committed to version control
- Database files may contain sensitive racing data
- Ensure proper access controls for production deployments

## Support

For issues related to:
- **API Access**: Contact The Racing API support
- **Code Issues**: Open an issue in this repository
- **Data Questions**: Check the API documentation or contact the maintainer
