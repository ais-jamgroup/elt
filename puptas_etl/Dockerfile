FROM python:3.9-slim

# Install dependencies
#RUN pip install pandas sqlalchemy pymysql
RUN pip install pandas sqlalchemy pymysql python-dotenv
RUN pip install flask


# Set working directory
WORKDIR /app

# Copy files
COPY puptas_etl.py /app/puptas_etl.py

# Set command to run the script
CMD ["python", "puptas_etl.py"]
#CMD ["bash"]
#CMD ["sh", "-c", "python /app/puptas_etl.py && tail -f /dev/null"]

