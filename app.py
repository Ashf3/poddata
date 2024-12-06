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
#Session(app)

# In-memory store for user-specific processed data
user_data_store = {}

@app.route('/upload', methods=['POST'])
def upload_file():
    #print("Request Headers:", request.headers)
    # Check if user has a session and retrieve userid
    userid = request.headers.get('Authorization')

    if not userid:
        return jsonify({"error": "User ID is missing from the request."}), 400
    
    if not session.get('userid'):
        session['userid'] = userid
    


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
        user_data_store[userid] = df
        return jsonify({"message": "File processed successfully."}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/data', methods=['GET'])
def get_data():
    # Retrieve userid from session
    userid = request.headers.get('Authorization')

    if not userid or userid not in user_data_store:
        return jsonify({"error": "No data available for this user. Please upload a file first."}), 400

    # Fetch the user's data
    df = user_data_store[userid]

    # Convert DataFrame to JSON
    result = df.to_json(orient='split', date_unit='ms')
    return result, 200


@app.route('/top-products', methods=['GET'])
def get_top_products():

    userid = request.headers.get('Authorization')

    if not userid or userid not in user_data_store:
        return jsonify({"error": "No data available for this user. Please upload a file first."}), 400

    df = user_data_store[userid]
    
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

    userid = request.headers.get('Authorization')

    if not userid or userid not in user_data_store:
        return jsonify({"error": "No data available for this user. Please upload a file first."}), 400

    df = user_data_store[userid]
    
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

@app.route('/tee-totals', methods=['GET'])
def get_teepublic_totals():

    userid = request.headers.get('Authorization')

    if not userid or userid not in user_data_store:
        return jsonify({"error": "No data available for this user. Please upload a file first."}), 400

    df = user_data_store[userid]

    try:
        df['Order Date'] = pd.to_datetime(df['Order Date'], utc=True)

        # Time comparisons
        today = pd.Timestamp.now(tz='UTC').normalize()
        start_of_week = today - pd.Timedelta(days=today.weekday())
        start_of_month = today.replace(day=1)
        start_of_year = today.replace(month=1, day=1)

        # Filter DataFrames for specific periods
        today_data = df[df['Order Date'] >= today]
        week_data = df[df['Order Date'] >= start_of_week]
        month_data = df[df['Order Date'] >= start_of_month]
        year_data = df[df['Order Date'] >= start_of_year]

        # Helper to calculate totals
        def calculate_totals(filtered_df, column):
            return filtered_df[column].sum()

        # Total Earnings
        earnings = {
            "all_time": calculate_totals(df, 'Total Earnings'),
            "today": calculate_totals(today_data, 'Total Earnings'),
            "week": calculate_totals(week_data, 'Total Earnings'),
            "month": calculate_totals(month_data, 'Total Earnings'),
            "year": calculate_totals(year_data, 'Total Earnings'),
        }

        # Affiliate Earnings
        affiliate_earnings = {
            "all_time": calculate_totals(df, 'Affiliate Earnings'),
            "today": calculate_totals(today_data, 'Affiliate Earnings'),
            "week": calculate_totals(week_data, 'Affiliate Earnings'),
            "month": calculate_totals(month_data, 'Affiliate Earnings'),
            "year": calculate_totals(year_data, 'Affiliate Earnings'),
        }

        # Designer Earnings
        designer_earnings = {
            "all_time": calculate_totals(df, 'Designer Earnings'),
            "today": calculate_totals(today_data, 'Designer Earnings'),
            "week": calculate_totals(week_data, 'Designer Earnings'),
            "month": calculate_totals(month_data, 'Designer Earnings'),
            "year": calculate_totals(year_data, 'Designer Earnings'),
        }

        # Sales Counts
        sales_counts = {
            "all_time": len(df),
            "today": len(today_data),
            "week": len(week_data),
            "month": len(month_data),
            "year": len(year_data),
        }

        return jsonify({
            "total_earnings": earnings,
            "affiliate_earnings": affiliate_earnings,
            "designer_earnings": designer_earnings,
            "sales_counts": sales_counts,
        })

    except Exception as e:
        return jsonify({"error": f"An error occurred while processing the data: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True)