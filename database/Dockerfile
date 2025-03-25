FROM python:3.10-slim

WORKDIR /app

# Copy only the necessary files
COPY product_api.py .
COPY supabase_client.py .
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port that the API runs on
EXPOSE 8100

# Command to run the API
CMD ["python", "product_api.py"]