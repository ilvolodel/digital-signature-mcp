from fastmcp import FastMCP  # type: ignore
from typing import Annotated, Dict
from pydantic import Field, BaseModel
from typing import List
import re
import os
import json
import base64
import requests
from requests.exceptions import RequestException
import boto3
from botocore.exceptions import ClientError
from datetime import datetime
from app.config.setting import settings


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

def transform_certificates(data):
    transformed = []
    for item in data:
        subject = item.get("subject", "")
        
        # cerco DNQ=12345 dentro alla stringa subject
        match = re.search(r"DNQ=([0-9]+)", subject)
        certificate_id = match.group(1) if match else None
        
        new_item = {**item}  # copio tutto
        if certificate_id:
            new_item["certificateId"] = certificate_id
        transformed.append(new_item)
    
    return transformed

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
            - subject: Soggetto del certificato
            - issuer: Emittente del certificato
            - validFrom: Data di inizio validità
            - validTo: Data di scadenza
            - serialNumber: Numero seriale del certificato
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
        
        return transform_certificates(result)

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
        clean_url = link_pdf.split('?')[0]  # Rimuove tutto dopo il '?'
        attach_name = clean_url.split('/')[-1]
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
                upload_result = upload_to_digitalocean_spaces(signed_document_bytes, signed_document_name)
                
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
