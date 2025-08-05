import os
import secrets
import httpx
import discogs_client

from dotenv import load_dotenv
from typing import Dict
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

load_dotenv()

DISCOGS_BASE_URL = "https://api.discogs.com"
HEADERS = {"User-Agent": "DiscogsRecommenderApp/1.0"}
CONSUMER_KEY = os.getenv("CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("CONSUMER_SECRET")
USER_AGENT = "DiscogsRecommenderApp/1.0"

if not all([CONSUMER_KEY, CONSUMER_SECRET]):
    raise RuntimeError("Configure CONSUMER_KEY and CONSUMER_SECRET in .env")

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=secrets.token_hex(32))

request_tokens: Dict[str, str] = {}

@app.get("/auth/login")
async def login(request: Request):
    client = discogs_client.Client(USER_AGENT)
    client.set_consumer_key(CONSUMER_KEY, CONSUMER_SECRET)
    oauth_token, oauth_secret, authorize_url = client.get_authorize_url(
        "http://localhost:8000/auth/callback"
    )
    request.session["request_token_secret"] = oauth_secret
    return RedirectResponse(authorize_url)

@app.get("/auth/callback")
async def callback(request: Request, oauth_token: str = None, oauth_verifier: str = None):
    if not all([oauth_token, oauth_verifier]):
        return JSONResponse({"error": "missing oauth_token or oauth_verifier"}, status_code=400)
    
    oauth_secret = request.session.get("request_token_secret")
    if oauth_secret is None:
        return JSONResponse({"error": "session expired or invalid"}, status_code=400)
    
    client = discogs_client.Client(USER_AGENT)
    client.set_consumer_key(CONSUMER_KEY, CONSUMER_SECRET)
    access_token, access_secret = client.get_access_token(oauth_verifier)
    auth_client = discogs_client.Client(
        USER_AGENT,
        consumer_key=CONSUMER_KEY,
        consumer_secret=CONSUMER_SECRET,
        token=access_token,
        secret=access_secret
    )
    me = auth_client.identity()
    return JSONResponse({
        "username": me.username,
        "name": me.name,
        "location": me.location,
        "access_token": access_token,
        "access_secret": access_secret
    })
    
@app.get("/me/collection")
async def get_collection(oauth_token: str, oauth_secret: str):
    auth_client = discogs_client.Client(
        USER_AGENT,
        consumer_key=CONSUMER_KEY,
        consumer_secret=CONSUMER_SECRET,
        token=oauth_token,
        secret=oauth_secret
    )
    me = auth_client.identity()
    collection = auth_client.user(me.username).collection_folders[0].releases
    return {"count": collection.count, "titles": [r.release.title for r in collection]}


@app.get("/release/{release_id}")
async def get_release(release_id: int):
    async with httpx.AsyncClient() as client:
        url = f"{DISCOGS_BASE_URL}/releases/{release_id}"
        response = await client.get(url, headers=HEADERS)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": "Release not found", 
                "status_code": response.status_code}