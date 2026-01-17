from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api.v1.endpoints import validator

app = FastAPI(title="YouTube Script Validator")

# Mount the static folder so users can download PDFs
# This means files in /static will be accessible at http://localhost:8000/static/filename.pdf
app.mount("/static", StaticFiles(directory="static"), name="static")

# Connect the router
app.include_router(validator.router, prefix="/api/v1", tags=["validator"])

@app.get("/")
def root():
    return {"message": "Script Validator API is live. Send POST to /api/v1/validate"}