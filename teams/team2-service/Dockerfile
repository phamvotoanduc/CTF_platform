FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    iputils-ping \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set up dummy environment flag & flag file for local start
RUN echo "FLAG{cyber_black_market_dummy_file_flag}" > /flag.txt
ENV FLAG_ENV="FLAG{cyber_black_market_dummy_env_flag}"

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "app:app"]
