FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the necessary project files
COPY pyunimus.py .
COPY run.sh .

# Make the run script executable
RUN chmod +x run.sh

# Set the entrypoint to the script
ENTRYPOINT ["./run.sh"]