import os
from flask import Flask, request, render_template, send_file, redirect, url_for
import fitz  # PyMuPDF
from PIL import Image
from io import BytesIO
import uuid

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def index():
    download_links = []

    if request.method == "POST":
        files = request.files.getlist("pdf_files")
        quality = int(request.form.get("quality", 75))

        for file in files:
            if file and file.filename.endswith(".pdf"):
                unique_name = f"{uuid.uuid4().hex}_{file.filename}"
                input_path = os.path.join(UPLOAD_FOLDER, unique_name)
                output_path = os.path.join(UPLOAD_FOLDER, "compressed_" + unique_name)
                file.save(input_path)

                compress_pdf(input_path, output_path, quality)
                download_links.append(url_for("download", filename=os.path.basename(output_path)))

    return render_template("index.html", download_links=download_links)

def compress_pdf(input_pdf, output_pdf, quality):
    """Сжимает изображения внутри PDF до указанного качества"""
    doc = fitz.open(input_pdf)

    for page in doc:
        images = page.get_images(full=True)
        for img_index, img in enumerate(images):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]

            image = Image.open(BytesIO(image_bytes))
            img_buffer = BytesIO()
            image = image.convert("RGB")
            image.save(img_buffer, format="JPEG", quality=quality)
            img_buffer.seek(0)

            doc.update_image(xref, img_buffer.read())

    doc.save(output_pdf)

@app.route("/download/<filename>")
def download(filename):
    return send_file(os.path.join(UPLOAD_FOLDER, filename), as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
