# 📝 Firma Digitale MCP Server

Server MCP per la firma digitale di documenti PDF utilizzando i servizi Infocert e il caricamento automatico su DigitalOcean Spaces.

**Caratteristiche principali:**
- ✅ Firma digitale PAdES BASELINE-B (conforme eIDAS)
- ✅ Posizionamento firma intelligente (7 posizioni + custom)
- ✅ Analisi PDF per trovare suggerimenti di posizionamento
- ✅ Autenticazione a due fattori via SMS
- ✅ Caricamento automatico su DigitalOcean Spaces con URL firmati (60 min)

---

## 🚀 Quick Start

### 1. Installazione

```bash
# Clone repository
git clone https://github.com/your-username/digital-signature-mcp.git
cd digital-signature-mcp

# Installa dipendenze
pip install -r requirements.txt
```

### 2. Configurazione

Crea un file `.env` nella root del progetto:

```env
# Configurazione Infocert
CLIENT_ID=your_client_id_here
CLIENT_SECRET=your_client_secret_here
SIGNATURE_API=https://api.infocert.it/signature
AUTHORIZATION_API=https://api.infocert.it/authorization
TENANT=your_tenant_here

# Configurazione DigitalOcean Spaces
DO_SPACES_ACCESS_KEY=your_digitalocean_access_key_here
DO_SPACES_SECRET_KEY=your_digitalocean_secret_key_here
DO_SPACES_REGION=nyc3
DO_SPACES_BUCKET=your_bucket_name_here
DO_SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com
```

### 3. Avvio

```bash
# Metodo 1: Docker
docker-compose up -d

# Metodo 2: Locale
fastmcp run app/main.py
```

---

## 🛠️ Tool MCP Disponibili

### **Tool 1: `analyze_pdf_signature_fields`** 🔍

Analizza un PDF per trovare suggerimenti su dove posizionare la firma.

**Input:**
```json
{
  "link_pdf": "https://example.com/document.pdf"
}
```

**Output:**
```json
{
  "total_pages": 5,
  "has_acroform_fields": false,
  "acroform_fields": [],
  "text_hints": [
    {
      "keyword": "firma",
      "page": 5,
      "text": "Firma del Cliente:",
      "position": "bottom",
      "description": "Trovato 'Firma del Cliente:' a pagina 5 (bottom)"
    }
  ],
  "recommendation": "💡 Trovato 'firma' a pagina 5 (bottom). Suggerisco di firmare su quella pagina in posizione 'bottom-right' o 'bottom-left'.",
  "suggested_positions": ["bottom-right", "bottom-left", "bottom-center", "top-right", "top-left", "top-center", "center"]
}
```

**Cosa cerca:**
1. ✅ Campi AcroForm signature (campi firma interattivi standard)
2. ✅ Parole chiave: "Firma", "Signature", "Sottoscritto", "Firmatario"
3. ✅ Pattern di linee: "______", ".....", "-----"

---

### **Tool 2: `sign_document`** ✍️

Firma digitalmente un documento PDF.

**Parametri principali:**

| Parametro | Tipo | Descrizione | Default |
|-----------|------|-------------|---------|
| `link_pdf` | string | URL del PDF da firmare | - |
| `page_signature` | string | `"prima_pagina"`, `"ultima_pagina"`, `"tutte_le_pagine"` | `"tutte_le_pagine"` |
| `signature_position` | string | Vedi sotto | `"bottom-right"` |
| `custom_coords` | object | `{"llx": 100, "lly": 50, "urx": 180, "ury": 80}` | `null` |
| `use_existing_field` | string | Nome campo AcroForm (es: `"Signature1"`) | `null` |

**Posizioni disponibili (`signature_position`):**

```
┌─────────────────────────────────────┐
│  top-left    top-center   top-right │
│                                     │
│                                     │
│              center                 │
│                                     │
│                                     │
│ bottom-left bottom-center bottom-   │
│                          right ⭐   │
└─────────────────────────────────────┘
```

**Esempio 1: Posizione predefinita**
```json
{
  "certificate_id": "...",
  "access_token": "...",
  "link_pdf": "https://...",
  "page_signature": "ultima_pagina",
  "signature_position": "bottom-right"
}
```

**Esempio 2: Coordinate custom**
```json
{
  "certificate_id": "...",
  "access_token": "...",
  "link_pdf": "https://...",
  "signature_position": "custom",
  "custom_coords": {
    "llx": 100,
    "lly": 50,
    "urx": 180,
    "ury": 80
  }
}
```

**Esempio 3: Campo AcroForm esistente**
```json
{
  "certificate_id": "...",
  "access_token": "...",
  "link_pdf": "https://...",
  "use_existing_field": "Firma_Cliente"
}
```

---

### Altri Tool

4. **`auth_token`**: Autenticazione con i servizi Infocert
5. **`get_certificates`**: Recupera i certificati digitali disponibili
6. **`request_smsp_challenge`**: Richiede un codice OTP via SMS
7. **`authorize_smsp`**: Autorizza la firma con OTP e PIN

---

## 🔄 Flusso Completo

### **Scenario A: Con analisi automatica del PDF**

```
1. Utente → Agente: "Voglio firmare questo documento: [URL]"

2. Agente → MCP: analyze_pdf_signature_fields(link_pdf=...)
   MCP → Agente: {
     "recommendation": "Trovato 'Firma' a pagina 5",
     "text_hints": [...]
   }

3. Agente → Utente: "Ho trovato 'Firma' a pagina 5. Dove vuoi firmare?
                      1. Pagina 5, in basso a destra (consigliato)
                      2. Ultima pagina, standard
                      3. Dimmi tu"

4. Utente → Agente: "Opzione 1"

5. Agente → MCP: sign_document(
     link_pdf=...,
     page_signature="quinta_pagina",
     signature_position="bottom-right"
   )

6. MCP → Agente: {
     "signed_pdf_url": "https://...",
     "expires_in": "60 minutes"
   }

7. Agente → Utente: "✅ Documento firmato!
                     📄 Scarica qui: [URL]
                     ⏰ Link valido 60 minuti"
```

### **Scenario B: Senza analisi (scelta diretta utente)**

```
1. Utente → Agente: "Firma questo PDF in basso a sinistra: [URL]"

2. Agente → MCP: sign_document(
     link_pdf=...,
     signature_position="bottom-left"
   )

3. MCP → Agente: {"signed_pdf_url": "..."}

4. Agente → Utente: "✅ Documento firmato! [URL]"
```

---

## 📐 Dimensioni Firma

Il talloncino di firma predefinito:
- **Larghezza:** 80 punti (~28mm)
- **Altezza:** 30 punti (~11mm)
- **Margine:** 15 punti (~5mm) dai bordi
- **Formato pagina:** A4 (595x842 punti)

Per coordinate custom, usa punti PDF (1 punto = 1/72 pollici = 0.35mm):
```python
{
  "llx": 100,  # Lower-Left X
  "lly": 50,   # Lower-Left Y
  "urx": 180,  # Upper-Right X (llx + 80)
  "ury": 80    # Upper-Right Y (lly + 30)
}
```

---

## 🧪 Testing

### Test posizionamento firma

```bash
# Visualizza ASCII art delle 7 posizioni
python test_signature_positions.py
```

Output:
```
┌─────────────────────────────────────┐
│ ▓▓▓▓▓▓▓▓▓▓▓            ▓▓▓▓▓▓▓▓▓▓▓ │  TOP
│                                     │
│                                     │
│              ▓▓▓▓▓▓▓▓▓▓▓           │  MIDDLE
│                                     │
│                                     │
│ ▓▓▓▓▓▓▓▓▓▓▓            ▓▓▓▓▓▓▓▓▓▓▓ │  BOTTOM
└─────────────────────────────────────┘
```

### Test analisi PDF

```bash
# Analizza un PDF di esempio
python example_analyze_pdf.py
```

---

## 🔐 Credenziali

### Infocert
Contatta [Infocert](https://www.infocert.it) per ottenere:
- `CLIENT_ID` e `CLIENT_SECRET` (OAuth2)
- `TENANT` (identificativo tenant)
- Certificati digitali per la firma

### DigitalOcean Spaces
1. Accedi a [DigitalOcean](https://cloud.digitalocean.com)
2. Vai su **API** → **Spaces Keys**
3. Crea una nuova **Access Key**
4. Crea un **Space** (bucket) nella regione desiderata
5. Usa le credenziali nel file `.env`

---

## 🐳 Docker

```bash
# Build
docker build -t signature-mcp .

# Run
docker-compose up -d

# Logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## 📂 Struttura Progetto

```
digital-signature-mcp/
├── app/
│   ├── main.py                 # Server MCP (tool definitions)
│   └── config/
│       └── setting.py          # Configurazione environment
├── requirements.txt            # Dipendenze Python
├── Dockerfile                  # Container Docker
├── docker-compose.yml          # Orchestrazione
├── test_signature_positions.py # Test posizioni firma
├── example_analyze_pdf.py      # Esempio analisi PDF
└── README.md                   # Questa documentazione
```

---

## 🔧 Personalizzazione

### Cambiare endpoint API

Modifica `.env`:
```env
SIGNATURE_API=https://your-custom-domain.com/signature
AUTHORIZATION_API=https://your-custom-domain.com/authorization
```

### Usare altro storage (non DigitalOcean)

Modifica `app/main.py` → funzione `upload_to_digitalocean_spaces()`:
- Sostituisci `boto3` con il tuo provider (AWS S3, Azure Blob, Google Cloud Storage)
- Mantieni la stessa interfaccia: `upload_to_storage(bytes, filename) -> dict`

### Aggiungere nuove posizioni firma

Modifica `app/main.py` → funzione `get_signature_position()`:
```python
elif position == "middle-left":
    return {
        "llx": margin,
        "lly": (page_height - sig_height) // 2,
        "urx": margin + sig_width,
        "ury": (page_height + sig_height) // 2
    }
```

---

## 🚨 Troubleshooting

### Errore: "PyPDF2 not found"

```bash
pip install PyPDF2==3.0.1
```

### Errore: "pdfplumber not found"

```bash
pip install pdfplumber==0.11.0
```

### Analisi PDF non trova niente

L'analisi cerca:
1. Campi AcroForm (solo se il PDF li ha)
2. Parole chiave testuali (solo se il testo è selezionabile)

Se il PDF è una **scansione** (immagine), l'analisi non funzionerà. In quel caso:
- Chiedi all'utente dove vuole firmare
- Usa una delle 7 posizioni predefinite

### PDF firmato non si apre

Verifica:
- Il PDF originale sia valido
- Le credenziali Infocert siano corrette
- Il certificato sia attivo e non scaduto

---

## 📚 Documentazione Aggiuntiva

- **Infocert API:** [Documentazione ufficiale](https://www.infocert.it)
- **pyHanko:** [GitHub repo](https://github.com/MatthiasValvekens/pyHanko)
- **FastMCP:** [GitHub repo](https://github.com/jlowin/fastmcp)
- **DigitalOcean Spaces:** [Documentazione](https://docs.digitalocean.com/products/spaces/)

---

## 🤝 Contribuire

Per contribuire a questo progetto:

1. Fai fork del repository
2. Crea un branch: `git checkout -b feature/my-feature`
3. Committa le modifiche: `git commit -am 'Add my feature'`
4. Push: `git push origin feature/my-feature`
5. Apri una Pull Request

---

## 📄 Licenza

Questo progetto è distribuito sotto licenza MIT.

---

## 🎯 Roadmap

- [ ] Supporto conversione automatica PDF/A
- [ ] OCR avanzato per PDF scannerizzati
- [ ] Interfaccia web per testing
- [ ] Supporto firme multiple su stesso documento
- [ ] Integrazione con altri provider di firma digitale

---

**Ultimo aggiornamento:** 2025-01-29
**Repository:** [GitHub](https://github.com/your-username/digital-signature-mcp)
