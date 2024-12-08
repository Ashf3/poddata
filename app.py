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

        def calculate_averages(total, period_length):
            return round(total / period_length, 2) if period_length > 0 else 0

        # Calculate time spans
        total_days = (df['Order Date'].max() - df['Order Date'].min()).days + 1
        total_weeks = total_days / 7
        total_months = total_days / 30.44  # Approximate average month length

        # Averages
        average_sales = {
            "per_day": calculate_averages(sales_counts["all_time"], total_days),
            "per_week": calculate_averages(sales_counts["all_time"], total_weeks),
            "per_month": calculate_averages(sales_counts["all_time"], total_months),
        }

        average_earnings = {
            "per_day": calculate_averages(earnings["all_time"], total_days),
            "per_week": calculate_averages(earnings["all_time"], total_weeks),
            "per_month": calculate_averages(earnings["all_time"], total_months),
        }

        return jsonify({
            "total_earnings": earnings,
            "affiliate_earnings": affiliate_earnings,
            "designer_earnings": designer_earnings,
            "sales_counts": sales_counts,
            "average_sales": average_sales,
            "average_earnings": average_earnings,
        })

    except Exception as e:
        return jsonify({"error": f"An error occurred while processing the data: {str(e)}"}), 500


@app.route('/tee-sales-data', methods=['GET'])
def get_sales_data():
    user_id = request.headers.get('Authorization')

    if not user_id or user_id not in user_data_store:
        return jsonify({"error": "No data available for this user. Please upload a file first."}), 400

    df = user_data_store[user_id]

    try:
        # Ensure 'Order Date' is in datetime format
        df['Order Date'] = pd.to_datetime(df['Order Date'], utc=True)

        # Helper to generate time series data
        def generate_time_series_data(df, period, date_column, freq, date_format):
            df[period] = df[date_column].dt.to_period(freq)  # Create a period-based column
            sales = df.groupby(period).size()  # Group by period and count sales
            all_periods = pd.period_range(start=df[period].min(), end=df[period].max(), freq=freq)
            sales = sales.reindex(all_periods, fill_value=0).reset_index()  # Fill missing periods with 0
            sales.columns = [period, 'Sales']  # Rename columns
            sales[period] = sales[period].dt.strftime(date_format)  # Format period for JSON compatibility
            return sales

        # Generate sales data for each granularity
        monthly_sales = generate_time_series_data(df, 'YearMonth', 'Order Date', 'M', '%Y-%m')
        weekly_sales = generate_time_series_data(df, 'YearWeek', 'Order Date', 'W', '%Y-%W')
        daily_sales = generate_time_series_data(df, 'YearDay', 'Order Date', 'D', '%Y-%m-%d')

        # Convert results to JSON-friendly format
        return jsonify({
            "monthly_sales_data": monthly_sales.to_dict(orient='records'),
            "weekly_sales_data": weekly_sales.to_dict(orient='records'),
            "daily_sales_data": daily_sales.to_dict(orient='records'),
        })

    except Exception as e:
        return jsonify({"error": f"An error occurred while processing the data: {str(e)}"}), 500

@app.route('/tee-earnings-data', methods=['GET'])
def get_earnings_data():
    user_id = request.headers.get('Authorization')

    if not user_id or user_id not in user_data_store:
        return jsonify({"error": "No data available for this user. Please upload a file first."}), 400

    df = user_data_store[user_id]

    try:
        # Ensure 'Order Date' is in datetime format
        df['Order Date'] = pd.to_datetime(df['Order Date'], utc=True)
        
        # Ensure 'Total Earnings' is numeric
        if 'Total Earnings' not in df.columns or not pd.api.types.is_numeric_dtype(df['Total Earnings']):
            return jsonify({"error": "'Total Earnings' column is missing or not numeric."}), 400

        # Helper to generate time series data
        def generate_time_series_data(df, period, date_column, freq, date_format, value_column):
            df[period] = df[date_column].dt.to_period(freq)  # Create a period-based column
            sales = df.groupby(period)[value_column].sum()  # Group by period and sum the earnings
            all_periods = pd.period_range(start=df[period].min(), end=df[period].max(), freq=freq)
            sales = sales.reindex(all_periods, fill_value=0).reset_index()  # Fill missing periods with 0
            sales.columns = [period, 'Total Earnings']  # Rename columns
            sales[period] = sales[period].dt.strftime(date_format)  # Format period for JSON compatibility
            return sales

        # Generate sales data for each granularity
        monthly_sales = generate_time_series_data(df, 'YearMonth', 'Order Date', 'M', '%Y-%m', 'Total Earnings')
        weekly_sales = generate_time_series_data(df, 'YearWeek', 'Order Date', 'W', '%Y-%W', 'Total Earnings')
        daily_sales = generate_time_series_data(df, 'YearDay', 'Order Date', 'D', '%Y-%m-%d', 'Total Earnings')

        # Convert results to JSON-friendly format
        return jsonify({
            "monthly_sales_data": monthly_sales.to_dict(orient='records'),
            "weekly_sales_data": weekly_sales.to_dict(orient='records'),
            "daily_sales_data": daily_sales.to_dict(orient='records'),
        })

    except Exception as e:
        return jsonify({"error": f"An error occurred while processing the data: {str(e)}"}), 500


@app.route('/tee-individual-sales', methods=['GET'])
def get_teepublic_sales():
    userid = request.headers.get('Authorization')
    time_scale = request.args.get('time_scale', 'all_time')

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
        if time_scale == 'today':
            filtered_df = df[df['Order Date'] >= today]
        elif time_scale == 'week':
            filtered_df = df[df['Order Date'] >= start_of_week]
        elif time_scale == 'month':
            filtered_df = df[df['Order Date'] >= start_of_month]
        elif time_scale == 'year':
            filtered_df = df[df['Order Date'] >= start_of_year]
        elif time_scale == 'all_time':
            filtered_df = df
        else:
            return jsonify({"error": "Invalid time scale. Use one of 'today', 'week', 'month', 'year', or 'all_time'."}), 400

        # Select relevant columns
        result = filtered_df[['Title', 'Total Earnings', 'Order Date']].to_dict(orient='records')

        return jsonify({
            "time_scale": time_scale,
            "designs_sold": result
        })

    except Exception as e:
        return jsonify({"error": f"An error occurred while processing the data: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True)