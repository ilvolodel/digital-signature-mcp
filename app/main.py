from fastmcp import FastMCP  # type: ignore
from typing import Annotated, Dict
from pydantic import Field, BaseModel
from typing import List
import base64
import requests
from requests.exceptions import RequestException
import boto3
from botocore.exceptions import ClientError
from datetime import datetime
from urllib.parse import urlparse, urlunparse, unquote
from app.config.setting import settings
from pyhanko.pdf_utils.reader import PdfFileReader

# MCP server configuration with additional options
mcp = FastMCP(
    name="Signature MCP Server",
    sse_path='/digital-signature/sse',
    message_path='/digital-signature/messages/',
    initialization_timeout=120,
    max_retries=10,
    retry_delay=5
)

@mcp.tool(
    name="auth_token",
    description="Autentica l'utente con i servizi Infocert e ottiene un token di accesso valido per utilizzare le API di firma digitale. Questo tool è il primo passo obbligatorio per accedere a tutti gli altri servizi di firma.",
    tags=["auth", "services"]
)
def auth_token(
    username: Annotated[str, Field(description="Username per l'accesso ai servizi Infocert (email o nome utente)")],
    password: Annotated[str, Field(description="Password per l'accesso ai servizi Infocert")]
) -> dict:
    """
    Autentica l'utente con i servizi Infocert e restituisce un token di accesso.
    
    Questo tool effettua una richiesta OAuth2 con grant_type=password per ottenere
    un token di accesso che permetterà di utilizzare tutti gli altri servizi di firma digitale.
    Il token ha una durata limitata e può essere rinnovato usando il refresh_token.
    
    Args:
        username (str): Username per l'accesso ai servizi Infocert
        password (str): Password per l'accesso ai servizi Infocert
        
    Returns:
        dict: Dizionario contenente:
            - access_token: Token di accesso per le API
            - refresh_token: Token per rinnovare l'accesso
            - expires_in: Durata del token in secondi
            - scope: Permessi associati al token
            - type: "error" se si verifica un errore
            - content: Messaggio di errore dettagliato
    """
    try:
        url = settings.AUTHORIZATION_API + "/token"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "password",
            "client_id": settings.CLIENT_ID,
            "client_secret": settings.CLIENT_SECRET,
            "username": username,
            "password": password
        }
        
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        result = response.json()
        
        return {
            "access_token": result["accessToken"],
            "refresh_token": result["refreshToken"],
            "expires_in": result["expiresIn"],
            "scope": result["scope"]
        }
    except RequestException as e:
        return {
            "type": "error",
            "content": f"Error during Services token request: {str(e)}"
        }
    except ValueError as e:
        return {
            "type": "error",
            "content": f"Error parsing Services response: {str(e)}"
        }

def upload_to_digitalocean_spaces(file_content: bytes, filename: str) -> dict:
    """
    Carica un file su DigitalOcean Spaces e genera un URL firmato con durata di 60 minuti.
    
    Args:
        file_content (bytes): Contenuto del file da caricare
        filename (str): Nome del file
        
    Returns:
        dict: Risultato del caricamento con URL firmato del file o errore
    """
    try:
        # Configura il client S3 per DigitalOcean Spaces
        session = boto3.session.Session()
        client = session.client(
            's3',
            region_name=settings.DO_SPACES_REGION,
            endpoint_url=settings.DO_SPACES_ENDPOINT,
            aws_access_key_id=settings.DO_SPACES_ACCESS_KEY,
            aws_secret_access_key=settings.DO_SPACES_SECRET_KEY
        )
        
        # Genera un nome file univoco con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"signed_documents/{timestamp}_{filename}"
        
        # Carica il file
        client.put_object(
            Bucket=settings.DO_SPACES_BUCKET,
            Key=unique_filename,
            Body=file_content,
            ContentType='application/pdf',
            ACL='private'  # File privato per sicurezza
        )
        
        # Genera URL firmato con durata di 60 minuti (3600 secondi)
        signed_url = client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': settings.DO_SPACES_BUCKET,
                'Key': unique_filename
            },
            ExpiresIn=3600  # 60 minuti
        )
        
        # Genera anche l'URL pubblico (per riferimento)
        public_url = f"{settings.DO_SPACES_ENDPOINT}/{settings.DO_SPACES_BUCKET}/{unique_filename}"
        
        return {
            "success": True,
            "signed_url": signed_url,  
            "expires_in": 3600,
        }
        
    except ClientError as e:
        return {
            "success": False,
            "error": f"DigitalOcean Spaces error: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Upload error: {str(e)}"
        }

def transform_certificates(certificates_data: list) -> dict:
    """
    Trasforma i dati dei certificati ricevuti dall'API Infocert.
    
    Args:
        certificates_data (list): Array di certificati dall'API
        
    Returns:
        dict: Lista trasformata di certificati con ID estratti dal DNQ e campi del subject
    """
    try:
        # Se non è una lista, restituisci i dati originali
        if not isinstance(certificates_data, list):
            return certificates_data
            
        transformed_certificates = []
        
        for cert in certificates_data:
            # Estrai l'ID dal campo subject DNQ se presente
            certificate_id = None
            if "subject" in cert:
                subject_str = cert["subject"]
                import re
                
                # Cerca l'ID nel DNQ (formato: DNQ=2024501530362, ...)
                dnq_match = re.search(r'DNQ=([^,]+)', subject_str)
                if dnq_match:
                    certificate_id = dnq_match.group(1)
            
            # Se non trovato nel DNQ, prova a estrarre dal CN
            if not certificate_id and "subject" in cert:
                subject_str = cert["subject"]
                import re
                cn_match = re.search(r'CN=([^,]+)', subject_str)
                if cn_match:
                    certificate_id = cn_match.group(1)
            
            # Estrai i campi dal subject del certificato (stringa)
            subject_info = {}
            if "subject" in cert:
                subject_str = cert["subject"]
                import re
                
                # Estrai GIVENNAME
                givenname_match = re.search(r'GIVENNAME=([^,]+)', subject_str)
                if givenname_match:
                    subject_info["given_name"] = givenname_match.group(1)
                
                # Estrai SURNAME
                surname_match = re.search(r'SURNAME=([^,]+)', subject_str)
                if surname_match:
                    subject_info["surname"] = surname_match.group(1)
                
                # Estrai CN (Common Name)
                cn_match = re.search(r'CN=([^,]+)', subject_str)
                if cn_match:
                    subject_info["common_name"] = cn_match.group(1)
                
                # Estrai DNQ
                dnq_match = re.search(r'DNQ=([^,]+)', subject_str)
                if dnq_match:
                    subject_info["dnq"] = dnq_match.group(1)
                
                # Estrai SERIALNUMBER
                serial_match = re.search(r'SERIALNUMBER=([^,]+)', subject_str)
                if serial_match:
                    subject_info["serial_number"] = serial_match.group(1)
                
                # Estrai C (Country)
                country_match = re.search(r'C=([^,]+)', subject_str)
                if country_match:
                    subject_info["country"] = country_match.group(1)
            
            transformed_cert = {
                "certificateId": certificate_id or "Non disponibile",
                "subject": cert.get("subject", ""),
                "subject_info": subject_info,  # Campi estratti dal subject
                "issuer": cert.get("issuer", ""),
                "status": cert.get("status", "Non disponibile"),
                "expirationDate": cert.get("expirationDate", "Non disponibile"),
            }
            
            transformed_certificates.append(transformed_cert)
        
        return {
            "certificates": transformed_certificates,
            "total_count": len(transformed_certificates)
        }
        
    except Exception as e:
        logger.error(f"Errore nella trasformazione dei certificati: {str(e)}")
        return {
            "type": "error",
            "content": f"Errore nella trasformazione dei certificati: {str(e)}",
            "original_data": certificates_data
        }

@mcp.tool(
    name="get_certificates",
    description="Recupera la lista di tutti i certificati digitali disponibili per l'utente autenticato. Ogni certificato contiene informazioni dettagliate incluso l'ID univoco necessario per le operazioni di firma.",
    tags=["certificates", "services"]
)
def get_certificates(
    access_token: Annotated[str, Field(description="Token di accesso ottenuto dal tool auth_token")]
) -> dict:
    """
    Recupera la lista completa dei certificati digitali disponibili per l'utente.
    
    Questo tool restituisce tutti i certificati di firma digitale associati all'account
    dell'utente, inclusi i dettagli del certificato e l'ID univoco necessario per
    le operazioni di firma. I certificati vengono automaticamente processati per
    estrarre l'ID dal campo subject DNQ.
    
    Args:
        access_token (str): Token di accesso valido ottenuto da auth_token
        
    Returns:
        dict: Lista di certificati con i seguenti campi per ogni certificato:
            - certificateId: ID univoco del certificato (estratto da DNQ)
            - subject: Soggetto del certificato (stringa originale)
            - subject_info: Campi estratti dal subject del certificato:
                - given_name: Nome dell'utente (GIVENNAME)
                - surname: Cognome dell'utente (SURNAME)
                - common_name: Nome comune (CN)
                - dnq: Identificativo DNQ
                - serial_number: Numero seriale dal subject (SERIALNUMBER)
                - country: Paese (C)
            - issuer: Emittente del certificato
            - status: Stato del certificato (es. "active")
            - expirationDate: Data di scadenza del certificato
            - ids: Array di identificatori del certificato
            - type: "error" se si verifica un errore
            - content: Messaggio di errore dettagliato
    """
    try:
        url = f"{settings.SIGNATURE_API}/certificates"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "tenant": settings.TENANT
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        result = response.json()
        
        list_certificates = transform_certificates(result)
        return list_certificates["certificates"][0]

    except RequestException as e:
        return {
            "type": "error",
            "content": f"Error retrieving certificates: {str(e)}"
        }
    except ValueError as e:
        return {
            "type": "error",
            "content": f"Error parsing certificates response: {str(e)}"
        }


@mcp.tool(
    name="request_smsp_challenge",
    description="Invia una richiesta di autenticazione SMS per la firma digitale. Questo tool invia un OTP (One-Time Password) via SMS al numero di telefono associato al certificato per verificare l'identità dell'utente prima della firma.",
    tags=["auth", "services", "smsp"]
)
def request_smsp_challenge(
    access_token: Annotated[str, Field(description="Token di accesso ottenuto dal tool auth_token")]
) -> dict:
    """
    Invia una richiesta di autenticazione SMS per la firma digitale.
    
    Questo tool avvia il processo di autenticazione a due fattori inviando un
    codice OTP (One-Time Password) via SMS al numero di telefono registrato
    per il certificato digitale. L'utente riceverà un SMS con il codice che
    dovrà essere utilizzato nel tool authorize_smsp per completare l'autenticazione.
    
    Args:
        access_token (str): Token di accesso valido ottenuto da auth_token
        
    Returns:
        dict: Risposta della richiesta contenente:
            - transactionId: ID della transazione per l'autorizzazione
            - status: Stato della richiesta
            - message: Messaggio informativo
            - type: "error" se si verifica un errore
            - content: Messaggio di errore dettagliato
    """
    try:
        url = f"{settings.SIGNATURE_API}/authenticators/SMSP/challenge"
        headers = {
            "tenant": settings.TENANT,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, headers=headers, json={})
        response.raise_for_status()
        result = response.json()
        
        return result

    except RequestException as e:
        return {
            "type": "error",
            "content": f"Error requesting SMSP challenge: {str(e)}"
        }
    except ValueError as e:
        return {
            "type": "error",
            "content": f"Error parsing SMSP challenge response: {str(e)}"
        }

@mcp.tool(
    name="authorize_smsp",
    description="Autorizza una richiesta di firma digitale utilizzando il codice OTP ricevuto via SMS. Questo tool completa il processo di autenticazione a due fattori e restituisce un token SAT necessario per la firma.",
    tags=["auth", "services", "smsp"]
)
def authorize_smsp(
    access_token: Annotated[str, Field(description="Token di accesso ottenuto dal tool auth_token")],
    certificate_id: Annotated[str, Field(description="ID del certificato digitale ottenuto da get_certificates")],
    transactionId: Annotated[str, Field(description="ID della transazione ottenuto da request_smsp_challenge")],
    otp: Annotated[str, Field(description="Codice OTP ricevuto via SMS dal tool request_smsp_challenge")],
    pin: Annotated[str, Field(description="PIN del certificato digitale (password di protezione)")]
) -> dict:
    """
    Autorizza una richiesta di firma digitale completando l'autenticazione SMS.
    
    Questo tool completa il processo di autenticazione a due fattori verificando
    il codice OTP ricevuto via SMS e il PIN del certificato. Se l'autenticazione
    è corretta, restituisce un token SAT (Signature Authorization Token) che
    deve essere utilizzato nel tool sign_document per firmare il documento.
    
    Args:
        access_token (str): Token di accesso valido ottenuto da auth_token
        certificate_id (str): ID del certificato digitale da utilizzare
        transactionId (str): ID della transazione ottenuto da request_smsp_challenge
        otp (str): Codice OTP ricevuto via SMS
        pin (str): PIN di protezione del certificato digitale
        
    Returns:
        dict: Risposta di autorizzazione contenente:
            - Infocert-SAT: Token di autorizzazione per la firma
            - type: "error" se si verifica un errore
            - content: Messaggio di errore dettagliato
    """
    try:
        url = f"{settings.SIGNATURE_API}/authenticators/{certificate_id}/SMSP/authorize"
        headers = {
            "tenant": settings.TENANT,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "signaturesNumber": 1,
            "transactionId": transactionId,
            "otp": otp,
            "pin": pin
        }
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        
        return {"Infocert-SAT": result["sat"]}

    except RequestException as e:
        return {
            "type": "error",
            "content": f"Error during SMSP authorization: {str(e)}"
        }
    except ValueError as e:
        return {
            "type": "error",
            "content": f"Error parsing SMSP authorization response: {str(e)}"
        }

@mcp.tool(
    name="sign_document",
    description="Firma digitalmente un documento PDF utilizzando il servizio Infocert. Questo tool scarica il documento dal link fornito, lo firma con il certificato specificato, converte il risultato in PDF e lo carica automaticamente su DigitalOcean Spaces.",
    tags=["signature", "services", "storage"]
)
def sign_document(
    certificate_id: Annotated[str, Field(description="ID del certificato digitale ottenuto da get_certificates")],
    access_token: Annotated[str, Field(description="Token di accesso ottenuto dal tool auth_token")],
    infocert_sat: Annotated[str, Field(description="Token SAT ottenuto dal tool authorize_smsp")],
    transaction_id: Annotated[str, Field(description="ID della transazione ottenuto da request_smsp_challenge")],
    pin: Annotated[str, Field(description="PIN del certificato digitale (password di protezione)")],
    link_pdf: Annotated[str, Field(description="URL del documento PDF da firmare (deve essere accessibile pubblicamente)")]
) -> dict:
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
        
    Returns:
        dict: Risposta della firma contenente:
            - applicationId: ID dell'applicazione
            - signatureResult: Array con i risultati della firma
                - requestId: ID della richiesta
                - isOk: Stato della firma
                - signedDocument: Documento firmato con content (base64), contentType e attachName
            - signed_document_url: URL firmato del PDF con durata di 60 minuti (condivisibile) (aggiunto automaticamente)
            - public_document_url: URL pubblico del PDF (richiede autenticazione) (aggiunto automaticamente)
            - uploaded_filename: Nome del file caricato (aggiunto automaticamente)
            - url_expires_in_minutes: Durata dell'URL firmato in minuti (60) (aggiunto automaticamente)
            - upload_info: Informazioni dettagliate del caricamento (aggiunto automaticamente)
            - upload_error: Eventuale errore durante il caricamento (aggiunto automaticamente)
            - type: "error" se si verifica un errore
            - content: Messaggio di errore dettagliato
    """
    try:

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
            
        # Converti il contenuto in base64
        content_base64 = base64.b64encode(pdf_response.content).decode('utf-8')
        url = f"{settings.SIGNATURE_API}/certificates/{certificate_id}/sign"
        headers = {
            "tenant": settings.TENANT,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Infocert-SAT": infocert_sat,
            "Transaction-Id": transaction_id
        }

        body = {
            "applicationId": "trusty",
            "pin": pin,
            "padesSignatures": [
                {
                    "signatureLevel": "BASELINE-B",
                    "requestId": transaction_id,
                    "document": {
                        "content": content_base64,
                        "contentType": "application/pdf",
                        "attachName": attach_name
                    },
                    "packaging": "ENVELOPED",
                    "isVisible": False
                }
            ]
        }

        response = requests.post(url, headers=headers, json=body)

        response.raise_for_status()
        result = response.json()
        upload_info={}

        # Estrai il documento firmato in base64 dalla risposta
        if "signatureResult" in result and len(result["signatureResult"]) > 0:
            signature_result = result["signatureResult"][0]
            if "signedDocument" in signature_result and "content" in signature_result["signedDocument"]:
                signed_document_base64 = signature_result["signedDocument"]["content"]
                signed_document_name = signature_result["signedDocument"].get("attachName", attach_name)
                
                # Converti da base64 a bytes
                signed_document_bytes = base64.b64decode(signed_document_base64)
                
                # Carica il PDF firmato su DigitalOcean Spaces
                upload_result = upload_to_digitalocean_spaces(signed_document_bytes, attach_name)
                
                # Aggiungi le informazioni di caricamento al risultato
                upload_info = upload_result
                
        
        return upload_info

    except RequestException as e:
        return {
            "type": "error",
            "content": f"Error during document signing: {str(e)}"
        }
    except ValueError as e:
        return {
            "type": "error",
            "content": f"Error parsing signature response: {str(e)}"
        }

#@mcp.tool(
#    name="verify_signature",
#    description="Verifica e valida tutte le firme digitali presenti in un documento PDF. Restituisce informazioni dettagliate su ogni firma inclusi validità, certificato, data di firma e stato di verifica.",
#    tags=["signature", "verification", "validation"]
#)
def verify_signature(
    link_pdf: Annotated[str, Field(description="URL del documento PDF firmato (deve essere accessibile pubblicamente)")]
) -> dict:
    """
    Verifica tutte le firme digitali presenti in un documento PDF.
    """
    try:
        # Scarica il PDF dal link fornito
        pdf_response = requests.get(link_pdf)
        pdf_response.raise_for_status()
        
        # Crea un file temporaneo in memoria
        from io import BytesIO
        pdf_stream = BytesIO(pdf_response.content)

        # Leggi il PDF
        pdf_reader = PdfFileReader(pdf_stream)
        
        # Verifica se il PDF ha firme
        if not pdf_reader.embedded_signatures:
            return {
                "total_signatures": 0,
                "signatures": [],
                "document_integrity": True,
                "verification_summary": "Nessuna firma digitale trovata nel documento",
                "message": "Il documento non contiene firme digitali"
            }
        
        signatures_info = []
        
        # Analizza ogni firma presente per estrarre solo le informazioni dei firmatari
        for i, sig in enumerate(pdf_reader.embedded_signatures, 1):
            try:
                # Accedi direttamente al certificato dalla firma senza validazione
                cert = sig.signer_cert
                
                # Estrai informazioni del firmatario
                signer_name = ""
                signer_email = ""
                
                # Prova a estrarre il nome dal subject del certificato
                if hasattr(cert, 'subject') and cert.subject:
                    # Usa l'attributo human_friendly se disponibile
                    if hasattr(cert.subject, 'human_friendly'):
                        signer_name = cert.subject.human_friendly
                    else:
                        # Fallback: estrai manualmente dal subject
                        for attr in cert.subject:
                            if hasattr(attr, 'oid') and attr.oid._name == 'commonName':
                                signer_name = str(attr.value)
                            elif hasattr(attr, 'oid') and attr.oid._name == 'emailAddress':
                                signer_email = str(attr.value)
                
                # Se non trovato nel subject, prova nei SAN
                if not signer_name and hasattr(cert, 'extensions'):
                    for ext in cert.extensions:
                        if hasattr(ext, 'oid') and ext.oid._name == 'subjectAltName':
                            for name in ext.value:
                                if isinstance(name, tuple) and name[0] == 'email':
                                    signer_email = name[1]
                                elif isinstance(name, tuple) and name[0] == 'dirName':
                                    # Prova a estrarre il nome dal DN
                                    pass
                
                # Data di firma - estrai direttamente dalla firma
                sign_date = None
                if hasattr(sig, 'signature_object') and sig.signature_object:
                    try:
                        sign_date = sig.signature_object.get_signing_time()
                    except:
                        pass
                
                # Livello della firma
                signature_level = "Unknown"
                if hasattr(sig, 'signature_object') and sig.signature_object:
                    try:
                        if hasattr(sig.signature_object, 'signature_level'):
                            signature_level = str(sig.signature_object.signature_level)
                    except:
                        pass
                
                signature_info = {
                    "cert": cert,
                    "signature_number": i,
                    "signer_name": signer_name or "Non disponibile",
                    "signer_email": signer_email or "Non disponibile",
                    "sign_date": sign_date.isoformat() if sign_date else "Non disponibile",
                    "certificate_subject": str(cert.subject) if hasattr(cert, 'subject') else "Non disponibile",
                    "certificate_issuer": str(cert.issuer) if hasattr(cert, 'issuer') else "Non disponibile",
                    "certificate_valid_from": cert.not_valid_before.isoformat() if hasattr(cert, 'not_valid_before') and cert.not_valid_before else "Non disponibile",
                    "certificate_valid_to": cert.not_valid_after.isoformat() if hasattr(cert, 'not_valid_after') and cert.not_valid_after else "Non disponibile",
                    "signature_level": signature_level,
                    "serial_number": cert.serial_number if hasattr(cert, 'serial_number') else "Non disponibile"
                }
                
                signatures_info.append(signature_info)
                
            except Exception as e:
                # Se c'è un errore nell'analisi di una singola firma
                signature_info = {
                    "signature_number": i,
                    "signer_name": f"Errore nell'analisi: {str(e)}",
                    "signer_email": "Non disponibile",
                    "sign_date": "Non disponibile",
                    "certificate_subject": "Non disponibile",
                    "certificate_issuer": "Non disponibile",
                    "certificate_valid_from": "Non disponibile",
                    "certificate_valid_to": "Non disponibile",
                    "signature_level": "Unknown",
                    "serial_number": "Non disponibile"
                }
                signatures_info.append(signature_info)
        
        # Riepilogo delle firme trovate
        summary = f"Trovate {len(signatures_info)} firme digitali nel documento"
        
        return {
            "total_signatures": len(signatures_info),
            "signatures": signatures_info,
            "summary": summary
        }
        
    except RequestException as e:
        return {
            "type": "error",
            "content": f"Errore durante il download del PDF: {str(e)}"
        }
    except Exception as e:
        return {
            "type": "error",
            "content": f"Errore durante la verifica delle firme: {str(e)}"
        }
   