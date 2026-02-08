from fpdf import FPDF
import os
from datetime import datetime

def generate_incident_pdf(photo_path, description, output_dir="app/output"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Incident Report", ln=1)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Date: {datetime.now().isoformat()}", ln=1)
    pdf.cell(0, 10, f"Description: {description}", ln=1)
    pdf.image(photo_path, x=10, y=40, w=pdf.w - 20)
    os.makedirs(output_dir, exist_ok=True)
    pdf_path = os.path.join(output_dir, f"incident_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf")
    pdf.output(pdf_path)
    return pdf_path
