from flask import Flask, request, jsonify
import pandas as pd

app = Flask(__name__)

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    
    # Check if file exists and is a CSV
    if not file or not file.filename.endswith('.csv'):
        return jsonify({"error": "Invalid file type. Please upload a CSV file."}), 200
    
    try:
        # Read the CSV file, skipping the first two rows and ignoring the last two rows
        df = pd.read_csv(file, skiprows=2)  # Skip the first two rows (header is in row 3)
        
        # Drop the last two rows
        df = df.iloc[:-4]

        # Clean date to datetime format
        df['Order Date'] = pd.to_datetime(df['Order Date'], utc=True)
        
        # Clean earnings columns to a numeric format
        df['Designer Earnings'] = pd.to_numeric(df['Designer Earnings'], errors='coerce')
        df['Affiliate Earnings'] = pd.to_numeric(df['Affiliate Earnings'], errors='coerce')
        
        # Convert DataFrame to JSON
        result = df.to_json(orient='split', date_unit='ms')
        
        # Return the processed data as JSON
        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
