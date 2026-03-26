from flask import Flask, render_template, request, send_file
import fitz  # PyMuPDF
import io

app = Flask(__name__)
app.config["DEBUG"] = True

@app.route("/", methods=["GET", "POST"])
def index():
    try:
        if request.method == "POST":

            if "pdf_file" not in request.files:
                return "Keine Datei übertragen"

            file = request.files["pdf_file"]

            if file.filename == '':
                return "Keine Datei ausgewählt"

            quality = int(request.form.get("quality", 50))

            data = file.read()

            pdf = fitz.open(stream=data, filetype="pdf")
            new_pdf = fitz.open()
            new_pdf_stream = io.BytesIO()

            # Сжатие страниц
            for page in pdf:
                pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5))   # 0.5 = среднее сжатие
                page_new = new_pdf.new_page(width=pix.width, height=pix.height)
                page_new.insert_image(
                    fitz.Rect(0, 0, pix.width, pix.height),
                    stream=pix.tobytes("ppm")
                )

            new_pdf.save(new_pdf_stream)
            new_pdf_stream.seek(0)

            return send_file(
                new_pdf_stream,
                as_attachment=True,
                download_name="komprimierte_datei.pdf",
                mimetype="application/pdf"
            )

        # GET — показ формы
        return render_template("index.html", title="PDF Compressor")

    except Exception as e:
        import traceback
        return f"<h2>FEHLER:</h2><pre>{traceback.format_exc()}</pre>"


if __name__ == "__main__":
    app.run(debug=True)
