FROM python:3.12-slim

WORKDIR /app

# Installa le dipendenze
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia il codice dell'applicazione
COPY . .

EXPOSE ${PORT}

# Imposta PYTHONPATH per includere la directory corrente
ENV PYTHONPATH=/app

# Comando per avviare l'applicazione
CMD fastmcp run ./app/main.py:mcp --transport sse --host 0.0.0.0 --port ${PORT}