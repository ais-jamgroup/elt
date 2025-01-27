import os
import pandas as pd
import sqlalchemy
from datetime import datetime
from flask import Flask

app = Flask(__name__)

@app.route("/")
def run_etl():
    """Trigger the ETL process."""
    try:
        print("Starting ETL process...")
        # Call the ETL functions
        extracted_data = extract()
        transformed_data = transform(extracted_data)
        load(transformed_data)
        print("ETL process completed successfully.")
        return "ETL process triggered and completed successfully!"
    except Exception as e:
        print(f"ETL process failed: {e}")
        return f"ETL process failed: {e}", 500


# Load environment variables for source and destination DBs
SRC_DB_USER = os.getenv("SRC_DB_USER", "remote_user")
SRC_DB_PASSWORD = os.getenv("SRC_DB_PASSWORD", "remote_password")
SRC_DB_HOST = os.getenv("SRC_DB_HOST", "localhost")
SRC_DB_PORT = os.getenv("SRC_DB_PORT", "3306")
SRC_DB_NAME = os.getenv("SRC_DB_NAME", "remote_source_db")

DEST_DB_USER = os.getenv("DEST_DB_USER", "root")
DEST_DB_PASSWORD = os.getenv("DEST_DB_PASSWORD", "root")
DEST_DB_HOST = os.getenv("DEST_DB_HOST", "localhost")
DEST_DB_PORT = os.getenv("DEST_DB_PORT", "3306")
DEST_DB_NAME = os.getenv("DEST_DB_NAME", "destination_db")

# Database connection strings
SRC_DB_URL = f"mysql+pymysql://{SRC_DB_USER}:{SRC_DB_PASSWORD}@{SRC_DB_HOST}:{SRC_DB_PORT}/{SRC_DB_NAME}"
DEST_DB_URL = f"mysql+pymysql://{DEST_DB_USER}:{DEST_DB_PASSWORD}@{DEST_DB_HOST}:{DEST_DB_PORT}/{DEST_DB_NAME}"

def extract():
    """Extract data from the remote `test_passers` table in the source database."""
    print("Extracting data...")
    try:
        engine = sqlalchemy.create_engine(SRC_DB_URL)
        query = "SELECT * FROM test_passers;"  # Extract only this table
        with engine.connect() as connection:
            data = pd.read_sql(query, connection)
        print("Data extracted from remote source:")
        print(data.head())
        return data
    except Exception as e:
        print(f"Error during data extraction: {e}")
        raise

def transform(data):
    """Transform the `test_passers` data for business intelligence."""
    print("Transforming data for business intelligence...")
    try:
        # Create a full name column in the "Surname, First Name Middle Name" format
        data["full_name"] = (
            data["surname"].str.title() + ", " +
            data["first_name"].str.title() + " " +
            data["middle_name"].fillna("").str.title()
        )

        # Format `date_of_birth` and calculate `age`
        data["date_of_birth"] = pd.to_datetime(data["date_of_birth"])
        current_date = datetime.now()
        data["age"] = data["date_of_birth"].apply(lambda dob: current_date.year - dob.year - ((current_date.month, current_date.day) < (dob.month, dob.day)))

        # Standardize and validate email format
        data["email"] = data["email"].str.lower().str.strip()

        # Clean up `address`, `shs_school`, and `school_address` by standardizing to title case
        data["address"] = data["address"].str.title().str.strip()
        data["shs_school"] = data["shs_school"].str.title().str.strip()
        data["school_address"] = data["school_address"].str.title().str.strip()

        # Format strand to capitalize first letter of each word
        data["strand"] = data["strand"].str.title().str.strip()

        # Add a calculated column for graduation decade (e.g., "2010s", "2020s")
        data["graduation_decade"] = (data["year_graduated"] // 10 * 10).astype(str) + "s"

        # Create a flag to identify test passers under the age of 18 (useful for filtering insights)
        data["is_minor"] = data["age"] < 18

        # Validate reference numbers (example: ensuring length and numeric format)
        data["is_reference_number_valid"] = data["reference_number"].str.match(r"^\d{8,12}$")  # Example: 8-12 digit numeric reference

        # Calculate the time elapsed since graduation
        data["years_since_graduation"] = current_date.year - data["year_graduated"]

        # Add a derived column for "region" or "province" if applicable (assuming address parsing is possible)
        # Example: Extract the last part of the address as a "region" (requires a structured address format)
        data["region"] = data["address"].str.extract(r"(\b\w+$)").fillna("Unknown")

        # Drop columns that are no longer needed
        columns_to_drop = ["first_name", "surname", "middle_name", "date_of_birth"]  # Specify columns to drop
        data = data.drop(columns=columns_to_drop)

        print("Transformed data:")
        print(data.head())
        return data

    except Exception as e:
        print(f"Error during data transformation: {e}")
        raise



def load(data):
    """Load transformed data into the local destination database."""
    print("Loading data into destination database...")
    try:
        engine = sqlalchemy.create_engine(DEST_DB_URL)
        with engine.connect() as connection:
            data.to_sql("test_passers_transformed", con=connection, if_exists="replace", index=False)  # Load into a new table
        print("Data loaded into destination database successfully!")
    except Exception as e:
        print(f"Error during data loading: {e}")
        raise

if __name__ == "__main__":
    try:
        print("Starting ETL process on container startup...")
        extracted_data = extract()
        transformed_data = transform(extracted_data)
        load(transformed_data)
        print("ETL process completed successfully.")
    except Exception as e:
        print(f"ETL process failed: {e}")
    app.run(host="0.0.0.0", port=5000, debug=True)
