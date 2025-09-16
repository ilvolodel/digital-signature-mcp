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
    description="Gets an authentication token from the Infocert Services.",
    tags=["auth", "services"]
)
def auth_token(
    username: Annotated[str, Field(description="Username")],
    password: Annotated[str, Field(description="Password")]
) -> dict:
    """
    Gets an authentication token from the Infocert Services.
    
    Args:
        username (str): Services username
        password (str): Services password
        
    Returns:
        dict: Dictionary containing the token and other authentication information
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
    description="Gets the list of available certificates from Infocert Digital.",
    tags=["certificates", "services"]
)
def get_certificates(
    access_token: Annotated[str, Field(description="Access token for authentication")]
) -> dict:
    """
    Gets the list of available certificates from Infocert Digital.
    
    Args:
        access_token (str): Access token for authentication
        
    Returns:
        dict: Dictionary containing the list of certificates or error information
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
    description="Requests an SMSP challenge for digital signature authentication. send the opt to user by sms",
    tags=["auth", "services", "smsp"]
)
def request_smsp_challenge(
    access_token: Annotated[str, Field(description="Access token for authentication")]
) -> dict:
    """
    Requests an SMSP challenge for digital signature authentication.
    
    Args:
        access_token (str): Access token for authentication
        
    Returns:
        dict: Dictionary containing the challenge response or error information
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
    description="Authorizes an SMSP signature request.",
    tags=["auth", "services", "smsp"]
)
def authorize_smsp(
    access_token: Annotated[str, Field(description="Access token for authentication")],
    certificate_id: Annotated[str, Field(description="Certificate ID")],
    transactionId: Annotated[str, Field(description="Transaction ID")],
    otp: Annotated[str, Field(description="One-time password")],
    pin: Annotated[str, Field(description="PIN code")]
) -> dict:
    """
    Authorizes an SMSP signature request.
    
    Args:
        access_token (str): Access token for authentication
        certificate_id (str): Certificate ID
        transactionId (str): Transaction ID
        otp (str): One-time password
        pin (str): PIN code
        
    Returns:
        dict: Dictionary containing the authorization response or error information
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
    description="Signs a document using Infocert Digital signature service.",
    tags=["signature", "services"]
)
def sign_document(
    certificate_id: Annotated[str, Field(description="Certificate ID")],
    access_token: Annotated[str, Field(description="Access token for authentication")],
    infocert_sat: Annotated[str, Field(description="SAT token from SMSP authorization")],
    transaction_id: Annotated[str, Field(description="Transaction ID from SMSP challenge")],
    pin: Annotated[str, Field(description="PIN code")],
    link_pdf: Annotated[str, Field(description="Link of the document to sign")]
) -> dict:
    """
    Signs a document using Infocert Digital signature service.
    
    Args:
        access_token (str): Access token for authentication
        certificate_id (str): Certificate ID
        infocert_sat (str): SAT token from SMSP authorization
        transaction_id (str): Transaction ID from SMSP challenge
        pin (str): PIN code
        link_pdf (str): Link of the document to sign
        
    Returns:
        dict: Dictionary containing the signature response or error information
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
