# AI Jefit Data Cleaner
This repository uses Google's Gemini AI to automatically read, untangle, and clean messy Jefit workout exports.
## How to use it:
 1. Upload your messy Jefit .csv file into the input/ folder.
 2. Wait about 1-2 minutes. GitHub Actions runs automatically in the background.
 3. Open the output/ folder and download Cleaned_Jefit_Data.csv.
## Setup (For Repository Owner)
To make this work, you must add a free Gemini API key to this repository:
 1. Get a free API key from Google AI Studio.
 2. Go to your GitHub repository **Settings**.
 3. On the left menu, go to **Secrets and variables** -> **Actions**.
 4. Click **New repository secret**.
 5. Name: GEMINI_API_KEY
 6. Secret: Paste your API key here.
 7. Click **Add secret**.
 8. 
