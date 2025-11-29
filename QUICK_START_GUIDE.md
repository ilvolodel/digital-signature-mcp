# Quick Start Guide - Personalizzazione Digital Signature MCP

## 🎯 Obiettivo

Personalizzare il server MCP per firma digitale con:
1. ✅ Repository su GitHub personale
2. ✅ Endpoint custom su dominio personale
3. ✅ Posizionamento firma personalizzabile
4. ✅ Conversione automatica in PDF/A

---

## 📚 Documentazione

- **Guida Completa (75+ pagine)**: `MIGRATION_AND_CUSTOMIZATION_GUIDE.md`
- **Analisi Tecnica**: `SUMMARY_ANALYSIS.md`
- **Quick Start**: Questo file

---

## ⚡ Quick Commands

### 1. Migrazione su GitHub (5 minuti)

```bash
# Entra nella directory
cd /workspace/digital-signature-mcp

# Rimuovi remote originale
git remote remove origin

# Aggiungi il TUO remote (SOSTITUISCI <USERNAME> e <REPO>)
git remote add origin https://github.com/<USERNAME>/<REPO>.git

# Push
git push -u origin main
```

### 2. Modifica Endpoint (15 minuti)

**File: `app/config/setting.py`** - Aggiungi alla fine:
```python
    # MCP Server configuration
    MCP_SSE_PATH: str = "/digital-signature/sse"
    MCP_MESSAGE_PATH: str = "/digital-signature/messages/"
    MCP_SERVER_NAME: str = "Signature MCP Server"
```

**File: `app/main.py`** - Modifica righe 16-23:
```python
mcp = FastMCP(
    name=settings.MCP_SERVER_NAME,
    sse_path=settings.MCP_SSE_PATH,
    message_path=settings.MCP_MESSAGE_PATH,
    initialization_timeout=120,
    max_retries=10,
    retry_delay=5
)
```

**File: `.env`** - Aggiungi:
```env
MCP_SSE_PATH=/api/signature/sse
MCP_MESSAGE_PATH=/api/signature/messages/
MCP_SERVER_NAME=Custom Signature Server
```

### 3. Posizionamento Firma (30 minuti)

**Copia la funzione `get_signature_position()` dalla guida completa**  
Cerca in `MIGRATION_AND_CUSTOMIZATION_GUIDE.md` sezione 5.4

**Modifica `sign_document()` signature** (riga 442):
- Aggiungi parametro `signature_position`
- Aggiungi parametro `custom_coords`

**Modifica loop signature_fields** (riga 566):
- Usa `get_signature_position()` invece di coordinate hardcoded

### 4. Conversione PDF/A (1-2 ore)

**File: `requirements.txt`** - Aggiungi:
```txt
pikepdf==9.4.2
ocrmypdf==16.5.0
pillow==11.0.0
pypdf==5.1.0
python-magic==0.4.27
pdf2image==1.17.0
reportlab==4.2.5
```

**File: `Dockerfile`** - Modifica:
```dockerfile
# Dopo la riga FROM python:3.12-slim
RUN apt-get update && apt-get install -y \
    ghostscript \
    libmagic1 \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*
```

**Crea file: `app/pdf_converter.py`**  
Copia il codice completo dalla guida (sezione 6.3)

**Modifica `app/main.py`**:
- Aggiungi import: `from app.pdf_converter import pdf_converter`
- Integra conversione in `sign_document()` (dopo download file)

### 5. Build e Test (10 minuti)

```bash
# Rebuild Docker
docker-compose build --no-cache

# Avvia servizi
docker-compose up -d

# Verifica logs
docker-compose logs -f signature-server

# Test endpoint
curl http://localhost:8888/api/signature/sse
```

---

## 📋 Checklist Veloce

```
Fase 1: Migrazione
[ ] Remote git modificato
[ ] Push su GitHub personale
[ ] Verificato git log

Fase 2: Endpoint
[ ] Modificato setting.py
[ ] Modificato main.py (FastMCP config)
[ ] Aggiornato .env
[ ] Testato endpoint SSE

Fase 3: Firma
[ ] Creata funzione get_signature_position()
[ ] Modificata signature sign_document()
[ ] Modificato loop signature_fields
[ ] Testato posizioni predefinite

Fase 4: PDF/A
[ ] Aggiornato requirements.txt
[ ] Aggiornato Dockerfile
[ ] Creato pdf_converter.py
[ ] Integrato in sign_document()
[ ] Rebuild Docker
[ ] Testato conversione

Fase 5: Deploy
[ ] Server in produzione
[ ] Nginx configurato
[ ] SSL attivo
[ ] Test completo
```

---

## 🚀 Esempio Utilizzo Finale

```python
# Firma con posizione personalizzata e conversione PDF/A automatica

sign_document(
    certificate_id="123456",
    access_token="...",
    infocert_sat="...",
    transaction_id="...",
    pin="1234",
    
    # Supporta URL di qualsiasi file (non solo PDF!)
    link_pdf="https://example.com/documento.jpg",  # ← Immagine!
    
    # Scelta pagine
    page_signature="ultima_pagina",
    
    # Scelta posizione (NUOVO!)
    signature_position="top_left",
    
    # Oppure coordinate custom (NUOVO!)
    custom_coords={"llx": 100, "lly": 700, "urx": 200, "ury": 750}
)

# Risultato:
# - File convertito in PDF/A-2b
# - Firmato digitalmente PAdES BASELINE-B
# - Talloncino posizionato in alto a sinistra (o coordinate custom)
# - Upload su DigitalOcean Spaces
# - URL firmato valido 60 minuti
```

---

## 🔍 Posizioni Predefinite

| Posizione | Dove Appare |
|-----------|-------------|
| `bottom_left` | 📍 Basso a sinistra |
| `bottom_center` | 📍 Basso al centro |
| `bottom_right` | 📍 Basso a destra (default attuale) |
| `top_left` | 📍 Alto a sinistra |
| `top_center` | 📍 Alto al centro |
| `top_right` | 📍 Alto a destra |
| `center` | 📍 Centro pagina |

---

## 🆘 Troubleshooting Rapido

**Errore: ocrmypdf not found**
```bash
# Nel Dockerfile, verifica che ci sia:
RUN apt-get install -y ghostscript
```

**Errore: libmagic not found**
```bash
# Nel Dockerfile, verifica che ci sia:
RUN apt-get install -y libmagic1
```

**Firma non visibile**
```bash
# Verifica coordinate:
# - llx/lly = Lower Left (in basso a sinistra)
# - urx/ury = Upper Right (in alto a destra)
# - Pagina A4: 595 x 842 punti
# - Coordinate devono essere: 0 < llx < urx < 595, 0 < lly < ury < 842
```

**PDF/A conversione fallisce**
```bash
# Test Ghostscript:
docker-compose exec signature-server gs --version

# Test ocrmypdf:
docker-compose exec signature-server ocrmypdf --version

# Logs dettagliati:
docker-compose logs -f signature-server | grep -i "error\|warning"
```

---

## 🔗 Link Utili

- **Guida Completa**: [MIGRATION_AND_CUSTOMIZATION_GUIDE.md](./MIGRATION_AND_CUSTOMIZATION_GUIDE.md)
- **Analisi Tecnica**: [SUMMARY_ANALYSIS.md](./SUMMARY_ANALYSIS.md)
- **Repository Originale**: https://github.com/AI-Blackbird/digital-signature-mcp

---

## ⏱️ Tempo Stimato Totale

- **Minimo (senza PDF/A)**: 1-2 ore
- **Completo (con tutto)**: 4-6 ore
- **Con testing approfondito**: 7-12 ore

---

## 💡 Suggerimenti

1. **Procedi step by step**: Non saltare i task
2. **Testa ogni modifica**: Prima di passare alla successiva
3. **Backup frequenti**: `git commit` dopo ogni task completato
4. **Leggi i logs**: `docker-compose logs -f` è tuo amico
5. **Consulta la guida completa**: Per dettagli implementativi

---

**Buona fortuna! 🎉**

*Per domande dettagliate, consulta sempre la guida completa: `MIGRATION_AND_CUSTOMIZATION_GUIDE.md`*
