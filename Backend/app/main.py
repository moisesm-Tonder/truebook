import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, processes, files, results

app = FastAPI(
    title="AFinOps Tonder — Contabilidad API",
    version="1.0.0",
    description="Backend del sistema de cierre contable mensual de Tonder",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(processes.router)
app.include_router(files.router)
app.include_router(results.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "AFinOps Tonder API"}
