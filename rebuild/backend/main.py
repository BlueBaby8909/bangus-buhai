from fastapi import FastAPI

app = FastAPI(title="Bangus Buhai Rebuild")

@app.get("/health")

def health():
    return {"status": "ok", "service": "bangus-buhai-rebuild"}