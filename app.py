import os
from flask import Flask, request, jsonify, session
from flask_session import Session
import pandas as pd
import uuid

app = Flask(__name__)

# Retrieve the SECRET_KEY from environment variables (for security)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')
app.config['SESSION_TYPE'] = 'filesystem'  # Use file-based session storage
app.config['SESSION_PERMANENT'] = False  # Sessions are not permanent by default
app.config['SESSION_USE_SIGNER'] = True  # Optionally, add extra security to session cookies

# Initialize session with Flask
Session(app)

# In-memory store for user-specific processed data
user_data_store = {}

@app.route('/upload', methods=['POST'])
def upload_file():
    # Check if user has a session and retrieve user_id
    user_id = request.headers.get('user_id')

    if not user_id:
        return jsonify({"error": "User ID is missing from the request."}), 400
    
    if not session.get('user_id'):
        session['user_id'] = user_id
    


    # Get the uploaded file
    file = request.files.get('file')
    if not file or not file.filename.endswith('.csv'):
        return jsonify({"error": "Invalid file type. Please upload a CSV file."}), 400

    try:
        # Process the CSV file
        df = pd.read_csv(file, skiprows=2)  # Skip the first two rows
        df = df.iloc[:-4]  # Drop the last four rows

        # Clean up the columns
        df['Order Date'] = pd.to_datetime(df['Order Date'], utc=True)
        df['Designer Earnings'] = pd.to_numeric(df['Designer Earnings'], errors='coerce')
        df['Affiliate Earnings'] = pd.to_numeric(df['Affiliate Earnings'], errors='coerce')

        # Store the processed data for this user in the user_data_store
        user_data_store[user_id] = df
        return jsonify({"message": "File processed successfully."}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/data', methods=['GET'])
def get_data():
    # Retrieve user_id from session
    user_id = request.headers.get('user_id')

    if not user_id or user_id not in user_data_store:
        return jsonify({"error": "No data available for this user. Please upload a file first."}), 400

    # Fetch the user's data
    df = user_data_store[user_id]

    # Convert DataFrame to JSON
    result = df.to_json(orient='split', date_unit='ms')
    return result, 200


@app.route('/top-products', methods=['GET'])
def get_top_products():

    user_id = request.headers.get('user_id')

    if not user_id or user_id not in user_data_store:
        return jsonify({"error": "No data available for this user. Please upload a file first."}), 400

    df = user_data_store[user_id]
    
    # Load the DataFrame from the session
    df['Order Date'] = pd.to_datetime(df['Order Date'],unit='ms', utc=True) 

    # Get the selected period from the query parameters
    period = request.args.get('period', 'alltime')
    today = pd.Timestamp.now(tz='UTC').normalize()
    start_of_week = today - pd.Timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)
    start_of_year = today.replace(month=1, day=1)

    if period == 'today':
        df = df[df['Order Date'] >= today]
    elif period == 'week':
        df = df[df['Order Date'] >= start_of_week]
    elif period == 'month':
        df = df[df['Order Date'] >= start_of_month]
    elif period == 'year':
        df = df[df['Order Date'] >= start_of_year]
    else:
        df = df  # Default to all data for 'alltime'

    top_products = (
        df.groupby('Product')
        .size()
        .reset_index(name='count')
        .sort_values(by='count', ascending=False)
        .head(10)
    )

    # Convert the DataFrame to a list of dictionaries
    top_products = top_products.to_dict(orient='records')

    return jsonify({"top_products": top_products})


@app.route('/top-designs', methods=['GET'])
def get_top_designs():

    user_id = request.headers.get('user_id')

    if not user_id or user_id not in user_data_store:
        return jsonify({"error": "No data available for this user. Please upload a file first."}), 400

    df = user_data_store[user_id]
    
    # Load the DataFrame from the session
    df['Order Date'] = pd.to_datetime(df['Order Date'],unit='ms', utc=True) 

    # Get the selected period from the query parameters
    period = request.args.get('period', 'alltime')
    today = pd.Timestamp.now(tz='UTC').normalize()
    start_of_week = today - pd.Timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)
    start_of_year = today.replace(month=1, day=1)

    if period == 'today':
        df = df[df['Order Date'] >= today]
    elif period == 'week':
        df = df[df['Order Date'] >= start_of_week]
    elif period == 'month':
        df = df[df['Order Date'] >= start_of_month]
    elif period == 'year':
        df = df[df['Order Date'] >= start_of_year]
    else:
        df = df  # Default to all data for 'alltime'

    top_designs = (
        df.groupby('Title')
        .size()
        .reset_index(name='count')
        .sort_values(by='count', ascending=False)
        .head(10)
    )

    # Convert the DataFrame to a list of dictionaries
    top_designs = top_designs.to_dict(orient='records')

    return jsonify({"top_designs": top_designs})

if __name__ == "__main__":
    app.run(debug=True)