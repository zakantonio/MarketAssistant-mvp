FROM python:3.10-slim

WORKDIR /app

# Copy only necessary files and directories
COPY . .
# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port that the API runs on
EXPOSE 8101

# Command to run the API
CMD ["python", "api.py"]