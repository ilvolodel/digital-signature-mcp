# 🎯 Guida Implementazione - Posizionamento Firma Intelligente

## 📋 Panoramica

Sistema per firmare digitalmente PDF con posizionamento intelligente della firma.

**Repository:** https://github.com/ilvolodel/digital-signature-mcp

---

## 🔄 Flusso Utente → Agente → MCP

### **Scenario 1: PDF senza campi predefiniti** (caso più comune)

```
👤 Utente: "Voglio firmare questo documento: [PDF URL]"

🤖 Agente: [Chiama analyze_pdf_signature_fields(pdf_url)]

🔧 MCP: Analizza PDF → Nessun campo AcroForm trovato
        Cerca testo: Trova "Firma del Cliente" a pagina 5

🤖 Agente: "Ho analizzato il documento:
           - 5 pagine totali
           - Trovato testo 'Firma del Cliente' a pagina 5
           
           Dove vuoi posizionare la firma?
           1. Vicino a 'Firma del Cliente' (pagina 5, in basso)
           2. Ultima pagina, angolo basso-destra (standard)
           3. Dimmi tu (es: 'pagina 3, in alto a sinistra')"

👤 Utente: "Opzione 1"

🤖 Agente: [Chiama sign_document(
               link_pdf=...,
               page_signature="quinta_pagina",
               signature_position="bottom-right"
           )]

🔧 MCP: Firma il documento → Carica su cloud
        Restituisce URL firmato

🤖 Agente: "✅ Documento firmato!
           📄 Scarica qui: [URL]
           ⏰ Link valido 60 minuti"
```

---

## 🛠️ Tool MCP Disponibili

### **Tool 1: `analyze_pdf_signature_fields`** (DA IMPLEMENTARE)

**Scopo:** Analizzare il PDF per trovare dove posizionare la firma

**Input:**
```python
{
  "link_pdf": "https://example.com/document.pdf"
}
```

**Output:**
```python
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
      "confidence": "medium"
    }
  ],
  "recommendation": "Ho trovato 'Firma del Cliente' a pagina 5. Suggerisco bottom-right su pagina 5.",
  "suggested_config": {
    "page_signature": "quinta_pagina",  // o numero specifico
    "signature_position": "bottom-right"
  }
}
```

**Algoritmo:**
1. Scarica PDF da URL
2. Cerca campi AcroForm con PyPDF2 (signature fields standard)
3. Se non trovati → Cerca testo con pdfplumber
   - Keywords: "firma", "signature", "sottoscritto", "firmatario"
   - Pattern: "______", ".....", "-----"
4. Genera raccomandazione
5. Restituisce risultato

**Comportamento:**
- ✅ **Trova campi AcroForm** → Proponi di usarli
- ✅ **Trova keyword testuali** → Suggerisci quella pagina
- ❌ **Non trova niente** → Suggerisci default (ultima pagina, bottom-right)

---

### **Tool 2: `sign_document`** (GIÀ IMPLEMENTATO ✅ - DA ESTENDERE)

**Stato attuale:** Già funzionante con 7 posizioni predefinite

**Parametri attuali:**
```python
{
  "certificate_id": "...",
  "access_token": "...",
  "infocert_sat": "...",
  "transaction_id": "...",
  "pin": "...",
  "link_pdf": "https://...",
  "page_signature": "tutte_le_pagine",  # o "prima_pagina", "ultima_pagina"
  "signature_position": "bottom-right",   # ← GIÀ IMPLEMENTATO!
  "custom_coords": null                   # ← GIÀ IMPLEMENTATO!
}
```

**Posizioni disponibili:**
- `bottom-right` (default)
- `bottom-left`
- `bottom-center`
- `top-right`
- `top-left`
- `top-center`
- `center`
- `custom` (con custom_coords)

**Da aggiungere:**
```python
{
  ...
  "use_existing_field": "Firma_Cliente"  # ← DA IMPLEMENTARE
}
```

Se `use_existing_field` è specificato:
- Ignora `signature_position` e `custom_coords`
- Cerca il campo AcroForm con quel nome
- Usa le sue coordinate native

---

## 🎯 Strategia Implementazione

### **FASE 1: Analisi Semplice** (Raccomandato per iniziare)

**Non implementare OCR pesante!** Troppo complesso.

**Implementa solo:**
1. ✅ Cerca campi AcroForm (PyPDF2) - Veloce, 2 secondi
2. ✅ Cerca keyword semplici (pdfplumber) - Medio, 5 secondi
3. ❌ NO OCR completo (pytesseract) - Lento, 30+ secondi

**Librerie necessarie:**
```bash
pip install PyPDF2 pdfplumber requests
```

**Codice esempio:** Vedi `example_analyze_pdf.py`

---

### **FASE 2: Logica Agente** (Lato AI, non MCP)

L'agente AI deve:

1. **Chiamare `analyze_pdf_signature_fields`**
2. **Interpretare risultato:**
   ```python
   if result["has_acroform_fields"]:
       # Proponi i campi trovati
       "Ho trovato questi campi firma: [lista]. Quale vuoi usare?"
   
   elif result["text_hints"]:
       # Suggerisci in base al testo trovato
       "Ho trovato 'Firma' a pagina X. Vuoi firmare lì?"
   
   else:
       # Chiedi all'utente
       "Dove vuoi posizionare la firma? (es: ultima pagina, in basso)"
   ```

3. **Tradurre risposta utente in parametri:**
   ```python
   Utente: "In basso a sinistra dell'ultima pagina"
   
   → Parametri:
   {
     "page_signature": "ultima_pagina",
     "signature_position": "bottom-left"
   }
   ```

4. **Chiamare `sign_document` con i parametri corretti**

---

## 📝 Esempi di Conversazione

### **Esempio 1: Trova keyword "Firma"**

```
Utente: "Firma questo: https://example.com/contratto.pdf"

Agente chiama: analyze_pdf_signature_fields(...)
Risposta: {
  "text_hints": [{"keyword": "firma", "page": 3}],
  "recommendation": "Pagina 3, bottom-right"
}

Agente: "Ho trovato 'Firma' a pagina 3. Vuoi firmare lì in basso a destra?"
Utente: "Sì"

Agente chiama: sign_document(
  page_signature="terza_pagina",
  signature_position="bottom-right"
)
```

### **Esempio 2: Non trova niente**

```
Utente: "Firma questo PDF"

Agente chiama: analyze_pdf_signature_fields(...)
Risposta: {
  "text_hints": [],
  "recommendation": "Default ultima pagina"
}

Agente: "Dove vuoi firmare? (Es: 'ultima pagina in basso a destra')"
Utente: "Prima pagina, in alto a destra"

Agente chiama: sign_document(
  page_signature="prima_pagina",
  signature_position="top-right"
)
```

### **Esempio 3: Trova campo AcroForm**

```
Agente chiama: analyze_pdf_signature_fields(...)
Risposta: {
  "has_acroform_fields": true,
  "acroform_fields": [{"name": "Signature1", "page": 2}]
}

Agente: "Il documento ha un campo firma predefinito a pagina 2. Vuoi usarlo?"
Utente: "Sì"

Agente chiama: sign_document(
  use_existing_field="Signature1"  # ← DA IMPLEMENTARE
)
```

---

## 🚀 Priorità Implementazione

### **Priority 1 - MUST HAVE** ⭐⭐⭐
1. ✅ **Tool `sign_document` con 7 posizioni** (GIÀ FATTO!)
2. 🔨 **Tool `analyze_pdf_signature_fields` base**
   - Cerca campi AcroForm
   - Cerca keyword semplici ("firma", "signature")
   - Restituisce raccomandazione

### **Priority 2 - SHOULD HAVE** ⭐⭐
3. 🔨 **Estendi `sign_document` con `use_existing_field`**
   - Supporta campi AcroForm nativi

### **Priority 3 - NICE TO HAVE** ⭐
4. ⏳ **OCR avanzato** (futuro, solo se necessario)
   - pytesseract per PDF scannerizzati
   - Analisi visiva linee tratteggiate

---

## 🧪 Testing

**Test 1: PDF con campi AcroForm**
```bash
# Usa un PDF form standard
python example_analyze_pdf.py
```

**Test 2: PDF senza campi (solo testo)**
```bash
# Crea PDF con testo "Firma: _______"
# Verifica che trova la keyword
```

**Test 3: Posizionamento firma**
```bash
python test_signature_positions.py
# Verifica tutte le 7 posizioni
```

---

## 📦 Dipendenze

```bash
# Già installate (presumibilmente)
pip install fastmcp requests boto3

# Da installare per analisi PDF
pip install PyPDF2 pdfplumber

# OPZIONALE - Solo per OCR futuro
# pip install pytesseract pdf2image
# sudo apt-get install tesseract-ocr  # Linux
# brew install tesseract  # Mac
```

---

## 🎨 Architettura Finale

```
┌─────────────┐
│   Utente    │
│  (Persona)  │
└─────┬───────┘
      │ "Voglio firmare questo PDF"
      │
┌─────▼────────────────────────────────────────┐
│          Agente AI (Claude/GPT)              │
│  - Riceve richiesta utente                   │
│  - Chiama MCP tools                          │
│  - Interpreta risultati                      │
│  - Dialoga con utente                        │
└─────┬────────────────────────────────────────┘
      │ Chiama tool MCP
      │
┌─────▼────────────────────────────────────────┐
│            MCP Server (questo repo)          │
│                                              │
│  Tool 1: analyze_pdf_signature_fields        │
│    ├─ Scarica PDF                           │
│    ├─ Cerca campi AcroForm                  │
│    ├─ Cerca keyword testuali                │
│    └─ Restituisce raccomandazione           │
│                                              │
│  Tool 2: sign_document                      │
│    ├─ Riceve parametri posizione            │
│    ├─ Calcola coordinate (7 posizioni)      │
│    ├─ Chiama Infocert API                   │
│    └─ Carica PDF firmato su cloud           │
└─────┬────────────────────────────────────────┘
      │
┌─────▼───────────┐      ┌──────────────────┐
│  Infocert API   │      │  DigitalOcean    │
│  (Firma PAdES)  │      │  Spaces (Storage)│
└─────────────────┘      └──────────────────┘
```

---

## ❓ Decisioni da Prendere

1. **OCR completo o solo keyword semplici?**
   - **Raccomandazione:** Solo keyword semplici (più affidabile)
   
2. **Analisi automatica o chiedi sempre all'utente?**
   - **Raccomandazione:** Ibrido (analizza → suggerisci → conferma utente)

3. **Supportare campi AcroForm?**
   - **Raccomandazione:** Sì, ma solo se trovati (non crearli)

4. **Default se non trova niente?**
   - **Raccomandazione:** Ultima pagina, bottom-right

---

## 🎯 Prossimi Step

1. ✅ **Testare `example_analyze_pdf.py`** con PDF reali
2. 🔨 **Implementare `analyze_pdf_signature_fields` in `app/main.py`**
3. 🔨 **Estendere `sign_document` con `use_existing_field`**
4. 🧪 **Testare flusso completo**
5. 📝 **Documentare esempi d'uso**

---

## 📞 Domande?

- Repository: https://github.com/ilvolodel/digital-signature-mcp
- Test positioning: `python test_signature_positions.py`
- Test analysis: `python example_analyze_pdf.py`

**Commit corrente:** `d9d1eee - Add customizable signature position feature`
