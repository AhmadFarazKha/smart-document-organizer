# Smart Document Organizer

## Overview

A web application that integrates with Google Drive to help you organize and search your documents efficiently.

## Prerequisites

* Python 3.8+
* Google Cloud Project with Drive API enabled
* Google API credentials

## Setup Instructions

1. Clone the repository
2. Create a virtual environment
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
3. Install dependencies
   ```
   pip install -r requirements.txt
   ```
4. Google Drive API Setup
   * Go to Google Cloud Console
   * Create a new project
   * Enable Google Drive API
   * Create OAuth 2.0 credentials
   * Download `credentials.json` and place in project root
5. Create `.env` file with your Google API key
6. Run the application
   ```
   python app.py
   ```

## Features

* List recent Google Drive documents
* Search documents by name
* Responsive web interface

## Technologies

* Flask
* Google Drive API
* JavaScript
* HTML5
* CSS3
