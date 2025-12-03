from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import os, requests, time

app = FastAPI(title="Personal AI Backend")

# --------------------------
# Simple token check
# --------------------------
def check_auth(auth: str | None):
    if not auth:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    token = auth.replace("Bearer ", "")
    allowed = [os.getenv("JWT_SECRET", "demo-secret"), "demo-token"]
    if token not in allowed:
        raise HTTPException(status_code=401, detail="Invalid token")
    return True

# --------------------------
# API Schema
# --------------------------
class ChatReq(BaseModel):
    question: str
    url: str | None = None

# --------------------------
# HEALTH CHECK
# --------------------------
@app.get("/health")
def health():
    return {"status": "ok"}

# --------------------------
# CHAT ENDPOINT
# --------------------------
@app.post("/chat")
def chat(req: ChatReq, authorization: str | None = Header(default=None)):

    check_auth(authorization)

    OPENAI_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_KEY:
        return {"answer": "Set OPENAI_API_KEY on Render dashboard under Environment Variables"}

    # Prompt for URL scraping (optional)
    if req.url:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
                page = browser.new_page()
                page.goto(req.url, timeout=30000)
                time.sleep(2)
                html = page.content()
                browser.close()

            cleaned = " ".join(html.split())
            req.question = f"Using the following webpage HTML, answer the question: {req.question}\n\nPAGE_HTML:\n{cleaned[:4000]}"

        except Exception as e:
            req.question = f"Error loading URL '{req.url}': {str(e)}. Just answer based on user question: {req.question}"

    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": req.question}],
        "max_tokens": 350
    }

    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        json=payload,
        headers={"Authorization": f"Bearer {OPENAI_KEY}"},
        timeout=30
    )
    
    j = r.json()
    return {"answer": j["choices"][0]["message"]["content"]}
