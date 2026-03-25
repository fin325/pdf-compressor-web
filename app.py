from flask import Flask, render_template, request, send_file
import fitz  # PyMuPDF
from PIL import Image
import io

app = Flask(__name__)
app.config["DEBUG"] = True  # 🔥 включаем отладку

@app.route("/", methods=["GET", "POST"])
def index():
    try:
        if request.method == "POST":

            if "pdf_file" not in request.files:
                return "Файл не передан"

            file = request.files["pdf_file"]
            quality = int(request.form.get("quality", 50))

            data = file.read()

            if len(data) == 0:
                return "Пустой файл"

            if len(data) > 10 * 1024 * 1024:
                return "Файл слишком большой (макс 10MB)"

            pdf = fitz.open(stream=data, filetype="pdf")
            new_pdf_stream = io.BytesIO()

            new_pdf = fitz.open()

            for page in pdf:
    pix = page.get_pixmap(matrix=fitz.Matrix(0.25, 0.25))

    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG", quality=quality)
    img_bytes.seek(0)

    rect = fitz.Rect(0, 0, pix.width, pix.height)
    page_new = new_pdf.new_page(width=pix.width, height=pix.height)
    page_new.insert_image(rect, stream=img_bytes.getvalue())

            new_pdf.save(new_pdf_stream)
            new_pdf_stream.seek(0)

            return send_file(
                new_pdf_stream,
                as_attachment=True,
                download_name="compressed.pdf",
                mimetype="application/pdf"
            )

        return render_template("index.html")

    except Exception as e:
        return f"ОШИБКА: {str(e)}"  # 🔥 теперь увидим реальную причину


if __name__ == "__main__":
    app.run(debug=True)
