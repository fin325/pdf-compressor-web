from flask import Flask, render_template, request, send_file
import fitz  # PyMuPDF
import io

app = Flask(__name__)
app.config["DEBUG"] = True  # 🔥 включаем отладку

MAX_FILE_SIZE_MB = 10

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
            if len(data) > MAX_FILE_SIZE_MB * 1024 * 1024:
                return f"Файл слишком большой (макс {MAX_FILE_SIZE_MB} MB)"

            pdf = fitz.open(stream=data, filetype="pdf")
            new_pdf = fitz.open()
            new_pdf_stream = io.BytesIO()

            # Сжатие каждой страницы
            for page in pdf:
                # Рендер страницы в изображение с уменьшением размера
                pix = page.get_pixmap(matrix=fitz.Matrix(0.25, 0.25))

                # Создаем новую страницу в PDF
                page_new = new_pdf.new_page(width=pix.width, height=pix.height)
                page_new.insert_image(
                    fitz.Rect(0, 0, pix.width, pix.height),
                    stream=pix.tobytes("ppm")  # напрямую без Pillow
                )

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
        # 🔥 Показываем точную ошибку прямо в браузере
        import traceback
        return f"<h2>ОШИБКА:</h2><pre>{traceback.format_exc()}</pre>"

if __name__ == "__main__":
    app.run(debug=True)
