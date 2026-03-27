from flask import Flask, render_template, request, send_file, jsonify
import fitz  # PyMuPDF
import io
import os
import psycopg2
from psycopg2 import errors

app = Flask(__name__)
# На сервере лучше отключать DEBUG или полагаться на логи Render
app.config["DEBUG"] = os.environ.get("FLASK_DEBUG", "False") == "True"

# ------------------- PostgreSQL (Supabase) -------------------

# Берем строку подключения из переменных окружения Render
DB_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    # Создает новое соединение с Supabase
    return psycopg2.connect(DB_URL)

def init_db():
    """Создает таблицу, если она еще не создана в Supabase"""
    if not DB_URL:
        print("DATABASE_URL не настроена. Пропускаю инициализацию БД.")
        return
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id SERIAL PRIMARY KEY,
                type TEXT NOT NULL,
                ip TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("БД проверена/инициализирована успешно.")
    except Exception as e:
        print(f"Не удалось инициализировать БД: {e}")

# Запускаем проверку таблицы при старте приложения
init_db()

def get_user_ip():
    # Важно для Render: берем реальный IP пользователя из заголовков прокси
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0]
    return request.remote_addr

def add_feedback(feedback_type):
    ip = get_user_ip()
    success = True
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO feedback (type, ip) VALUES (%s, %s)",
            (feedback_type, ip)
        )
        conn.commit()
        cur.close()
    except errors.UniqueViolation:
        success = False
    except Exception as e:
        print(f"Database error: {e}")
        success = False
    finally:
        if conn:
            conn.close()
    return success

def get_feedback():
    conn = None
    likes, dislikes = 0, 0
    try:
        if DB_URL:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM feedback WHERE type='like'")
            likes = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM feedback WHERE type='dislike'")
            dislikes = cur.fetchone()[0]
            cur.close()
    except Exception as e:
        print(f"Error fetching stats: {e}")
    finally:
        if conn:
            conn.close()
    return {"likes": likes, "dislikes": dislikes}

# ------------------- PDF -------------------

@app.route("/", methods=["GET", "POST"])
def index():
    try:
        if request.method == "POST":
            if "pdf_file" not in request.files or request.files["pdf_file"].filename == '':
                return "Keine Datei ausgewählt"

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
            new_doc.save(output_stream, garbage=4, deflate=True, deflate_images=True, 
                         deflate_fonts=True, clean=True)
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

# ------------------- Feedback API -------------------

@app.route("/feedback", methods=["POST"])
def feedback():
    action = request.form.get("action")
    if action in ["like", "dislike"]:
        if not add_feedback(action):
            return jsonify({
                "message": "Вы уже голосовали", 
                **get_feedback()
            })
    return jsonify(get_feedback())

@app.route("/feedback", methods=["GET"])
def feedback_stats():
    return jsonify(get_feedback())

# ------------------- Run (Исправлено для Render) -------------------

if __name__ == "__main__":
    # Читаем порт, который дает Render. Если локально — используем 5000.
    port = int(os.environ.get("PORT", 5000))
    # host="0.0.0.0" обязателен для работы в облаке!
    app.run(host="0.0.0.0", port=port)
