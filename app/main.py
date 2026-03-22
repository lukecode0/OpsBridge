from fastapi import FastAPI


app = FastAPI(title="OpsBridge")


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}
