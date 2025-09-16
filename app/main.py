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
from app.config.setting import settings


# MCP server configuration with additional options
mcp = FastMCP(
    "Signature MCP Server",
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
    description="Firma digitalmente un documento PDF utilizzando il servizio Infocert. Questo tool scarica il documento dal link fornito, lo firma con il certificato specificato e restituisce il documento firmato in formato base64.",
    tags=["signature", "services"]
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
    4. Restituisce il documento firmato
    
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
            - signedDocument: Documento firmato in formato base64
            - signatureId: ID univoco della firma applicata
            - timestamp: Timestamp della firma
            - certificateInfo: Informazioni del certificato utilizzato
            - type: "error" se si verifica un errore
            - content: Messaggio di errore dettagliato
    """
    try:

        # Scarica il PDF dal link fornito
        pdf_response = requests.get(link_pdf)
        pdf_response.raise_for_status()
        
        # Estrai il nome del file dal link
        attach_name = link_pdf.split('/')[-1]
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
        print(result)
        return result

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
