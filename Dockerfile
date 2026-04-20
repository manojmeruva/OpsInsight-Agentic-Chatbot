# Use Python 3.12.8-slim as the base image
FROM python:3.12.8-slim

# Prevent Python from writing .pyc files to disk and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /impressa-interact-backend

# Copy the requirements file and install dependencies
COPY app/src/requirements.txt /impressa-interact-backend/requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the entire application code from the src directory to /app
COPY app/src/ /impressa-interact-backend

# Copy the local llm.db to the container
# COPY LLM_Testing.db /impressa-flask-backend/LLM_Testing.db



# Set the DB_PATH environment variable to point to the database file in the volume
# ENV DB_PATH="/impressa-flask-backend/LLM_Testing.db"

# (Optional) Set other environment variables; these can be overridden at runtime
ENV TOGETHER_API_KEY=""
ENV MODEL_NAME=""
ENV MONGO_URI=""
# Expose port 5000 so the container is accessible on that port
EXPOSE 5000

# Start the Fastapi application
CMD ["python", "main.py"]                             



