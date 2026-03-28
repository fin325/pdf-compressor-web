from flask import Flask, render_template, request, send_file, jsonify
import fitz
import io
import os
import psycopg2
from psycopg2 import errors

app = Flask(__name__)
app.config["DEBUG"] = os.environ.get("FLASK_DEBUG", "False") == "True"

# ------------------- DATABASE -------------------

DB_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DB_URL, sslmode="require")

def add_feedback(feedback_type, user_ip):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO feedback (type, ip) VALUES (%s, %s) RETURNING id",
            (feedback_type, user_ip)
        )
        feedback_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        return feedback_id
    except errors.UniqueViolation:
        return "already_voted" 
    except Exception as e:
        print(f"❌ Ошибка записи: {e}")
        return None
    finally:
        if conn:
            conn.close()

def delete_feedback(feedback_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM feedback WHERE id = %s", (feedback_id,))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Ошибка удаления: {e}")
        return False

def get_feedback():
    likes = 0
    dislikes = 0
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM feedback WHERE type='like'")
        likes = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM feedback WHERE type='dislike'")
        dislikes = cur.fetchone()[0]
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Ошибка чтения: {e}")
    
    total = likes + dislikes
    percent = int((likes / total) * 100) if total > 0 else 0
    return {"likes": likes, "dislikes": dislikes, "percent": percent}

# ------------------- ROUTES -------------------

@app.route("/")
def index():
    # Теперь главная страница только отображает HTML
    return render_template("index.html", title="PDF Compressor")

@app.route("/compress", methods=["POST"])
def compress_pdf():
    # Теперь вся логика сжатия здесь
    try:
        if "pdf_file" not in request.files or request.files["pdf_file"].filename == '':
            return "Keine Datei ausgewählt", 400

        file = request.files["pdf_file"]
        quality = int(request.form.get("quality", "30"))

        data = file.read()
        doc = fitz.open(stream=data, filetype="pdf")
        new_doc = fitz.open()

        scale = quality / 100.0

        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            new_page = new_doc.new_page(width=pix.width, height=pix.height)
            new_page.insert_image(fitz.Rect(0, 0, pix.width, pix.height), pixmap=pix)

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
            download_name="compressed.pdf",
            mimetype="application/pdf"
        )
    except Exception as e:
        import traceback
        return f"<h2>FEHLER:</h2><pre>{traceback.format_exc()}</pre>", 500

# ------------------- FEEDBACK API -------------------

@app.route("/feedback", methods=["GET", "POST"])
def feedback_api():
    # Получаем IP пользователя
    if request.headers.get('X-Forwarded-For'):
        ip = request.headers.get('X-Forwarded-For').split(',')[0]
    else:
        ip = request.remote_addr

    if request.method == "POST":
        action = request.form.get("action")
        feedback_id = request.form.get("id")

        if action == "remove" and feedback_id:
            delete_feedback(feedback_id)
            return jsonify(get_feedback())

        if action in ["like", "dislike"]:
            new_id = add_feedback(action, ip)
            stats = get_feedback()
            
            if new_id == "already_voted":
                return jsonify({"error": "Already voted", **stats}), 200
            
            return jsonify({"id": new_id, **stats})

    # GET запрос возвращает статистику
    return jsonify(get_feedback())

# ------------------- RUN -------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
