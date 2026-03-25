from flask import Flask, render_template, request, send_file
import fitz  # PyMuPDF
from PIL import Image
import io

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        file = request.files.get("pdf_file")
        quality = int(request.form.get("quality", 50))

        if not file:
            return "Нет файла PDF"

        pdf = fitz.open(stream=file.read(), filetype="pdf")
        new_pdf_stream = io.BytesIO()

        # Создаём новый PDF
        new_pdf = fitz.open()
        for page in pdf:
            pix = page.get_pixmap()  # рендер страницы
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            img_bytes = io.BytesIO()
            img.save(img_bytes, format="JPEG", quality=quality)
            img_bytes.seek(0)

            # Добавляем сжатое изображение как новую страницу
            img_pdf = fitz.open("pdf", img_bytes.read())
            new_pdf.insert_pdf(img_pdf)

        new_pdf.save(new_pdf_stream)
        new_pdf_stream.seek(0)

        return send_file(
            new_pdf_stream,
            as_attachment=True,
            download_name="compressed.pdf",
            mimetype="application/pdf"
        )

    return render_template("index.html")
    

if __name__ == "__main__":
    app.run(debug=True)
