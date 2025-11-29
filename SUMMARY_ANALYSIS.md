# Analisi Repository: digital-signature-mcp

## Data Analisi: 2025-11-29

---

## SOMMARIO ESECUTIVO

Il repository **digital-signature-mcp** è un server MCP (Model Context Protocol) per la firma digitale di documenti PDF utilizzando le API di Infocert, con caricamento automatico su DigitalOcean Spaces.

### Stato Attuale
- ✅ Funzionante e completo per firma digitale PAdES
- ✅ Integrazione con Infocert API
- ✅ Upload automatico su DigitalOcean Spaces
- ❌ NON supporta conversione PDF/A
- ❌ Posizionamento firma HARDCODED
- ❌ Endpoint MCP non personalizzabili

---

## OBIETTIVI DI PERSONALIZZAZIONE

### 1. Migrazione Repository ✅
**Complessità**: Bassa (15-30 minuti)

Clonare il repository e ripubblicarlo sul tuo GitHub personale.

**Comandi chiave**:
```bash
git remote remove origin
git remote add origin https://github.com/<TUO_USERNAME>/<TUO_REPO>.git
git push -u origin main
```

### 2. Modifica Endpoint e Dominio ✅
**Complessità**: Media (1-2 ore)

Modificare i path MCP (`/digital-signature/*` → `/<TUO_PATH>/*`) ed esporli su dominio personalizzato tramite Nginx reverse proxy.

**File da modificare**:
- `app/main.py`: Configurazione FastMCP
- `app/config/setting.py`: Aggiungere variabili `MCP_SSE_PATH`, `MCP_MESSAGE_PATH`
- `.env`: Nuove variabili di configurazione
- Nginx config: Reverse proxy con SSL

### 3. Posizionamento Talloncino Personalizzabile ✅
**Complessità**: Media (2-3 ore)

Attualmente le coordinate sono hardcoded (llx=500, lly=60, urx=580, ury=90).

**Implementazione**:
- Creare funzione `get_signature_position()` con posizioni predefinite:
  - `bottom_left`, `bottom_center`, `bottom_right`
  - `top_left`, `top_center`, `top_right`
  - `center`
- Aggiungere parametro `signature_position` al tool `sign_document`
- Supportare coordinate personalizzate con parametro `custom_coords`

**Esempio uso**:
```python
sign_document(
    ...,
    signature_position="top_left",
    custom_coords={"llx": 100, "lly": 700, "urx": 200, "ury": 750}
)
```

### 4. Conversione Automatica in PDF/A ✅
**Complessità**: Alta (3-4 ore)

Implementare conversione automatica di tutti i file in PDF/A prima della firma.

**Requisiti**:
- Supporto immagini: JPG, PNG, TIFF, BMP, GIF → PDF/A
- Supporto Office: DOC, DOCX, XLS, XLSX, PPT, PPTX → PDF/A (richiede LibreOffice)
- Verifica PDF esistenti: Se già PDF/A, skip conversione
- Conversione PDF standard → PDF/A-2b

**Nuove dipendenze**:
- `pikepdf` 9.4.2: Manipolazione e verifica PDF
- `ocrmypdf` 16.5.0: Conversione in PDF/A
- `pillow` 11.0.0: Gestione immagini
- `python-magic` 0.4.27: Rilevamento MIME type
- Ghostscript (system): Richiesto da ocrmypdf
- LibreOffice (optional): Per conversione file Office

**File da creare**:
- `app/pdf_converter.py`: Modulo conversione completo (~400 righe)

**File da modificare**:
- `app/main.py`: Integrazione conversione prima della firma
- `requirements.txt`: Aggiungere nuove dipendenze
- `Dockerfile`: Installare Ghostscript, LibreOffice

---

## ARCHITETTURA ATTUALE

```
┌─────────────────────────────────────────────────────────────┐
│                     MCP Client (Cline, Claude)              │
└────────────────────────┬────────────────────────────────────┘
                         │ SSE/Messages
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              FastMCP Server (app/main.py)                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Tools:                                              │   │
│  │  - auth_token                                        │   │
│  │  - get_certificates                                  │   │
│  │  - request_smsp_challenge                            │   │
│  │  - authorize_smsp                                    │   │
│  │  - sign_document                                     │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────┬────────────────────────────────┬─────────────────┘
           │                                │
           │ HTTPS                          │ S3 API
           ▼                                ▼
┌──────────────────────┐      ┌──────────────────────────┐
│   Infocert API       │      │  DigitalOcean Spaces     │
│   - OAuth2           │      │  - PDF firmati           │
│   - Firma PAdES      │      │  - URL firmati (60min)   │
└──────────────────────┘      └──────────────────────────┘
```

---

## ARCHITETTURA FUTURA (CON MODIFICHE)

```
┌─────────────────────────────────────────────────────────────┐
│                     MCP Client (Cline, Claude)              │
└────────────────────────┬────────────────────────────────────┘
                         │ SSE/Messages (CUSTOM ENDPOINTS)
                         │ /api/signature/sse
                         │ /api/signature/messages/
                         ▼
┌──────────────────────────────────────────────────────────┐
│                 Nginx Reverse Proxy                       │
│              (tuo-dominio.com + SSL)                      │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│        FastMCP Server (app/main.py) - MODIFICATO           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Tools (ENHANCED):                                   │   │
│  │  - auth_token                                        │   │
│  │  - get_certificates                                  │   │
│  │  - request_smsp_challenge                            │   │
│  │  - authorize_smsp                                    │   │
│  │  - sign_document (+ signature_position + PDF/A)     │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  NEW: pdf_converter.py                              │   │
│  │  - convert_to_pdfa()                                 │   │
│  │  - is_pdf_a_compliant()                              │   │
│  │  - convert_image_to_pdfa()                           │   │
│  │  - convert_pdf_to_pdfa()                             │   │
│  │  - convert_office_to_pdfa()                          │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────┬────────────────────────────────┬─────────────────┘
           │                                │
           │ HTTPS                          │ S3 API
           ▼                                ▼
┌──────────────────────┐      ┌──────────────────────────┐
│   Infocert API       │      │  DigitalOcean Spaces     │
│   - OAuth2           │      │  - PDF/A firmati         │
│   - Firma PAdES      │      │  - URL firmati (60min)   │
└──────────────────────┘      └──────────────────────────┘
```

---

## FLUSSO DI FIRMA ATTUALE

```
1. auth_token(username, password)
   └─> access_token

2. get_certificates(access_token)
   └─> certificate_id, subject_info

3. request_smsp_challenge(access_token)
   └─> transaction_id

4. Utente riceve SMS con OTP

5. authorize_smsp(access_token, certificate_id, transaction_id, otp, pin)
   └─> infocert_sat (SAT token)

6. sign_document(certificate_id, access_token, infocert_sat, 
                 transaction_id, pin, link_pdf, page_signature)
   ├─> Download PDF da link_pdf
   ├─> Converti in base64
   ├─> Firma con Infocert API (PAdES BASELINE-B)
   ├─> Posiziona talloncino (HARDCODED: llx=500, lly=60)
   ├─> Upload su DigitalOcean Spaces
   └─> Restituisci URL firmato (60 min)
```

---

## FLUSSO DI FIRMA FUTURO (CON MODIFICHE)

```
1. auth_token(username, password)
   └─> access_token

2. get_certificates(access_token)
   └─> certificate_id, subject_info

3. request_smsp_challenge(access_token)
   └─> transaction_id

4. Utente riceve SMS con OTP

5. authorize_smsp(access_token, certificate_id, transaction_id, otp, pin)
   └─> infocert_sat (SAT token)

6. sign_document(certificate_id, access_token, infocert_sat, 
                 transaction_id, pin, link_pdf, page_signature,
                 signature_position, custom_coords)      ← NEW PARAMS
   ├─> Download FILE da link_pdf (non solo PDF!)        ← MODIFICATO
   │
   ├─> NUOVO: Conversione in PDF/A
   │   ├─> Rileva MIME type (magic)
   │   ├─> Se immagine → PDF/A con ReportLab + ocrmypdf
   │   ├─> Se Office → PDF con LibreOffice → PDF/A
   │   ├─> Se PDF → Verifica conformità PDF/A
   │   │   ├─> Se già PDF/A → Skip conversione
   │   │   └─> Se non PDF/A → Converti con ocrmypdf
   │   └─> Risultato: PDF/A-2b garantito
   │
   ├─> Converti PDF/A in base64
   │
   ├─> Firma con Infocert API (PAdES BASELINE-B)
   │
   ├─> NUOVO: Posiziona talloncino (CONFIGURABILE)
   │   ├─> Se custom_coords → Usa coordinate fornite
   │   └─> Se signature_position → Usa posizione predefinita
   │       (bottom_left, bottom_center, bottom_right,
   │        top_left, top_center, top_right, center)
   │
   ├─> Upload PDF/A firmato su DigitalOcean Spaces
   │
   └─> Restituisci URL firmato (60 min) + info conversione
```

---

## MODIFICHE FILE PER FILE

### File da Modificare

1. **`app/config/setting.py`**
   - Aggiungere: `MCP_SSE_PATH`, `MCP_MESSAGE_PATH`, `MCP_SERVER_NAME`

2. **`app/main.py`** (MODIFICHE SIGNIFICATIVE)
   - Riga 16-23: Usare variabili da settings invece di hardcode
   - Riga 203: Aggiungere funzione `get_signature_position()`
   - Riga 442: Modificare signature di `sign_document()` (nuovi parametri)
   - Riga 500-513: Integrare conversione PDF/A
   - Riga 566-581: Usare coordinate dinamiche per firma

3. **`requirements.txt`**
   - Aggiungere: pikepdf, ocrmypdf, pillow, pypdf, python-magic, pdf2image, reportlab

4. **`Dockerfile`**
   - Aggiungere installazione: ghostscript, libmagic1, poppler-utils, tesseract-ocr
   - Opzionale: libreoffice (per file Office)

5. **`docker-compose.yml`**
   - Aggiungere environment variables per MCP paths

6. **`.env.example`**
   - Aggiungere template per: MCP_SSE_PATH, MCP_MESSAGE_PATH, MCP_SERVER_NAME

### File da Creare

1. **`app/pdf_converter.py`** (NUOVO - ~400 righe)
   - Classe `PDFAConverter`
   - Metodi:
     - `detect_file_type(file_content)`: Rileva MIME type
     - `is_pdf_a_compliant(pdf_content)`: Verifica PDF/A
     - `convert_image_to_pdfa(image_content)`: Immagini → PDF/A
     - `convert_pdf_to_pdfa(pdf_content)`: PDF → PDF/A
     - `convert_office_to_pdfa(file_content, mime_type)`: Office → PDF/A
     - `convert_to_pdfa(file_content)`: Dispatcher principale

2. **`test_pdfa_conversion.py`** (OPZIONALE - test)
   - Script di test per verificare conversioni

3. **`MIGRATION_AND_CUSTOMIZATION_GUIDE.md`** (CREATO ✅)
   - Guida completa per implementare le modifiche

---

## DIPENDENZE E INSTALLAZIONE

### Dipendenze Python (requirements.txt)

**Attuali**:
```
fastmcp==2.2.4
requests==2.32.3
pydantic==2.11.4
pydantic-settings==2.8.1
boto3==1.40.32
pyHanko==0.31.0
```

**Da Aggiungere**:
```
pikepdf==9.4.2
ocrmypdf==16.5.0
pillow==11.0.0
pypdf==5.1.0
python-magic==0.4.27
pdf2image==1.17.0
reportlab==4.2.5
```

### Dipendenze Sistema (Dockerfile)

**Da Aggiungere**:
```bash
apt-get install -y \
    ghostscript \
    libmagic1 \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-ita \
    tesseract-ocr-eng
```

**Opzionale (per file Office)**:
```bash
apt-get install -y \
    libreoffice \
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-impress
```

---

## STIMA TEMPO E COMPLESSITÀ

| Task | Tempo Stimato | Complessità | Priorità |
|------|---------------|-------------|----------|
| 1. Migrazione GitHub | 15-30 min | Bassa | Alta |
| 2. Modifica Endpoint | 1-2 ore | Media | Alta |
| 3. Posizionamento Firma | 2-3 ore | Media | Alta |
| 4. Conversione PDF/A | 3-4 ore | Alta | Alta |
| Testing Completo | 1-2 ore | Media | Alta |
| **TOTALE** | **7-12 ore** | **Media-Alta** | - |

---

## CHECKLIST IMPLEMENTAZIONE

### Fase 1: Setup e Migrazione (30 min)
- [ ] Clona repository attuale
- [ ] Crea nuovo repository su GitHub personale
- [ ] Configura remote e push
- [ ] Verifica git log e branch

### Fase 2: Modifica Endpoint (1-2 ore)
- [ ] Modifica `app/config/setting.py` (aggiungi variabili MCP)
- [ ] Modifica `app/main.py` (usa settings per endpoint)
- [ ] Aggiorna `.env.example`
- [ ] Configura Nginx reverse proxy
- [ ] Installa certificato SSL
- [ ] Test endpoint SSE

### Fase 3: Posizionamento Firma (2-3 ore)
- [ ] Crea funzione `get_signature_position()` in `app/main.py`
- [ ] Modifica signature `sign_document()` (aggiungi parametri)
- [ ] Modifica loop `signature_fields` (usa coordinate dinamiche)
- [ ] Aggiorna docstring
- [ ] Test posizioni predefinite
- [ ] Test coordinate personalizzate

### Fase 4: Conversione PDF/A (3-4 ore)
- [ ] Aggiorna `requirements.txt`
- [ ] Aggiorna `Dockerfile` (installa Ghostscript, etc.)
- [ ] Crea file `app/pdf_converter.py`
- [ ] Implementa classe `PDFAConverter`
- [ ] Implementa `detect_file_type()`
- [ ] Implementa `is_pdf_a_compliant()`
- [ ] Implementa `convert_image_to_pdfa()`
- [ ] Implementa `convert_pdf_to_pdfa()`
- [ ] Implementa `convert_office_to_pdfa()` (opzionale)
- [ ] Implementa `convert_to_pdfa()` (dispatcher)
- [ ] Integra in `sign_document()` (`app/main.py`)
- [ ] Rebuild Docker image
- [ ] Test conversione immagini
- [ ] Test conversione PDF
- [ ] Test verifica PDF/A esistenti

### Fase 5: Testing e Deploy (1-2 ore)
- [ ] Test flusso completo di firma
- [ ] Test con diversi formati file
- [ ] Test tutte le posizioni firma
- [ ] Verifica logs per errori
- [ ] Test performance (file grandi)
- [ ] Verifica upload DigitalOcean Spaces
- [ ] Test URL firmati
- [ ] Deploy su server produzione
- [ ] Configura dominio e SSL
- [ ] Monitoring e alerting

---

## RISCHI E MITIGAZIONI

### Rischio 1: Ghostscript non funziona in Docker
**Probabilità**: Media  
**Impatto**: Alto  
**Mitigazione**: Testare conversione PDF/A immediatamente dopo build Docker. Verificare versione Ghostscript compatibile con ocrmypdf.

### Rischio 2: File Office non convertibili (LibreOffice mancante)
**Probabilità**: Alta (se non installato)  
**Impatto**: Medio  
**Mitigazione**: Rendere supporto Office opzionale. Documentare chiaramente. Fornire messaggio errore chiaro all'utente.

### Rischio 3: Conversione PDF/A troppo lenta
**Probabilità**: Media  
**Impatto**: Medio  
**Mitigazione**: Implementare timeout adeguati. Considerare processing asincrono con Celery per file grandi.

### Rischio 4: Coordinate firma fuori pagina
**Probabilità**: Bassa (con posizioni predefinite)  
**Impatto**: Medio  
**Mitigazione**: Validare coordinate custom prima di passare ad API. Aggiungere bounds checking.

### Rischio 5: PDF/A non accettato da Infocert
**Probabilità**: Bassa  
**Impatto**: Alto  
**Mitigazione**: Testare con diversi PDF/A prima del deploy. Verificare conformità con pikepdf. Usare PDF/A-2b (standard più compatibile).

---

## NEXT STEPS

1. **Leggi il documento completo**: `MIGRATION_AND_CUSTOMIZATION_GUIDE.md`
2. **Segui i task nell'ordine**: Migrazione → Endpoint → Posizionamento → PDF/A
3. **Testa ad ogni step**: Non procedere finché il task corrente non funziona
4. **Documenta problemi**: Annota errori e soluzioni trovate
5. **Backup regolari**: Commit git frequenti con messaggi descrittivi

---

## RISORSE

- **Guida Completa**: `/workspace/digital-signature-mcp/MIGRATION_AND_CUSTOMIZATION_GUIDE.md`
- **Repository Originale**: https://github.com/AI-Blackbird/digital-signature-mcp
- **FastMCP Docs**: https://github.com/jlowin/fastmcp
- **ocrmypdf Docs**: https://ocrmypdf.readthedocs.io/
- **pikepdf Docs**: https://pikepdf.readthedocs.io/
- **PDF/A Standard**: https://www.pdfa.org/

---

*Analisi completata il 2025-11-29*
