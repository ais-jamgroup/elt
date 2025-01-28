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
        extracted_data = extract()
        demographics, education_trends, insights = transform(extracted_data)
        load(demographics, education_trends, insights)
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

SRC_DB_URL = f"mysql+pymysql://{SRC_DB_USER}:{SRC_DB_PASSWORD}@{SRC_DB_HOST}:{SRC_DB_PORT}/{SRC_DB_NAME}"
DEST_DB_URL = f"mysql+pymysql://{DEST_DB_USER}:{DEST_DB_PASSWORD}@{DEST_DB_HOST}:{DEST_DB_PORT}/{DEST_DB_NAME}"

def extract():
    """Extract data from the remote `test_passers` table in the source database."""
    print("Extracting data...")
    try:
        engine = sqlalchemy.create_engine(SRC_DB_URL)
        query = "SELECT * FROM test_passers;"
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
        current_date = datetime.now()
        
        # Clean and format data
        data["full_name"] = (
            data["surname"].str.title() + ", " +
            data["first_name"].str.title() + " " +
            data["middle_name"].fillna("").str.title()
        )
        data["date_of_birth"] = pd.to_datetime(data["date_of_birth"], errors="coerce")
        data["age"] = data["date_of_birth"].apply(
            lambda dob: current_date.year - dob.year - ((current_date.month, current_date.day) < (dob.month, dob.day))
            if pd.notnull(dob) else None
        )
        data["email"] = data["email"].str.lower().str.strip()
        data["address"] = data["address"].str.title().str.strip()
        data["shs_school"] = data["shs_school"].str.title().str.strip()
        data["school_address"] = data["school_address"].str.title().str.strip()
        data["strand"] = data["strand"].str.title().str.strip()
        data["graduation_decade"] = (data["year_graduated"] // 10 * 10).astype(str) + "s"
        data["is_minor"] = data["age"] < 18
        
        # Replace NaN in critical columns
        data["strand"] = data["strand"].fillna("Unknown")
        data["year_graduated"] = data["year_graduated"].fillna(0).astype(int)
        
        # Drop columns no longer needed
        data = data.drop(columns=["first_name", "surname", "middle_name", "date_of_birth"])

        # Split into separate tables
        demographics = data[["full_name", "age", "address", "email", "is_minor"]]
        education_trends = data[["shs_school", "school_address", "strand", "year_graduated", "graduation_decade"]]
        
        # Create insights table
        insights = pd.DataFrame({
            "total_passers": [len(data)],
            "average_age": [data["age"].mean() if not data["age"].isnull().all() else None],
            "min_age": [data["age"].min() if not data["age"].isnull().all() else None],
            "max_age": [data["age"].max() if not data["age"].isnull().all() else None],
            "minor_count": [data["is_minor"].sum() if "is_minor" in data.columns else 0],
            "major_count": [(~data["is_minor"]).sum() if "is_minor" in data.columns else 0],
            "most_common_school": [data["shs_school"].mode()[0] if not data["shs_school"].mode().empty else "N/A"],
            "most_common_strand": [data["strand"].mode()[0] if not data["strand"].mode().empty else "N/A"],
            "passers_by_strand": [pd.Series(data["strand"].value_counts()).to_json()],
            "passers_by_year_graduated": [pd.Series(data["year_graduated"].value_counts()).to_json()],
        })

        # Debugging outputs
        print("Transform Data Input:")
        print(data.head())
        print("Insights DataFrame:")
        print(insights)
        
        return demographics, education_trends, insights
    except Exception as e:
        print(f"Error during data transformation: {e}")
        raise


def load(demographics, education_trends, insights):
    """Load transformed data into the local destination database."""
    print("Loading data into destination database...")
    try:
        engine = sqlalchemy.create_engine(DEST_DB_URL)
        with engine.connect() as connection:
            demographics.to_sql("demographics", con=connection, if_exists="replace", index=False)
            education_trends.to_sql("education_trends", con=connection, if_exists="replace", index=False)
            insights.to_sql("insights", con=connection, if_exists="replace", index=False)
        print("Data loaded into destination database successfully!")
    except Exception as e:
        print(f"Error during data loading: {e}")
        raise

if __name__ == "__main__":
    try:
        print("Starting ETL process on container startup...")
        extracted_data = extract()
        demographics, education_trends, insights = transform(extracted_data)
        load(demographics, education_trends, insights)
        print("ETL process completed successfully.")
    except Exception as e:
        print(f"ETL process failed: {e}")
    app.run(host="0.0.0.0", port=5000, debug=True)
