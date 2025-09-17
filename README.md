# Firma Digitale MCP Server

Server MCP per la firma digitale di documenti PDF utilizzando i servizi Infocert e il caricamento automatico su DigitalOcean Spaces.

## Configurazione

### Variabili d'Ambiente

Crea un file `.env` nella root del progetto con le seguenti variabili:

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

### Ottenere le Credenziali

#### Infocert
- Contatta Infocert per ottenere le credenziali API
- `CLIENT_ID` e `CLIENT_SECRET` per l'autenticazione OAuth2
- `TENANT` per identificare il tuo tenant

#### DigitalOcean Spaces
1. Accedi al tuo account DigitalOcean
2. Vai su "API" nel menu laterale
3. Crea una nuova API Key con permessi di Spaces
4. Crea un nuovo Space nella regione desiderata
5. Usa le credenziali e il nome del bucket nelle variabili d'ambiente

## Installazione

```bash
pip install -r requirements.txt
```

## Utilizzo

Il server fornisce i seguenti tool MCP:

1. **auth_token**: Autenticazione con i servizi Infocert
2. **get_certificates**: Recupera i certificati digitali disponibili
3. **request_smsp_challenge**: Richiede un codice OTP via SMS
4. **authorize_smsp**: Autorizza la firma con OTP e PIN
5. **sign_document**: Firma un documento PDF e lo carica su DigitalOcean Spaces

### Flusso di Firma

1. Autenticati con `auth_token`
2. Recupera i certificati con `get_certificates`
3. Richiedi un challenge SMS con `request_smsp_challenge`
4. Autorizza con `authorize_smsp` usando OTP e PIN
5. Firma il documento con `sign_document`

Il documento firmato verrà automaticamente caricato su DigitalOcean Spaces e l'URL sarà restituito nella risposta.

## Funzionalità

- ✅ Firma digitale PAdES BASELINE-B
- ✅ Autenticazione a due fattori via SMS
- ✅ Caricamento automatico su DigitalOcean Spaces
- ✅ Gestione sicura delle credenziali tramite variabili d'ambiente
- ✅ File PDF firmati organizzati con timestamp
