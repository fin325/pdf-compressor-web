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
            quality = int(request.form.get("quality", 60))   # качество от 10 до 100

            # Читаем файл
            data = file.read()
            doc = fitz.open(stream=data, filetype="pdf")
            new_doc = fitz.open()

            # === Основная логика сжатия ===
            scale = quality / 100.0                     # 60% качества → scale = 0.6
            for page in doc:
                # Рендерим страницу с уменьшенным разрешением
                pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)

                # Создаём новую страницу того же размера
                new_page = new_doc.new_page(width=pix.width, height=pix.height)

                # Вставляем как JPEG с качеством (чем ниже quality — тем сильнее сжатие)
                new_page.insert_image(
                    fitz.Rect(0, 0, pix.width, pix.height),
                    pixmap=pix,
                    compress="jpeg",          # важно!
                    quality=quality           # используем значение из формы
                )

            # Сохраняем с максимальным сжатием
            output_stream = io.BytesIO()
            new_doc.save(
                output_stream,
                garbage=4,           # удаляем ненужные объекты
                deflate=True,        # сжимаем потоки
                deflate_images=True,
                deflate_fonts=True,
                clean=True
            )
            output_stream.seek(0)

            doc.close()
            new_doc.close()

            return send_file(
                output_stream,
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
