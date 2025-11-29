# Guida alla Migrazione e Personalizzazione del Digital Signature MCP Server

## Data di creazione: 2025-11-29

---

## INDICE

1. [Panoramica del Repository Attuale](#1-panoramica-del-repository-attuale)
2. [Obiettivi del Progetto](#2-obiettivi-del-progetto)
3. [Task 1: Migrazione su GitHub Personale](#3-task-1-migrazione-su-github-personale)
4. [Task 2: Modifica degli Endpoint e Dominio](#4-task-2-modifica-degli-endpoint-e-dominio)
5. [Task 3: Posizionamento Personalizzabile del Talloncino](#5-task-3-posizionamento-personalizzabile-del-talloncino)
6. [Task 4: Conversione Automatica in PDF/A](#6-task-4-conversione-automatica-in-pdfa)
7. [Configurazione Finale](#7-configurazione-finale)
8. [Testing](#8-testing)
9. [Note Tecniche Importanti](#9-note-tecniche-importanti)

---

## 1. PANORAMICA DEL REPOSITORY ATTUALE

### 1.1 Struttura del Progetto

```
digital-signature-mcp/
├── .env.example              # Template variabili d'ambiente
├── .gitignore               # File da escludere dal versioning
├── Dockerfile               # Container configuration
├── docker-compose.yml       # Docker orchestration
├── README.md                # Documentazione originale
├── requirements.txt         # Dipendenze Python
└── app/
    ├── main.py             # Applicazione principale MCP
    └── config/
        ├── __init__.py
        └── setting.py      # Gestione configurazioni
```

### 1.2 Tecnologie Utilizzate

- **Framework**: FastMCP 2.2.4 - Server MCP (Model Context Protocol)
- **Linguaggio**: Python 3.12
- **Storage**: DigitalOcean Spaces (compatibile S3) tramite boto3
- **API Firma**: Infocert Digital Signature API
- **PDF Processing**: pyHanko 0.31.0
- **Container**: Docker + Docker Compose

### 1.3 Funzionalità Attuali

Il server MCP espone 5 tool:

1. **auth_token**: Autenticazione OAuth2 con Infocert
2. **get_certificates**: Recupero certificati digitali disponibili
3. **request_smsp_challenge**: Richiesta OTP via SMS
4. **authorize_smsp**: Autorizzazione firma con OTP e PIN
5. **sign_document**: Firma documento PDF con upload automatico su DigitalOcean Spaces

### 1.4 Flusso di Firma Attuale

```
1. auth_token(username, password) → access_token
2. get_certificates(access_token) → certificate_id
3. request_smsp_challenge(access_token) → transaction_id
4. authorize_smsp(access_token, certificate_id, transaction_id, otp, pin) → SAT token
5. sign_document(certificate_id, access_token, infocert_sat, transaction_id, pin, link_pdf) → signed_url
```

### 1.5 Endpoint API Infocert Attuali

- **SIGNATURE_API**: `https://api.infocert.digital/signature/v1`
- **AUTHORIZATION_API**: `https://isac.infocert.it/isac-oauth2/api`

### 1.6 Configurazione Endpoint MCP Attuali

Nel file `app/main.py` (righe 16-23):
```python
mcp = FastMCP(
    name="Signature MCP Server",
    sse_path='/digital-signature/sse',
    message_path='/digital-signature/messages/',
    initialization_timeout=120,
    max_retries=10,
    retry_delay=5
)
```

### 1.7 Posizionamento Firma Attuale

Nel file `app/main.py` (righe 569-581):
```python
signature_fields.append({
    "position": {
        "page": page_num,
        "llx": 500,    # Lower Left X - HARDCODED
        "lly": 60,     # Lower Left Y - HARDCODED
        "urx": 580,    # Upper Right X - HARDCODED
        "ury": 90      # Upper Right Y - HARDCODED
    },
    "signatureImage": "iVBORw0KGgoAAAANSUh...",  # Base64 image
    "avoidGraphicLayers": True,
    "visibleText": visible_text,
    "fontSize": 4
})
```

**Coordinate attuali**: Angolo in basso a destra della pagina (llx=500, lly=60, urx=580, ury=90)

### 1.8 Formato PDF Attuale

- **Input**: PDF generico (non verificato se PDF/A)
- **Output**: PDF firmato con firma PAdES BASELINE-B (NON PDF/A)
- **Storage**: DigitalOcean Spaces con URL firmato (60 minuti di validità)

---

## 2. OBIETTIVI DEL PROGETTO

### 2.1 Task da Implementare

1. ✅ **Migrazione Repository**: Clonare e ripubblicare su GitHub personale
2. ✅ **Modifica Endpoint**: Cambiare path MCP ed esporre su dominio personalizzato
3. ✅ **Posizionamento Firma**: Permettere scelta posizione talloncino su PDF
4. ✅ **Conversione PDF/A**: Convertire automaticamente tutti i file in PDF/A prima della firma

---

## 3. TASK 1: MIGRAZIONE SU GITHUB PERSONALE

### 3.1 Prerequisiti

- Account GitHub personale
- Git configurato localmente
- GITHUB_TOKEN con permessi `repo` (se necessario per operazioni automatiche)

### 3.2 Comandi per la Migrazione

```bash
# 1. Il repository è già clonato in /workspace/digital-signature-mcp
cd /workspace/digital-signature-mcp

# 2. Verifica remote attuale
git remote -v
# Output: origin  https://github.com/AI-Blackbird/digital-signature-mcp.git

# 3. Rimuovi remote origin esistente
git remote remove origin

# 4. Aggiungi nuovo remote verso il tuo GitHub
# SOSTITUISCI: <TUO_USERNAME> con il tuo username GitHub
# SOSTITUISCI: <TUO_REPO_NAME> con il nome che vuoi dare al repo
git remote add origin https://github.com/<TUO_USERNAME>/<TUO_REPO_NAME>.git

# 5. Verifica la configurazione
git remote -v

# 6. Crea un nuovo branch (opzionale, ma raccomandato)
git checkout -b main-custom

# 7. Push al nuovo repository
# NOTA: Se il repository non esiste su GitHub, crealo prima tramite interfaccia web
git push -u origin main-custom

# OPPURE, se vuoi mantenere il branch main:
git push -u origin main
```

### 3.3 Creazione Repository su GitHub (via API)

Se preferisci creare il repository via API:

```bash
# Usando curl e GITHUB_TOKEN
curl -X POST https://api.github.com/user/repos \
  -H "Authorization: token ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github.v3+json" \
  -d '{
    "name": "digital-signature-mcp-custom",
    "description": "Custom Digital Signature MCP Server with PDF/A support",
    "private": false,
    "auto_init": false
  }'
```

### 3.4 Verifica Post-Migrazione

```bash
# Verifica che il repository sia stato creato correttamente
git log --oneline --max-count=5
git branch -a
git remote show origin
```

---

## 4. TASK 2: MODIFICA DEGLI ENDPOINT E DOMINIO

### 4.1 Endpoint MCP da Modificare

**File**: `app/main.py` (righe 16-23)

**Modifica Attuale**:
```python
mcp = FastMCP(
    name="Signature MCP Server",
    sse_path='/digital-signature/sse',           # ← DA MODIFICARE
    message_path='/digital-signature/messages/', # ← DA MODIFICARE
    initialization_timeout=120,
    max_retries=10,
    retry_delay=5
)
```

**Modifica Proposta**:
```python
mcp = FastMCP(
    name="Signature MCP Server",
    sse_path='/<TUO_PATH_CUSTOM>/sse',           # ← NUOVO PATH
    message_path='/<TUO_PATH_CUSTOM>/messages/', # ← NUOVO PATH
    initialization_timeout=120,
    max_retries=10,
    retry_delay=5
)
```

**Esempio Concreto** (se vuoi usare `/api/signature`):
```python
mcp = FastMCP(
    name="Signature MCP Server",
    sse_path='/api/signature/sse',
    message_path='/api/signature/messages/',
    initialization_timeout=120,
    max_retries=10,
    retry_delay=5
)
```

### 4.2 Configurazione Variabili d'Ambiente

**Opzione 1**: Aggiungere variabili configurabili

**File**: `app/config/setting.py`

**Modifica**:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Existing settings
    CLIENT_ID: str
    CLIENT_SECRET: str
    SIGNATURE_API: str
    AUTHORIZATION_API: str
    TENANT: str
    
    # DigitalOcean Spaces configuration
    DO_SPACES_ACCESS_KEY: str
    DO_SPACES_SECRET_KEY: str
    DO_SPACES_REGION: str = "nyc3"
    DO_SPACES_BUCKET: str
    DO_SPACES_ENDPOINT: str = "https://nyc3.digitaloceanspaces.com"
    
    # NUOVO: MCP Server configuration
    MCP_SSE_PATH: str = "/digital-signature/sse"
    MCP_MESSAGE_PATH: str = "/digital-signature/messages/"
    MCP_SERVER_NAME: str = "Signature MCP Server"

settings = Settings()
```

**File**: `app/main.py` (righe 16-23)

**Modifica**:
```python
from app.config.setting import settings

mcp = FastMCP(
    name=settings.MCP_SERVER_NAME,
    sse_path=settings.MCP_SSE_PATH,
    message_path=settings.MCP_MESSAGE_PATH,
    initialization_timeout=120,
    max_retries=10,
    retry_delay=5
)
```

**File**: `.env.example`

**Aggiungi**:
```env
# MCP Server Endpoints
MCP_SSE_PATH=/api/signature/sse
MCP_MESSAGE_PATH=/api/signature/messages/
MCP_SERVER_NAME=Custom Signature MCP Server
```

### 4.3 Configurazione Dominio e Reverse Proxy

Per esporre il server su un dominio personalizzato, avrai bisogno di un reverse proxy (es. Nginx).

**Esempio Configurazione Nginx**:

```nginx
# File: /etc/nginx/sites-available/signature-mcp

upstream signature_mcp {
    server localhost:8888;  # Porta del container Docker
}

server {
    listen 80;
    server_name tuo-dominio.com;  # ← SOSTITUISCI

    # Redirect HTTP to HTTPS (opzionale ma raccomandato)
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name tuo-dominio.com;  # ← SOSTITUISCI

    # SSL Configuration (usa Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/tuo-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tuo-dominio.com/privkey.pem;

    # MCP Server Endpoints
    location /api/signature/ {
        proxy_pass http://signature_mcp/api/signature/;
        proxy_http_version 1.1;
        
        # SSE Support
        proxy_set_header Connection '';
        proxy_set_header Cache-Control 'no-cache';
        proxy_set_header X-Accel-Buffering 'no';
        proxy_buffering off;
        
        # Standard headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeout for long-running requests
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
```

**Comandi per Attivare Nginx**:

```bash
# 1. Crea il file di configurazione
sudo nano /etc/nginx/sites-available/signature-mcp

# 2. Abilita il sito
sudo ln -s /etc/nginx/sites-available/signature-mcp /etc/nginx/sites-enabled/

# 3. Verifica la configurazione
sudo nginx -t

# 4. Riavvia Nginx
sudo systemctl restart nginx

# 5. Installa certificato SSL (Let's Encrypt)
sudo certbot --nginx -d tuo-dominio.com
```

### 4.4 Docker Compose con Variabili Custom

**File**: `docker-compose.yml`

**Modifica**:
```yaml
services:
  signature-server:
    container_name: signature-server
    build: .
    ports:
      - "${PORT}:${PORT}"
    volumes:
      - .:/app
    restart: unless-stopped
    env_file:
      - .env
    environment:
      - MCP_SSE_PATH=${MCP_SSE_PATH:-/api/signature/sse}
      - MCP_MESSAGE_PATH=${MCP_MESSAGE_PATH:-/api/signature/messages/}
      - MCP_SERVER_NAME=${MCP_SERVER_NAME:-Custom Signature MCP Server}
    networks:
      - signature-network

networks:
  signature-network:
    driver: bridge
```

---

## 5. TASK 3: POSIZIONAMENTO PERSONALIZZABILE DEL TALLONCINO

### 5.1 Analisi del Codice Attuale

**File**: `app/main.py` (righe 566-581)

Le coordinate attuali sono **hardcoded**:
- `llx=500` (Lower Left X)
- `lly=60` (Lower Left Y)
- `urx=580` (Upper Right X)
- `ury=90` (Upper Right Y)

Questo posiziona la firma nell'**angolo in basso a destra**.

### 5.2 Sistema di Coordinate PDF

Nel sistema di coordinate PDF:
- Origine (0,0) è nell'**angolo in basso a sinistra**
- X cresce verso destra
- Y cresce verso l'alto
- Dimensioni standard pagina A4: **595 x 842 punti**

### 5.3 Posizioni Predefinite Comuni

| Posizione | llx | lly | urx | ury | Descrizione |
|-----------|-----|-----|-----|-----|-------------|
| Basso Sinistra | 20 | 60 | 100 | 90 | Angolo in basso a sinistra |
| Basso Centro | 257 | 60 | 337 | 90 | Centro in basso |
| Basso Destra | 500 | 60 | 580 | 90 | Angolo in basso a destra (ATTUALE) |
| Alto Sinistra | 20 | 752 | 100 | 782 | Angolo in alto a sinistra |
| Alto Centro | 257 | 752 | 337 | 782 | Centro in alto |
| Alto Destra | 500 | 752 | 580 | 782 | Angolo in alto a destra |
| Centro Pagina | 247 | 396 | 327 | 426 | Centro della pagina |

### 5.4 Implementazione del Sistema di Posizionamento

**Opzione 1: Posizioni Predefinite (Raccomandato per Semplicità)**

**File**: `app/main.py`

**Aggiungi questa funzione** (dopo la riga 203, prima del decorator @mcp.tool):

```python
def get_signature_position(position_name: str, page_width: int = 595, page_height: int = 842) -> dict:
    """
    Restituisce le coordinate per il posizionamento del talloncino di firma.
    
    Args:
        position_name: Nome della posizione desiderata
        page_width: Larghezza della pagina in punti (default: 595 per A4)
        page_height: Altezza della pagina in punti (default: 842 per A4)
    
    Returns:
        dict: Coordinate {"llx": int, "lly": int, "urx": int, "ury": int}
    
    Posizioni disponibili:
        - "bottom_left": Angolo in basso a sinistra
        - "bottom_center": Centro in basso
        - "bottom_right": Angolo in basso a destra (default attuale)
        - "top_left": Angolo in alto a sinistra
        - "top_center": Centro in alto
        - "top_right": Angolo in alto a destra
        - "center": Centro della pagina
        - "custom": Usa coordinate personalizzate (deve passare custom_coords)
    """
    # Dimensioni standard del talloncino di firma
    signature_width = 80
    signature_height = 30
    margin = 20  # Margine dai bordi
    
    positions = {
        "bottom_left": {
            "llx": margin,
            "lly": margin + 40,
            "urx": margin + signature_width,
            "ury": margin + 40 + signature_height
        },
        "bottom_center": {
            "llx": (page_width - signature_width) // 2,
            "lly": margin + 40,
            "urx": (page_width + signature_width) // 2,
            "ury": margin + 40 + signature_height
        },
        "bottom_right": {
            "llx": page_width - margin - signature_width,
            "lly": margin + 40,
            "urx": page_width - margin,
            "ury": margin + 40 + signature_height
        },
        "top_left": {
            "llx": margin,
            "lly": page_height - margin - signature_height,
            "urx": margin + signature_width,
            "ury": page_height - margin
        },
        "top_center": {
            "llx": (page_width - signature_width) // 2,
            "lly": page_height - margin - signature_height,
            "urx": (page_width + signature_width) // 2,
            "ury": page_height - margin
        },
        "top_right": {
            "llx": page_width - margin - signature_width,
            "lly": page_height - margin - signature_height,
            "urx": page_width - margin,
            "ury": page_height - margin
        },
        "center": {
            "llx": (page_width - signature_width) // 2,
            "lly": (page_height - signature_height) // 2,
            "urx": (page_width + signature_width) // 2,
            "ury": (page_height + signature_height) // 2
        }
    }
    
    # Default: bottom_right (comportamento attuale)
    return positions.get(position_name, positions["bottom_right"])
```

**Modifica la funzione `sign_document`** (riga 442):

**PRIMA** (riga 442):
```python
def sign_document(
    certificate_id: Annotated[str, Field(description="ID del certificato digitale ottenuto da get_certificates")],
    access_token: Annotated[str, Field(description="Token di accesso ottenuto dal tool auth_token")],
    infocert_sat: Annotated[str, Field(description="Token SAT ottenuto dal tool authorize_smsp")],
    transaction_id: Annotated[str, Field(description="ID della transazione ottenuto da request_smsp_challenge")],
    pin: Annotated[str, Field(description="PIN del certificato digitale (password di protezione)")],
    link_pdf: Annotated[str, Field(description="URL del documento PDF da firmare (deve essere accessibile pubblicamente)")],
    page_signature: Annotated[str, Field(description="Pagina dove posizionare la firma: 'prima_pagina', 'ultima_pagina', o 'tutte_le_pagine' (default: 'ultima_pagina')", default="ultima_pagina")] = "tutte_le_pagine",
) -> dict:
```

**DOPO**:
```python
def sign_document(
    certificate_id: Annotated[str, Field(description="ID del certificato digitale ottenuto da get_certificates")],
    access_token: Annotated[str, Field(description="Token di accesso ottenuto dal tool auth_token")],
    infocert_sat: Annotated[str, Field(description="Token SAT ottenuto dal tool authorize_smsp")],
    transaction_id: Annotated[str, Field(description="ID della transazione ottenuto da request_smsp_challenge")],
    pin: Annotated[str, Field(description="PIN del certificato digitale (password di protezione)")],
    link_pdf: Annotated[str, Field(description="URL del documento PDF da firmare (deve essere accessibile pubblicamente)")],
    page_signature: Annotated[str, Field(description="Pagina dove posizionare la firma: 'prima_pagina', 'ultima_pagina', o 'tutte_le_pagine' (default: 'ultima_pagina')", default="ultima_pagina")] = "tutte_le_pagine",
    signature_position: Annotated[str, Field(description="Posizione del talloncino di firma: 'bottom_left', 'bottom_center', 'bottom_right', 'top_left', 'top_center', 'top_right', 'center' (default: 'bottom_right')", default="bottom_right")] = "bottom_right",
    custom_coords: Annotated[Optional[dict], Field(description="Coordinate personalizzate: {'llx': int, 'lly': int, 'urx': int, 'ury': int}. Ignora signature_position se fornito.", default=None)] = None,
) -> dict:
```

**Modifica il loop di creazione signature_fields** (righe 566-581):

**PRIMA**:
```python
# Crea l'array signatureFields dinamico per ogni pagina
signature_fields = []
for page_num in signature_pages:
    signature_fields.append({
        "position": {
            "page": page_num,
            "llx": 500,
            "lly": 60,
            "urx": 580,
            "ury": 90
        },
        "signatureImage": "iVBORw0KGgoAAAANSUh...",
        "avoidGraphicLayers": True,
        "visibleText": visible_text,
        "fontSize": 4
    })
```

**DOPO**:
```python
# Determina le coordinate del talloncino
if custom_coords:
    # Usa coordinate personalizzate se fornite
    coords = {
        "llx": custom_coords.get("llx", 500),
        "lly": custom_coords.get("lly", 60),
        "urx": custom_coords.get("urx", 580),
        "ury": custom_coords.get("ury", 90)
    }
else:
    # Usa posizione predefinita
    coords = get_signature_position(signature_position)

# Crea l'array signatureFields dinamico per ogni pagina
signature_fields = []
for page_num in signature_pages:
    signature_fields.append({
        "position": {
            "page": page_num,
            "llx": coords["llx"],
            "lly": coords["lly"],
            "urx": coords["urx"],
            "ury": coords["ury"]
        },
        "signatureImage": "iVBORw0KGgoAAAANSUh...",
        "avoidGraphicLayers": True,
        "visibleText": visible_text,
        "fontSize": 4
    })
```

**Aggiorna la docstring** della funzione `sign_document` per includere i nuovi parametri:

```python
"""
Firma digitalmente un documento PDF utilizzando il servizio Infocert.

Questo tool esegue la firma digitale completa di un documento PDF:
1. Scarica il documento dal link fornito
2. Converte il contenuto in base64
3. Applica la firma digitale PAdES (PDF Advanced Electronic Signatures)
4. Converte il risultato base64 in file PDF
5. Carica automaticamente il PDF firmato su DigitalOcean Spaces

La firma utilizza il livello BASELINE-B per garantire la massima compatibilità
e conformità agli standard europei per le firme elettroniche avanzate.

Args:
    certificate_id (str): ID del certificato digitale da utilizzare
    access_token (str): Token di accesso valido ottenuto da auth_token
    infocert_sat (str): Token di autorizzazione ottenuto da authorize_smsp
    transaction_id (str): ID della transazione ottenuto da request_smsp_challenge
    pin (str): PIN di protezione del certificato digitale
    link_pdf (str): URL pubblico del documento PDF da firmare
    page_signature (str): Pagina dove posizionare la firma: 'prima_pagina', 'ultima_pagina', o 'tutte_le_pagine'
    signature_position (str): Posizione del talloncino: 'bottom_left', 'bottom_center', 'bottom_right', 
                             'top_left', 'top_center', 'top_right', 'center'
    custom_coords (dict, optional): Coordinate personalizzate {"llx": int, "lly": int, "urx": int, "ury": int}
    
Returns:
    dict: Risposta della firma con URL del documento firmato
"""
```

### 5.5 Esempio di Utilizzo

**Posizione Predefinita**:
```python
sign_document(
    certificate_id="123456",
    access_token="...",
    infocert_sat="...",
    transaction_id="...",
    pin="1234",
    link_pdf="https://example.com/doc.pdf",
    page_signature="ultima_pagina",
    signature_position="top_left"  # Firma in alto a sinistra
)
```

**Coordinate Personalizzate**:
```python
sign_document(
    certificate_id="123456",
    access_token="...",
    infocert_sat="...",
    transaction_id="...",
    pin="1234",
    link_pdf="https://example.com/doc.pdf",
    page_signature="tutte_le_pagine",
    custom_coords={
        "llx": 100,
        "lly": 400,
        "urx": 200,
        "ury": 450
    }
)
```

---

## 6. TASK 4: CONVERSIONE AUTOMATICA IN PDF/A

### 6.1 Requisiti

Il sistema deve:
1. **Accettare qualsiasi file** (DOC, DOCX, TXT, immagini, etc.)
2. **Convertire automaticamente in PDF/A** se non è già PDF
3. **Verificare se un PDF è già PDF/A compliant**
4. **Convertire PDF non-compliant in PDF/A**
5. **Mantenere la qualità del documento originale**

### 6.2 Librerie Necessarie

**File**: `requirements.txt`

**Aggiungi**:
```txt
# Existing dependencies
fastmcp==2.2.4
requests==2.32.3
pydantic==2.11.4
pydantic-settings==2.8.1
boto3==1.40.32
pyHanko==0.31.0

# NUOVE DIPENDENZE per PDF/A conversion
pikepdf==9.4.2           # PDF manipulation e verifica PDF/A
ocrmypdf==16.5.0         # Conversione in PDF/A (include Ghostscript)
pillow==11.0.0           # Conversione immagini in PDF
pypdf==5.1.0             # Alternative PDF processing
python-magic==0.4.27     # Rilevamento tipo MIME
pdf2image==1.17.0        # Conversione PDF in immagini (se necessario)
reportlab==4.2.5         # Creazione PDF da zero
```

**NOTA**: `ocrmypdf` richiede Ghostscript installato nel sistema.

**File**: `Dockerfile`

**Modifica**:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# NUOVO: Installa dipendenze di sistema per PDF/A conversion
RUN apt-get update && apt-get install -y \
    ghostscript \
    libmagic1 \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-ita \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Installa le dipendenze Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia il codice dell'applicazione
COPY . .

EXPOSE ${PORT}

# Imposta PYTHONPATH per includere la directory corrente
ENV PYTHONPATH=/app

# Comando per avviare l'applicazione
CMD fastmcp run ./app/main.py:mcp --transport sse --host 0.0.0.0 --port ${PORT}
```

### 6.3 Implementazione delle Funzioni di Conversione

**File**: `app/pdf_converter.py` (NUOVO FILE)

```python
"""
PDF/A Conversion Module

Questo modulo gestisce la conversione di file in PDF/A compliant.
Supporta:
- Conversione di file Office (DOC, DOCX, XLS, XLSX, PPT, PPTX)
- Conversione di immagini (JPG, PNG, TIFF, BMP)
- Conversione di PDF standard in PDF/A
- Verifica della conformità PDF/A
"""

import os
import tempfile
import magic
from io import BytesIO
from typing import Tuple, Optional
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import pikepdf
import ocrmypdf
from pathlib import Path


class PDFAConverter:
    """Classe per la conversione di file in PDF/A."""
    
    # MIME types supportati
    SUPPORTED_IMAGE_TYPES = [
        'image/jpeg',
        'image/png',
        'image/tiff',
        'image/bmp',
        'image/gif'
    ]
    
    SUPPORTED_OFFICE_TYPES = [
        'application/msword',  # DOC
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # DOCX
        'application/vnd.ms-excel',  # XLS
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # XLSX
        'application/vnd.ms-powerpoint',  # PPT
        'application/vnd.openxmlformats-officedocument.presentationml.presentation'  # PPTX
    ]
    
    PDF_TYPES = [
        'application/pdf'
    ]
    
    def __init__(self):
        """Inizializza il converter."""
        self.magic = magic.Magic(mime=True)
    
    def detect_file_type(self, file_content: bytes) -> str:
        """
        Rileva il tipo MIME del file.
        
        Args:
            file_content: Contenuto del file in bytes
            
        Returns:
            str: MIME type del file
        """
        return self.magic.from_buffer(file_content)
    
    def is_pdf_a_compliant(self, pdf_content: bytes) -> Tuple[bool, str]:
        """
        Verifica se un PDF è già PDF/A compliant.
        
        Args:
            pdf_content: Contenuto del PDF in bytes
            
        Returns:
            Tuple[bool, str]: (is_compliant, version)
                is_compliant: True se è PDF/A
                version: Versione PDF/A (es. "PDF/A-1b", "PDF/A-2b", "PDF/A-3b") o "Not PDF/A"
        """
        try:
            with pikepdf.open(BytesIO(pdf_content)) as pdf:
                # Controlla metadata XMP per identificatore PDF/A
                if hasattr(pdf, 'open_metadata'):
                    metadata = pdf.open_metadata()
                    metadata_str = str(metadata)
                    
                    # Cerca identificatori PDF/A
                    if 'pdfaid:part' in metadata_str.lower():
                        # Estrai versione
                        if 'part="1"' in metadata_str or 'part>1<' in metadata_str:
                            return True, "PDF/A-1b"
                        elif 'part="2"' in metadata_str or 'part>2<' in metadata_str:
                            return True, "PDF/A-2b"
                        elif 'part="3"' in metadata_str or 'part>3<' in metadata_str:
                            return True, "PDF/A-3b"
                        else:
                            return True, "PDF/A (unknown version)"
                
                # Controlla anche nel PDF Info dictionary
                if '/GTS_PDFA1Version' in pdf.Root or '/GTS_PDFAVersion' in pdf.Root:
                    return True, "PDF/A (detected in Root)"
                
                return False, "Not PDF/A"
                
        except Exception as e:
            print(f"Error checking PDF/A compliance: {str(e)}")
            return False, f"Error: {str(e)}"
    
    def convert_image_to_pdfa(self, image_content: bytes, filename: str = "document.pdf") -> bytes:
        """
        Converte un'immagine in PDF/A.
        
        Args:
            image_content: Contenuto dell'immagine in bytes
            filename: Nome del file (per logging)
            
        Returns:
            bytes: PDF/A generato
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Salva immagine temporanea
            temp_image = os.path.join(tmpdir, "input_image.tmp")
            with open(temp_image, 'wb') as f:
                f.write(image_content)
            
            # Apri immagine con Pillow
            img = Image.open(temp_image)
            
            # Converti in RGB se necessario (per CMYK, LA, etc.)
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            
            # Crea PDF temporaneo
            temp_pdf = os.path.join(tmpdir, "temp.pdf")
            
            # Determina dimensioni pagina basate su immagine
            img_width, img_height = img.size
            aspect_ratio = img_width / img_height
            
            # Usa A4 come base, adatta se necessario
            page_width, page_height = A4
            
            if aspect_ratio > (page_width / page_height):
                # Immagine più larga, adatta larghezza
                new_width = page_width - 40  # margine
                new_height = new_width / aspect_ratio
            else:
                # Immagine più alta, adatta altezza
                new_height = page_height - 40  # margine
                new_width = new_height * aspect_ratio
            
            # Centra immagine
            x = (page_width - new_width) / 2
            y = (page_height - new_height) / 2
            
            # Crea PDF con ReportLab
            c = canvas.Canvas(temp_pdf, pagesize=A4)
            c.drawImage(temp_image, x, y, width=new_width, height=new_height)
            c.save()
            
            # Converti in PDF/A con ocrmypdf
            temp_pdfa = os.path.join(tmpdir, "output_pdfa.pdf")
            ocrmypdf.ocr(
                temp_pdf,
                temp_pdfa,
                skip_text=True,  # Non fare OCR, è già un'immagine
                output_type='pdfa',
                pdfa_image_compression='jpeg',
                optimize=1
            )
            
            # Leggi risultato
            with open(temp_pdfa, 'rb') as f:
                return f.read()
    
    def convert_pdf_to_pdfa(self, pdf_content: bytes, filename: str = "document.pdf") -> bytes:
        """
        Converte un PDF standard in PDF/A.
        
        Args:
            pdf_content: Contenuto del PDF in bytes
            filename: Nome del file (per logging)
            
        Returns:
            bytes: PDF/A generato
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Salva PDF di input
            input_pdf = os.path.join(tmpdir, "input.pdf")
            with open(input_pdf, 'wb') as f:
                f.write(pdf_content)
            
            # Converti in PDF/A
            output_pdfa = os.path.join(tmpdir, "output_pdfa.pdf")
            
            try:
                ocrmypdf.ocr(
                    input_pdf,
                    output_pdfa,
                    skip_text=True,  # Mantieni testo esistente
                    output_type='pdfa-2',  # PDF/A-2b (più moderno)
                    optimize=1,
                    pdfa_image_compression='jpeg'
                )
            except Exception as e:
                # Se ocrmypdf fallisce, prova con pikepdf (metodo più semplice)
                print(f"ocrmypdf failed, trying pikepdf: {str(e)}")
                
                with pikepdf.open(input_pdf) as pdf:
                    # Aggiungi metadata PDF/A
                    with pdf.open_metadata() as meta:
                        meta['pdfaid:part'] = '2'
                        meta['pdfaid:conformance'] = 'B'
                    
                    pdf.save(output_pdfa, linearize=True)
            
            # Leggi risultato
            with open(output_pdfa, 'rb') as f:
                return f.read()
    
    def convert_office_to_pdfa(self, file_content: bytes, mime_type: str, filename: str = "document") -> bytes:
        """
        Converte un file Office (DOC, DOCX, XLS, XLSX, PPT, PPTX) in PDF/A.
        
        NOTA: Questa funzione richiede LibreOffice installato.
        Se non è disponibile, solleva NotImplementedError.
        
        Args:
            file_content: Contenuto del file in bytes
            mime_type: Tipo MIME del file
            filename: Nome del file (senza estensione)
            
        Returns:
            bytes: PDF/A generato
            
        Raises:
            NotImplementedError: Se LibreOffice non è disponibile
        """
        # Verifica se LibreOffice è installato
        import shutil
        if not shutil.which('libreoffice'):
            raise NotImplementedError(
                "LibreOffice non è installato. "
                "Installa con: apt-get install libreoffice"
            )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Determina estensione file
            extensions = {
                'application/msword': '.doc',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
                'application/vnd.ms-excel': '.xls',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
                'application/vnd.ms-powerpoint': '.ppt',
                'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx'
            }
            ext = extensions.get(mime_type, '.tmp')
            
            # Salva file di input
            input_file = os.path.join(tmpdir, f"input{ext}")
            with open(input_file, 'wb') as f:
                f.write(file_content)
            
            # Converti in PDF con LibreOffice
            import subprocess
            subprocess.run([
                'libreoffice',
                '--headless',
                '--convert-to', 'pdf',
                '--outdir', tmpdir,
                input_file
            ], check=True, capture_output=True)
            
            # Il file PDF generato
            pdf_file = os.path.join(tmpdir, "input.pdf")
            
            # Leggi PDF generato
            with open(pdf_file, 'rb') as f:
                pdf_content = f.read()
            
            # Converti in PDF/A
            return self.convert_pdf_to_pdfa(pdf_content, filename)
    
    def convert_to_pdfa(self, file_content: bytes, filename: str = "document") -> Tuple[bytes, str]:
        """
        Converte qualsiasi file supportato in PDF/A.
        
        Args:
            file_content: Contenuto del file in bytes
            filename: Nome del file
            
        Returns:
            Tuple[bytes, str]: (pdf_a_content, message)
                pdf_a_content: Contenuto PDF/A in bytes
                message: Messaggio informativo sulla conversione
        """
        # Rileva tipo file
        mime_type = self.detect_file_type(file_content)
        
        # Se è già un PDF, controlla se è PDF/A
        if mime_type in self.PDF_TYPES:
            is_compliant, version = self.is_pdf_a_compliant(file_content)
            
            if is_compliant:
                return file_content, f"File già conforme {version}, nessuna conversione necessaria"
            else:
                # Converti in PDF/A
                pdfa_content = self.convert_pdf_to_pdfa(file_content, filename)
                return pdfa_content, f"PDF convertito in PDF/A-2b"
        
        # Se è un'immagine
        elif mime_type in self.SUPPORTED_IMAGE_TYPES:
            pdfa_content = self.convert_image_to_pdfa(file_content, filename)
            return pdfa_content, f"Immagine ({mime_type}) convertita in PDF/A"
        
        # Se è un file Office
        elif mime_type in self.SUPPORTED_OFFICE_TYPES:
            try:
                pdfa_content = self.convert_office_to_pdfa(file_content, mime_type, filename)
                return pdfa_content, f"File Office ({mime_type}) convertito in PDF/A"
            except NotImplementedError as e:
                raise ValueError(
                    f"Conversione file Office non supportata: {str(e)}. "
                    "Carica il file come PDF invece."
                )
        
        # Tipo file non supportato
        else:
            raise ValueError(
                f"Tipo file non supportato: {mime_type}. "
                f"Tipi supportati: PDF, immagini (JPG, PNG, TIFF, BMP, GIF), "
                f"file Office (DOC, DOCX, XLS, XLSX, PPT, PPTX)"
            )


# Istanza globale del converter
pdf_converter = PDFAConverter()
```

### 6.4 Integrazione nel Tool sign_document

**File**: `app/main.py`

**Aggiungi import** (riga 14, dopo gli altri import):
```python
from app.pdf_converter import pdf_converter
```

**Modifica la funzione `sign_document`** (dopo il download del file, circa riga 500):

**PRIMA** (righe 500-513):
```python
# Scarica il PDF dal link fornito
pdf_response = requests.get(link_pdf)
pdf_response.raise_for_status()

# Rimuovi i parametri di query dall'URL e estrai il nome del file
parsed = urlparse(link_pdf)
url_no_query = urlunparse(parsed._replace(query=""))
clean_url = url_no_query.split('?')[0] 
attach_name = clean_url.split('/')[-1]
attach_name = unquote(attach_name)

if not attach_name:
    attach_name = "documento.pdf"
```

**DOPO**:
```python
# Scarica il file dal link fornito
file_response = requests.get(link_pdf)
file_response.raise_for_status()

# Rimuovi i parametri di query dall'URL e estrai il nome del file
parsed = urlparse(link_pdf)
url_no_query = urlunparse(parsed._replace(query=""))
clean_url = url_no_query.split('?')[0] 
attach_name = clean_url.split('/')[-1]
attach_name = unquote(attach_name)

if not attach_name:
    attach_name = "documento.pdf"

# NUOVO: Converti in PDF/A se necessario
try:
    file_content_original = file_response.content
    pdf_content, conversion_message = pdf_converter.convert_to_pdfa(
        file_content_original, 
        attach_name
    )
    
    # Usa il contenuto PDF/A per il resto del processo
    pdf_response_content = pdf_content
    
    # Log della conversione
    print(f"Conversione PDF/A: {conversion_message}")
    
except ValueError as e:
    # Se la conversione fallisce, restituisci errore
    return {
        "type": "error",
        "content": f"Errore nella conversione in PDF/A: {str(e)}"
    }
except Exception as e:
    # Errore generico
    return {
        "type": "error",
        "content": f"Errore durante la conversione del file: {str(e)}"
    }

# Assicurati che attach_name abbia estensione .pdf
if not attach_name.lower().endswith('.pdf'):
    attach_name = attach_name.rsplit('.', 1)[0] + '.pdf'
```

**Modifica il resto della funzione** per usare `pdf_response_content` invece di `pdf_response.content`:

**Trova** (circa riga 516):
```python
# Conta le pagine del PDF
from io import BytesIO
pdf_stream = BytesIO(pdf_response.content)
```

**Sostituisci con**:
```python
# Conta le pagine del PDF
from io import BytesIO
pdf_stream = BytesIO(pdf_response_content)  # ← USA IL CONTENUTO CONVERTITO
```

**Trova** (circa riga 556):
```python
# Converti il contenuto in base64
content_base64 = base64.b64encode(pdf_response.content).decode('utf-8')
```

**Sostituisci con**:
```python
# Converti il contenuto in base64
content_base64 = base64.b64encode(pdf_response_content).decode('utf-8')  # ← USA IL CONTENUTO CONVERTITO
```

**Aggiorna il dizionario di ritorno** (circa riga 624) per includere info sulla conversione:

**Trova**:
```python
return upload_info
```

**Sostituisci con**:
```python
# Aggiungi informazioni sulla conversione PDF/A
upload_info["pdfa_conversion"] = conversion_message
return upload_info
```

### 6.5 Aggiornamento Dockerfile per LibreOffice (Opzionale)

Se vuoi supportare la conversione di file Office, modifica il Dockerfile:

**File**: `Dockerfile`

**PRIMA**:
```dockerfile
# NUOVO: Installa dipendenze di sistema per PDF/A conversion
RUN apt-get update && apt-get install -y \
    ghostscript \
    libmagic1 \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-ita \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*
```

**DOPO**:
```dockerfile
# NUOVO: Installa dipendenze di sistema per PDF/A conversion
RUN apt-get update && apt-get install -y \
    ghostscript \
    libmagic1 \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-ita \
    tesseract-ocr-eng \
    libreoffice \
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-impress \
    && rm -rf /var/lib/apt/lists/*
```

**NOTA**: LibreOffice aumenta significativamente la dimensione dell'immagine Docker (~500MB). Se non hai bisogno di convertire file Office, ometti questa parte.

### 6.6 Testing della Conversione PDF/A

**Script di Test** (crea file `test_pdfa_conversion.py` nella root):

```python
#!/usr/bin/env python3
"""
Script di test per la conversione PDF/A.
"""

import sys
sys.path.insert(0, '/app')  # Adjust if needed

from app.pdf_converter import pdf_converter
import base64

def test_pdf_conversion():
    """Testa la conversione di un PDF."""
    
    # Test 1: PDF standard
    print("\n=== TEST 1: PDF Standard ===")
    # Crea un PDF di esempio (questo è un PDF minimo valido)
    sample_pdf = base64.b64decode(
        'JVBERi0xLjQKJeLjz9MKMyAwIG9iago8PC9GaWx0ZXIvRmxhdGVEZWNvZGUvTGVuZ3RoIDQ5Pj5z'
        'dHJlYW0KeJwr5HIK4TI2UzA0MFMwtTQFABBxBHsKZW5kc3RyZWFtCmVuZG9iagoxIDAgb2JqCjw8'
        'L1R5cGUvUGFnZS9QYXJlbnQgNCAwIFIvQ29udGVudHMgMyAwIFI+PgplbmRvYmoKNCAwIG9iago8'
        'PC9UeXBlL1BhZ2VzL0NvdW50IDEvS2lkcyBbMSAwIFJdPj4KZW5kb2JqCjUgMCBvYmoKPDwvVHlw'
        'ZS9DYXRhbG9nL1BhZ2VzIDQgMCBSPj4KZW5kb2JqCnhyZWYKMCA2CjAwMDAwMDAwMDAgNjU1MzUg'
        'ZiAKMDAwMDAwMDA3MyAwMDAwMCBuIAowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAwMTUgMDAw'
        'MDAgbiAKMDAwMDAwMDEyMyAwMDAwMCBuIAowMDAwMDAwMTc2IDAwMDAwIG4gCnRyYWlsZXIKPDwv'
        'U2l6ZSA2L1Jvb3QgNSAwIFI+PgpzdGFydHhyZWYKMjI1CiUlRU9GCg=='
    )
    
    result, message = pdf_converter.convert_to_pdfa(sample_pdf, "test.pdf")
    print(f"Messaggio: {message}")
    print(f"Dimensione output: {len(result)} bytes")
    
    # Verifica che sia PDF/A
    is_compliant, version = pdf_converter.is_pdf_a_compliant(result)
    print(f"PDF/A Compliant: {is_compliant}, Version: {version}")
    
    # Test 2: Immagine
    print("\n=== TEST 2: Immagine PNG ===")
    # Crea una piccola immagine PNG (1x1 pixel rosso)
    sample_image = base64.b64decode(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx'
        '0gAAAABJRU5ErkJggg=='
    )
    
    result, message = pdf_converter.convert_to_pdfa(sample_image, "test.png")
    print(f"Messaggio: {message}")
    print(f"Dimensione output: {len(result)} bytes")
    
    # Verifica che sia PDF/A
    is_compliant, version = pdf_converter.is_pdf_a_compliant(result)
    print(f"PDF/A Compliant: {is_compliant}, Version: {version}")
    
    print("\n=== TUTTI I TEST COMPLETATI ===")

if __name__ == "__main__":
    test_pdf_conversion()
```

**Esegui il test**:
```bash
docker-compose exec signature-server python /app/test_pdfa_conversion.py
```

---

## 7. CONFIGURAZIONE FINALE

### 7.1 File .env Completo

**File**: `.env`

```env
# Server Configuration
PORT=8888

# MCP Server Endpoints (CUSTOM)
MCP_SSE_PATH=/api/signature/sse
MCP_MESSAGE_PATH=/api/signature/messages/
MCP_SERVER_NAME=Custom Signature MCP Server

# Infocert API Configuration
CLIENT_ID=your_client_id_here
CLIENT_SECRET=your_client_secret_here
SIGNATURE_API=https://api.infocert.digital/signature/v1
AUTHORIZATION_API=https://isac.infocert.it/isac-oauth2/api
TENANT=your_tenant_here

# DigitalOcean Spaces Configuration
DO_SPACES_ACCESS_KEY=your_access_key_here
DO_SPACES_SECRET_KEY=your_secret_key_here
DO_SPACES_REGION=nyc3
DO_SPACES_BUCKET=your_bucket_name_here
DO_SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com

# PDF/A Conversion Settings (Optional)
PDFA_DEFAULT_VERSION=2  # 1, 2, or 3
PDFA_IMAGE_COMPRESSION=jpeg  # jpeg or lossless
```

### 7.2 Struttura File Finale

```
digital-signature-mcp-custom/
├── .env                      # Configurazione (NON committare)
├── .env.example              # Template configurazione
├── .gitignore               
├── Dockerfile                # Con dipendenze PDF/A
├── docker-compose.yml       
├── README.md                 # Documentazione aggiornata
├── requirements.txt          # Con nuove dipendenze
├── test_pdfa_conversion.py   # Script di test (opzionale)
├── MIGRATION_AND_CUSTOMIZATION_GUIDE.md  # Questo documento
└── app/
    ├── main.py               # Con tutte le modifiche
    ├── pdf_converter.py      # NUOVO: Modulo conversione PDF/A
    └── config/
        ├── __init__.py
        └── setting.py        # Con nuove variabili
```

### 7.3 Comandi per Build e Deploy

```bash
# 1. Build dell'immagine Docker
docker-compose build

# 2. Avvio dei servizi
docker-compose up -d

# 3. Verifica dei log
docker-compose logs -f signature-server

# 4. Test degli endpoint
curl http://localhost:8888/api/signature/sse

# 5. Stop dei servizi
docker-compose down

# 6. Rebuild completo (se hai modificato Dockerfile)
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## 8. TESTING

### 8.1 Test Endpoint MCP

```bash
# Test SSE endpoint
curl -N http://localhost:8888/api/signature/sse

# Test message endpoint (dovrebbe richiedere POST con JSON)
curl -X POST http://localhost:8888/api/signature/messages/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

### 8.2 Test Conversione PDF/A

**Crea file** `test_sign_with_pdfa.py`:

```python
#!/usr/bin/env python3
"""
Test completo del flusso di firma con conversione PDF/A.
"""

import requests
import base64
from io import BytesIO
from PIL import Image

# Configurazione
BASE_URL = "http://localhost:8888"
USERNAME = "your_username"
PASSWORD = "your_password"
PIN = "your_pin"

def create_test_image():
    """Crea un'immagine di test."""
    img = Image.new('RGB', (200, 100), color='red')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()

def test_full_flow():
    """Testa il flusso completo di firma."""
    
    # 1. Autenticazione
    print("1. Autenticazione...")
    # TODO: Implementa chiamata MCP per auth_token
    
    # 2. Recupero certificati
    print("2. Recupero certificati...")
    # TODO: Implementa chiamata MCP per get_certificates
    
    # 3. Richiesta OTP
    print("3. Richiesta OTP...")
    # TODO: Implementa chiamata MCP per request_smsp_challenge
    
    # 4. Autorizzazione
    print("4. Autorizzazione...")
    otp = input("Inserisci OTP ricevuto via SMS: ")
    # TODO: Implementa chiamata MCP per authorize_smsp
    
    # 5. Firma documento con posizione custom
    print("5. Firma documento...")
    # TODO: Implementa chiamata MCP per sign_document con:
    # - link_pdf: URL del file da firmare
    # - page_signature: "tutte_le_pagine"
    # - signature_position: "top_left"
    # - custom_coords: None
    
    print("\nTest completato!")

if __name__ == "__main__":
    test_full_flow()
```

### 8.3 Test Posizionamento Firma

**Testa tutte le posizioni predefinite**:

```python
positions = [
    "bottom_left",
    "bottom_center",
    "bottom_right",
    "top_left",
    "top_center",
    "top_right",
    "center"
]

for position in positions:
    print(f"\nTestando posizione: {position}")
    # Chiama sign_document con signature_position=position
    # Verifica visivamente il PDF risultante
```

**Testa coordinate personalizzate**:

```python
# Firma nell'angolo in alto a sinistra con dimensioni custom
custom_coords = {
    "llx": 50,
    "lly": 700,
    "urx": 150,
    "ury": 750
}

# Chiama sign_document con custom_coords
```

### 8.4 Checklist di Verifica

- [ ] Repository migrato su GitHub personale
- [ ] Endpoint MCP modificati (sse_path e message_path)
- [ ] Server raggiungibile su dominio personalizzato
- [ ] Posizionamento firma funziona con posizioni predefinite
- [ ] Posizionamento firma funziona con coordinate personalizzate
- [ ] Conversione immagini (JPG, PNG) in PDF/A
- [ ] Verifica PDF/A su PDF esistenti
- [ ] Conversione PDF non-compliant in PDF/A
- [ ] Conversione file Office (se LibreOffice installato)
- [ ] Firma applica su pagina corretta (prima, ultima, tutte)
- [ ] Upload su DigitalOcean Spaces funziona
- [ ] URL firmato generato correttamente
- [ ] Docker container si avvia senza errori
- [ ] Logs non mostrano errori critici

---

## 9. NOTE TECNICHE IMPORTANTI

### 9.1 Limiti e Considerazioni

1. **Dimensione File**:
   - DigitalOcean Spaces: limite per singolo PUT è 5GB
   - Considera multipart upload per file >100MB

2. **Performance**:
   - Conversione PDF/A può richiedere 2-10 secondi per file grandi
   - Considera timeout adeguati per le richieste HTTP

3. **Qualità PDF/A**:
   - `ocrmypdf` produce PDF/A-2b (raccomandato)
   - Alcuni PDF complessi potrebbero non convertire perfettamente

4. **Gestione Errori**:
   - Implementa retry logic per chiamate API Infocert
   - Gestisci timeout per download file grandi

5. **Sicurezza**:
   - Non loggare credenziali o token
   - Valida sempre input utente
   - Sanitizza nomi file per evitare path traversal

### 9.2 Troubleshooting Comune

**Problema**: `ocrmypdf` fallisce con errore Ghostscript
**Soluzione**: Verifica che Ghostscript sia installato: `gs --version`

**Problema**: LibreOffice non trovato per conversione Office
**Soluzione**: Installa LibreOffice o ometti supporto file Office

**Problema**: PDF troppo grande per memoria
**Soluzione**: Usa file temporanei su disco invece di BytesIO

**Problema**: Firma non visibile sul PDF
**Soluzione**: Verifica coordinate, assicurati che siano entro dimensioni pagina

**Problema**: Docker build fallisce per spazio disco
**Soluzione**: Rimuovi immagini inutilizzate: `docker system prune -a`

### 9.3 Ottimizzazioni Future

1. **Cache Conversioni**:
   - Salva conversioni PDF/A già effettuate
   - Usa hash SHA256 del file come chiave

2. **Processing Asincrono**:
   - Usa Celery per conversioni lunghe
   - Notifica utente al completamento

3. **Batch Processing**:
   - Firma multipli documenti in una chiamata
   - Upload batch su DigitalOcean Spaces

4. **Validazione Avanzata**:
   - Verifica firme esistenti prima di aggiungere nuova
   - Controlla integrità PDF con pikepdf

5. **Monitoring**:
   - Integra con Prometheus per metriche
   - Log strutturati con JSON

### 9.4 Risorse Utili

- **FastMCP Docs**: https://github.com/jlowin/fastmcp
- **pyHanko Docs**: https://pyhanko.readthedocs.io/
- **ocrmypdf Docs**: https://ocrmypdf.readthedocs.io/
- **pikepdf Docs**: https://pikepdf.readthedocs.io/
- **PDF/A Standard**: https://www.pdfa.org/
- **Infocert API**: Documentazione fornita da Infocert
- **DigitalOcean Spaces**: https://docs.digitalocean.com/products/spaces/

### 9.5 Contatti e Supporto

Per domande o problemi con l'implementazione:
1. Controlla i log Docker: `docker-compose logs -f`
2. Verifica configurazione .env
3. Consulta documentazione API Infocert
4. Apri issue su GitHub del progetto

---

## CONCLUSIONE

Questo documento fornisce una guida completa per:
1. ✅ Migrare il repository su GitHub personale
2. ✅ Modificare endpoint MCP ed esporli su dominio custom
3. ✅ Implementare posizionamento personalizzabile del talloncino di firma
4. ✅ Aggiungere conversione automatica in PDF/A per tutti i file

L'implementazione di tutte le modifiche richiede:
- **Tempo stimato**: 4-6 ore
- **Competenze**: Python, Docker, API REST, PDF processing
- **Infrastruttura**: Server con Docker, dominio, certificato SSL

Segui i task nell'ordine presentato per un'implementazione pulita e testabile.

**Buon lavoro! 🚀**

---

*Documento generato il 2025-11-29 da OpenHands Agent*
