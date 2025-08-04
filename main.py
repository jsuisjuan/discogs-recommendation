import httpx
from fastapi import FastAPI

app = FastAPI()

DISCOGS_BASE_URL = "https://api.discogs.com"
HEADERS = {
    "User-Agent": "HouseRecommenderApp/1.0"
}

@app.get("/release/{release_id}")
async def get_release(release_id: int):
    async with httpx.AsyncClient() as client:
        url = f"{DISCOGS_BASE_URL}/releases/{release_id}"
        response = await client.get(url, headers=HEADERS)
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "error": "Release not found", 
                "status_code": response.status_code
            }