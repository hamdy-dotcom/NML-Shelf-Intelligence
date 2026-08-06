"""Standalone dev wrapper — runs only the genome router on its own port."""
import logging

from fastapi import FastAPI

from genome.router import router as genome_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s")

app = FastAPI(title="NML Genome (standalone)", version="0.1.0")
app.include_router(genome_router)
