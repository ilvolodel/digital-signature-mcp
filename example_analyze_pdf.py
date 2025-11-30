#!/usr/bin/env python3
"""
Esempio di analisi PDF per trovare dove posizionare la firma.

Approccio IBRIDO:
1. Cerca campi AcroForm (campi interattivi)
2. Cerca testo con keyword: "Firma", "Signature", "Sottoscritto"
3. Se non trova niente → chiedi all'utente
"""

import requests
from io import BytesIO

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    print("⚠️  pdfplumber non installato. Installa con: pip install pdfplumber")

try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    print("⚠️  PyPDF2 non installato. Installa con: pip install PyPDF2")


def analyze_pdf_signature_hints(pdf_url: str) -> dict:
    """
    Analizza un PDF cercando indizi su dove posizionare la firma.
    
    Metodi (in ordine):
    1. Campi AcroForm (signature fields standard)
    2. Parole chiave nel testo: "Firma", "Signature", "Sottoscritto"
    3. Linee tratteggiate "______"
    
    Args:
        pdf_url: URL del PDF da analizzare
        
    Returns:
        dict con risultati analisi
    """
    result = {
        "has_acroform_fields": False,
        "acroform_fields": [],
        "text_hints": [],
        "recommendation": None,
        "total_pages": 0
    }
    
    try:
        # Scarica PDF
        response = requests.get(pdf_url, timeout=30)
        response.raise_for_status()
        pdf_bytes = BytesIO(response.content)
        
        # FASE 1: Cerca campi AcroForm con PyPDF2
        if PYPDF2_AVAILABLE:
            print("\n🔍 FASE 1: Cerco campi AcroForm...")
            pdf_reader = PdfReader(pdf_bytes)
            result["total_pages"] = len(pdf_reader.pages)
            
            if "/AcroForm" in pdf_reader.trailer["/Root"]:
                acro_form = pdf_reader.trailer["/Root"]["/AcroForm"]
                if "/Fields" in acro_form:
                    fields = acro_form["/Fields"]
                    for field in fields:
                        field_obj = field.get_object()
                        field_type = field_obj.get("/FT", "")
                        field_name = field_obj.get("/T", "")
                        
                        # Cerca solo signature fields
                        if field_type == "/Sig" or "signature" in str(field_name).lower():
                            result["has_acroform_fields"] = True
                            result["acroform_fields"].append({
                                "name": str(field_name),
                                "type": str(field_type),
                                "page": "unknown"  # PyPDF2 non dà facilmente la pagina
                            })
                            print(f"   ✅ Trovato campo: {field_name} (tipo: {field_type})")
        
        # FASE 2: Cerca parole chiave nel testo con pdfplumber
        if PDFPLUMBER_AVAILABLE:
            print("\n🔍 FASE 2: Cerco parole chiave nel testo...")
            pdf_bytes.seek(0)  # Reset stream
            
            keywords = ["firma", "signature", "sottoscritto", "firmatario", "sign here"]
            line_patterns = ["_____", ".....", "-----"]  # Linee per firma
            
            with pdfplumber.open(pdf_bytes) as pdf:
                result["total_pages"] = len(pdf.pages)
                
                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    text_lower = text.lower()
                    
                    # Cerca keywords
                    for keyword in keywords:
                        if keyword in text_lower:
                            # Trova posizione approssimativa
                            words = page.extract_words()
                            for word in words:
                                if keyword in word["text"].lower():
                                    result["text_hints"].append({
                                        "keyword": keyword,
                                        "page": page_num,
                                        "text": word["text"],
                                        "x": word["x0"],
                                        "y": word["top"],
                                        "confidence": "medium"
                                    })
                                    print(f"   ✅ Trovato '{keyword}' a pagina {page_num}")
                    
                    # Cerca linee tratteggiate
                    for pattern in line_patterns:
                        if pattern in text:
                            result["text_hints"].append({
                                "keyword": "line_pattern",
                                "page": page_num,
                                "text": pattern,
                                "confidence": "low"
                            })
                            print(f"   ✅ Trovato pattern '{pattern}' a pagina {page_num}")
        
        # FASE 3: Genera raccomandazione
        if result["has_acroform_fields"]:
            result["recommendation"] = f"Usa il campo AcroForm '{result['acroform_fields'][0]['name']}'"
        elif result["text_hints"]:
            first_hint = result["text_hints"][0]
            result["recommendation"] = f"Ho trovato '{first_hint['keyword']}' a pagina {first_hint['page']}. Suggerisco di firmare lì."
        else:
            result["recommendation"] = "Nessun indizio trovato. Chiedi all'utente dove vuole firmare."
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "recommendation": "Errore nell'analisi. Chiedi all'utente dove firmare."
        }


def print_analysis_result(result: dict):
    """Stampa i risultati in formato leggibile"""
    print("\n" + "=" * 60)
    print("📊 RISULTATI ANALISI PDF")
    print("=" * 60)
    
    if "error" in result:
        print(f"\n❌ Errore: {result['error']}")
        return
    
    print(f"\n📄 Pagine totali: {result['total_pages']}")
    
    print(f"\n🔖 Campi AcroForm: {'✅ Trovati' if result['has_acroform_fields'] else '❌ Nessuno'}")
    for field in result["acroform_fields"]:
        print(f"   - {field['name']} (tipo: {field['type']})")
    
    print(f"\n📝 Indizi testuali: {len(result['text_hints'])} trovati")
    for hint in result["text_hints"][:5]:  # Max 5
        print(f"   - '{hint['keyword']}' a pagina {hint['page']}")
    
    print(f"\n💡 RACCOMANDAZIONE:")
    print(f"   {result['recommendation']}")
    
    print("\n" + "=" * 60)


# Test con un PDF di esempio
if __name__ == "__main__":
    print("🧪 TEST ANALISI PDF")
    print("=" * 60)
    
    if not PDFPLUMBER_AVAILABLE or not PYPDF2_AVAILABLE:
        print("\n⚠️  Installare dipendenze:")
        print("   pip install pdfplumber PyPDF2")
        exit(1)
    
    # Usa un PDF di test (metti qui un URL reale)
    test_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    
    print(f"\n📥 Analizzo: {test_url}\n")
    
    result = analyze_pdf_signature_hints(test_url)
    print_analysis_result(result)
    
    print("\n✅ Test completato!")
