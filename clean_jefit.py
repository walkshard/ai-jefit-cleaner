```python
import os
import glob
import json
import pandas as pd
import google.generativeai as genai

print("Starting AI Jefit Data Cleaner...")

# 1. Setup Gemini API
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY environment variable not set.")
    exit(1)

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

# 2. Find input files
input_files = glob.glob("input/*.csv") + glob.glob("input/*.txt")
if not input_files:
    print("No files found in the 'input' folder.")
    exit(0)

all_records = []

# 3. AI Processing Function
def process_chunk_with_ai(text_chunk):
    prompt = """
    You are a data cleaner. Extract workout data from this messy Jefit export.
    Output MUST be a valid JSON array of objects. 
    Each object must have exactly these keys: "Date" (format YYYY-MM-DD), "Exercise", "Weight", "Reps".
    If a row contains compacted sets (e.g., "135x10, 135x8"), create a separate JSON object for each set.
    Ignore headers, summaries, empty lines, or invalid data. Return ONLY the JSON array.
    """
    try:
        response = model.generate_content(
            f"{prompt}\n\nData:\n{text_chunk}",
            generation_config=genai.GenerationConfig(response_mime_type="application/json")
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"AI Chunk processing failed: {e}")
        return []

# 4. Read and Chunk Data
for file_path in input_files:
    print(f"Processing {file_path}...")
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    # Process in chunks of 150 lines to ensure AI accuracy
    chunk_size = 150
    for i in range(0, len(lines), chunk_size):
        chunk = "".join(lines[i:i + chunk_size])
        if chunk.strip():
            print(f"  Sending lines {i} to {i + len(lines[i:i+chunk_size])} to AI...")
            extracted_data = process_chunk_with_ai(chunk)
            all_records.extend(extracted_data)

# 5. Format and Save Output
if not all_records:
    print("AI could not extract any valid workout records.")
    exit(1)

df = pd.DataFrame(all_records)

# Clean up and add Set numbers
df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
df = df.dropna(subset=['Date', 'Exercise', 'Weight', 'Reps'])
df = df.sort_values(by=['Date', 'Exercise'])
df['Set'] = df.groupby(['Date', 'Exercise']).cumcount() + 1

# Reorder columns
df = df[['Date', 'Exercise', 'Set', 'Weight', 'Reps']]

# Ensure output directory exists
os.makedirs('output', exist_ok=True)
output_path = 'output/Cleaned_Jefit_Data.csv'
df.to_csv(output_path, index=False)

print(f"Success! {len(df)} sets cleaned and saved to {output_path}.")

```

