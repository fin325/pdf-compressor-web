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
            
            # Получаем качество из кнопок
            quality_str = request.form.get("quality", "30")
            quality = int(quality_str)

            data = file.read()
            doc = fitz.open(stream=data, filetype="pdf")
            new_doc = fitz.open()

            scale = quality / 100.0

            for page in doc:
                pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)

                new_page = new_doc.new_page(width=pix.width, height=pix.height)

                new_page.insert_image(
                    fitz.Rect(0, 0, pix.width, pix.height),
                    pixmap=pix
                )

            output_stream = io.BytesIO()
            new_doc.save(
                output_stream,
                garbage=4,
                deflate=True,
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
