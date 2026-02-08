from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from app.detect import detect_image, detect_video
from app.logs import save_prevention, save_incident
from app.pdf_generator import generate_incident_pdf
import tempfile, shutil, os

app = FastAPI(title="PPE Safety MVP")

@app.post("/detect/image")
async def detect_image_endpoint(file: UploadFile = File(...)):
    try:
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        _, detections, counts, output_path = detect_image(tmp_path, os.path.splitext(file.filename)[0])
        save_prevention(output_path, counts)
        return {"output_path": output_path, "detections": detections, "summary": counts}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/detect/video")
async def detect_video_endpoint(file: UploadFile = File(...)):
    try:
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        output_path, counts = detect_video(tmp_path)
        return {"output_path": output_path, "summary": counts}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/save_incident")
async def save_incident_endpoint(file: UploadFile = File(...), description: str = Form(...)):
    try:
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        pdf_path = generate_incident_pdf(tmp_path, description)
        save_incident(pdf_path, description)
        return {"pdf_path": pdf_path, "description": description}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/download")
async def download_file(path: str):
    if os.path.exists(path):
        return FileResponse(path)
    return JSONResponse({"error": "File not found"}, status_code=404)
