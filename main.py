import os
import discogs_client
from discogs_client import Client

from dotenv import load_dotenv
from typing import Any
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware


load_dotenv()

DISCOGS_BASE_URL = "https://api.discogs.com"
HEADERS = {"User-Agent": "DiscogsRecommenderApp/1.0"}
CONSUMER_KEY = os.getenv("CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("CONSUMER_SECRET")
SECRET_KEY = os.getenv("SECRET_KEY")
USER_AGENT = "DiscogsRecommenderApp/1.0"

if not all([CONSUMER_KEY, CONSUMER_SECRET]):
    raise RuntimeError("Configure CONSUMER_KEY and CONSUMER_SECRET in .env")

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)


def get_auth_client(token: str, secret: str) -> Client:
    return discogs_client.Client(USER_AGENT, consumer_key=CONSUMER_KEY,
        consumer_secret=CONSUMER_SECRET, token=token, secret=secret)


@app.get("/auth/login")
async def login(request: Request) -> RedirectResponse:
    client = discogs_client.Client(USER_AGENT)
    client.set_consumer_key(CONSUMER_KEY, CONSUMER_SECRET)
    oauth_token, oauth_secret, authorize_url = client.get_authorize_url(
        "http://localhost:8000/auth/callback")
    request.session["request_token_secret"] = oauth_secret
    request.session["request_token"] = oauth_token
    return RedirectResponse(authorize_url)


@app.get("/auth/callback")
async def callback(request: Request, oauth_token: str = None, 
    oauth_verifier: str = None) -> JSONResponse:
    
    if not all([oauth_token, oauth_verifier]):
        return JSONResponse({"error": "missing oauth_token or oauth_verifier"},
            status_code=400)
    
    request_token = request.session.get("request_token")
    request_secret = request.session.get("request_token_secret")
    if not all([request_token, request_secret]):
        return JSONResponse({"error": "session expired or invalid"}, 
            status_code=400)
    
    auth_client = get_auth_client(request_token, request_secret)
    access_token, access_secret = auth_client.get_access_token(oauth_verifier)
    auth_client = get_auth_client(access_token, access_secret)
    me = auth_client.identity()
    
    return JSONResponse({"username": me.username, "name": me.name, 
        "location": me.location, "access_token": access_token, 
        "access_secret": access_secret})


@app.get("/me/collection")
async def get_collection(oauth_token: str, oauth_secret: str) -> dict[str, Any]:
    auth_client = get_auth_client(oauth_token, oauth_secret)
    me = auth_client.identity()
    collection = me.collection_folders[0].releases
    return {"collection": [r.release.title for r in collection]}