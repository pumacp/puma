FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_PYTHON_VERSION_WARNING=1 \
    PIP_TRUSTED_HOST=pypi.org,pypi.python.org,files.pythonhosted.org

RUN apt-get update && apt-get install -y \
    wget \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --trusted-host pypi.org \
    --trusted-host pypi.python.org --trusted-host files.pythonhosted.org \
    -r requirements.txt

COPY . .

RUN mkdir -p /usr/local/lib/python3.11/site-packages/codecarbon/data/private_infra && \
    echo '{"country": "Sweden", "emission_factor": 0.04, "year": 2023}' > /usr/local/lib/python3.11/site-packages/codecarbon/data/private_infra/nordic_emissions.json || true

CMD ["tail", "-f", "/dev/null"]
