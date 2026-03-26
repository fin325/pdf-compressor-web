from flask import Flask, render_template, request, send_file
import fitz  # PyMuPDF
import io

app = Flask(__name__)
app.config["DEBUG"] = True

@app.route("/", methods=["GET", "POST"])
def index():
    try:
        if request.method == "POST":
            if "pdf_file" not in request.files or request.files["pdf_file"].filename == '':
                return "Keine Datei ausgewählt"

            file = request.files["pdf_file"]
            quality = int(request.form.get("quality", 60))   # рекомендуемое значение по умолчанию 60

            data = file.read()
            doc = fitz.open(stream=data, filetype="pdf")
            new_doc = fitz.open()

            # Мягкий масштаб + сильное JPEG-сжатие
            scale = 0.75 + (quality / 400.0)   # от ~0.775 при 10% до ~1.0 при 100%

            for page in doc:
                # Рендерим страницу
                pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)

                # Создаём новую страницу
                new_page = new_doc.new_page(width=pix.width, height=pix.height)

                # Важно: конвертируем в JPEG байты с нужным качеством
                img_bytes = pix.tobytes("jpeg", jpg_quality=quality)

                new_page.insert_image(
                    new_page.rect,
                    stream=img_bytes
                )

            # Сильное сжатие при сохранении
            output = io.BytesIO()
            new_doc.save(
                output,
                garbage=4,           # максимальная очистка
                deflate=True,
                deflate_images=True,
                deflate_fonts=True,
                clean=True
            )
            output.seek(0)

            doc.close()
            new_doc.close()

            return send_file(
                output,
                as_attachment=True,
                download_name="komprimierte_datei.pdf",
                mimetype="application/pdf"
            )

        return render_template("index.html", title="PDF Compressor")

    except Exception as e:
        import traceback
        return f"<h2>FEHLER:</h2><pre>{traceback.format_exc()}</pre>"


if __name__ == "__main__":
    app.run(debug=True)
