# === PDF Compressor App ===
# DE: Flask-Anwendung zur PDF-Komprimierung mit Like/Dislike-Bewertungssystem
# RU: Flask-приложение для сжатия PDF с системой оценок Like/Dislike
# EN: Flask application for PDF compression with Like/Dislike rating system

from flask import Flask, render_template, request, send_file, jsonify
import fitz
import io
import os
import psycopg2
from psycopg2 import errors

app = Flask(__name__)
app.config["DEBUG"] = os.environ.get("FLASK_DEBUG", "False") == "True"

# ------------------- DATABASE / DATENBANK / БАЗА ДАННЫХ -------------------

# DE: Verbindungs-URL aus Umgebungsvariable
# RU: URL подключения из переменной окружения
# EN: Connection URL from environment variable
DB_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    # DE: Stellt eine sichere Verbindung zur PostgreSQL-Datenbank her
    # RU: Устанавливает защищённое соединение с базой данных PostgreSQL
    # EN: Establishes a secure connection to the PostgreSQL database
    return psycopg2.connect(DB_URL, sslmode="require")


def add_feedback(feedback_type, user_ip):
    # DE: Fügt eine Bewertung hinzu / aktualisiert / entfernt sie und passt den Zähler an
    # RU: Добавляет / обновляет / удаляет голос и корректирует счётчик
    # EN: Adds / updates / removes a vote and adjusts the counter
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # DE: Prüfen, ob diese IP bereits abgestimmt hat (innerhalb der letzten 6 Tage)
        # RU: Проверяем, голосовал ли уже этот IP (за последние 6 дней)
        # EN: Check whether this IP has already voted (within the last 6 days)
        cur.execute("SELECT id, type FROM feedback WHERE ip = %s", (user_ip,))
        existing_vote = cur.fetchone()

        if existing_vote:
            vote_id, v_type = existing_vote

            # DE: Gleiche Schaltfläche erneut geklickt — Stimme wird zurückgenommen
            # RU: Нажата та же кнопка — голос отменяется
            # EN: Same button clicked again — vote is removed
            if v_type == feedback_type:
                cur.execute("DELETE FROM feedback WHERE id = %s", (vote_id,))
                cur.execute(
                    "UPDATE feedback_totals SET count = GREATEST(count - 1, 0) WHERE type = %s",
                    (feedback_type,)
                )
                conn.commit()
                return "removed"
            else:
                # DE: Anderer Typ — Stimme wird geändert (z. B. von Like zu Dislike)
                # RU: Другой тип — голос изменяется (например, с лайка на дизлайк)
                # EN: Different type — vote is changed (e.g. from like to dislike)
                cur.execute("UPDATE feedback SET type = %s WHERE id = %s", (feedback_type, vote_id))
                cur.execute(
                    "UPDATE feedback_totals SET count = GREATEST(count - 1, 0) WHERE type = %s",
                    (v_type,)
                )
                cur.execute(
                    "UPDATE feedback_totals SET count = count + 1 WHERE type = %s",
                    (feedback_type,)
                )
                conn.commit()
                return "updated"
        else:
            # DE: Erste Stimme dieser IP — neue Zeile einfügen und Zähler erhöhen
            # RU: Первый голос этого IP — добавляем запись и увеличиваем счётчик
            # EN: First vote of this IP — insert new row and increment counter
            cur.execute(
                "INSERT INTO feedback (type, ip) VALUES (%s, %s) RETURNING id",
                (feedback_type, user_ip)
            )
            new_id = cur.fetchone()[0]
            cur.execute(
                "UPDATE feedback_totals SET count = count + 1 WHERE type = %s",
                (feedback_type,)
            )
            conn.commit()
            return new_id

    except Exception as e:
        # DE / RU / EN: Datenbankfehler / Ошибка БД / Database error
        print(f"❌ Datenbankfehler / Ошибка БД / Database error: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            conn.close()


def delete_feedback(feedback_id):
    # DE: Löscht eine einzelne Bewertung manuell (Admin-Funktion)
    # RU: Удаляет один голос вручную (админская функция)
    # EN: Manually deletes a single vote (admin function)
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM feedback WHERE id = %s", (feedback_id,))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Löschfehler / Ошибка удаления / Delete error: {e}")
        return False


def get_feedback():
    # DE: Liest die aggregierten Zählerstände aus feedback_totals (dauerhafte Statistik)
    # RU: Читает агрегированные счётчики из feedback_totals (постоянная статистика)
    # EN: Reads aggregated counters from feedback_totals (persistent statistics)
    likes = 0
    dislikes = 0
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT type, count FROM feedback_totals")
        rows = cur.fetchall()
        for row in rows:
            if row[0] == 'like':
                likes = row[1]
            elif row[0] == 'dislike':
                dislikes = row[1]
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Lesefehler / Ошибка чтения / Read error: {e}")

    total = likes + dislikes
    percent = int((likes / total) * 100) if total > 0 else 0
    return {"likes": likes, "dislikes": dislikes, "percent": percent}


# ------------------- ROUTES / ROUTEN / МАРШРУТЫ -------------------

@app.route("/")
def index():
    # DE: Startseite mit dem PDF-Kompressor
    # RU: Главная страница с PDF-компрессором
    # EN: Home page with the PDF compressor
    return render_template("index.html", title="PDF Compressor")


@app.route("/wakeup", methods=["GET"])
def wakeup():
    # DE: Leichter Endpoint zum Aufwecken des Render-Servers (Cold-Start-Vermeidung)
    # RU: Лёгкий эндпоинт для пробуждения сервера Render (избежание cold-start)
    # EN: Lightweight endpoint to wake up the Render server (cold-start avoidance)
    return "OK", 200


@app.route("/compress", methods=["POST"])
def compress_pdf():
    # DE: Empfängt PDF, komprimiert es und gibt die komprimierte Datei zurück
    # RU: Принимает PDF, сжимает его и возвращает сжатый файл
    # EN: Receives PDF, compresses it and returns the compressed file
    try:
        if "pdf_file" not in request.files or request.files["pdf_file"].filename == '':
            # DE: Keine Datei ausgewählt — Fehler 400
            # RU: Файл не выбран — ошибка 400
            # EN: No file selected — error 400
            return "Keine Datei ausgewählt", 400

        file = request.files["pdf_file"]
        quality = int(request.form.get("quality", "30"))

        data = file.read()
        doc = fitz.open(stream=data, filetype="pdf")
        new_doc = fitz.open()

        # DE: Skalierungsfaktor basierend auf gewählter Qualität
        # RU: Коэффициент масштабирования на основе выбранного качества
        # EN: Scale factor based on chosen quality
        scale = quality / 100.0

        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            new_page = new_doc.new_page(width=pix.width, height=pix.height)
            new_page.insert_image(fitz.Rect(0, 0, pix.width, pix.height), pixmap=pix)

        # DE: Komprimiertes PDF im Arbeitsspeicher erstellen
        # RU: Создаём сжатый PDF в оперативной памяти
        # EN: Create compressed PDF in memory
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
        # DE: Fehler beim Verarbeiten der PDF
        # RU: Ошибка при обработке PDF
        # EN: Error while processing PDF
        return f"<h2>FEHLER:</h2><pre>{traceback.format_exc()}</pre>", 500


# ------------------- FEEDBACK API / БЛОК ОЦЕНОК -------------------

@app.route("/feedback", methods=["GET", "POST"])
def feedback_api():
    # DE: API für Like/Dislike-Bewertungen
    # RU: API для оценок Like/Dislike
    # EN: API for Like/Dislike ratings

    # DE: IP-Adresse aus Proxy-Header oder Direktverbindung lesen
    # RU: Получаем IP-адрес из proxy-заголовка или прямого подключения
    # EN: Get IP address from proxy header or direct connection
    if request.headers.get('X-Forwarded-For'):
        ip = request.headers.get('X-Forwarded-For').split(',')[0]
    else:
        ip = request.remote_addr

    if request.method == "POST":
        action = request.form.get("action")

        if action in ["like", "dislike"]:
            # DE: Bewertung verarbeiten und aktualisierte Statistik zurückgeben
            # RU: Обрабатываем голос и возвращаем обновлённую статистику
            # EN: Process the vote and return updated statistics
            result_status = add_feedback(action, ip)
            stats = get_feedback()

            return jsonify({
                "status": result_status,
                **stats
            })

    return jsonify(get_feedback())


# ------------------- RUN / ЗАПУСК / СТАРТ -------------------

if __name__ == "__main__":
    # DE: Lokaler Start (in Produktion via Gunicorn auf Render)
    # RU: Локальный запуск (в продакшене через Gunicorn на Render)
    # EN: Local startup (in production via Gunicorn on Render)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
