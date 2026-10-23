from backend.core.application import create_app

app = create_app()

@app.get("/health")
def health():
    return {"status": "ok", "service": "bangus-buhai-rebuild"}
