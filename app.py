from flask import Flask, render_template, request, send_file, jsonify
import fitz
import io
import os
import psycopg2
from psycopg2 import errors  # <--- ДОБАВЛЕНО: для обработки ошибки уникальности IP

app = Flask(__name__)
app.config["DEBUG"] = os.environ.get("FLASK_DEBUG", "False") == "True"

# ------------------- DATABASE -------------------

DB_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DB_URL, sslmode="require")

def add_feedback(feedback_type, user_ip): # <--- ИЗМЕНЕНО: добавили аргумент user_ip
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # <--- ИЗМЕНЕНО: записываем и тип, и IP
        cur.execute(
    "INSERT INTO feedback (type, ip) VALUES (%s, %s) RETURNING id",
    (feedback_type, user_ip)
)


        feedback_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        return feedback_id

    except errors.UniqueViolation: # <--- ДОБАВЛЕНО: ловим попытку повторного голоса
        print(f"ℹ️ IP {user_ip} уже есть в базе.")
        return "already_voted" 
    except Exception as e:
        print(f"❌ Ошибка записи: {e}")
        return None
    finally:
        if conn:
            conn.close()

# Функции delete_feedback и get_feedback остаются без изменений (они у тебя верные)
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

# ------------------- PDF ------------------- (Твой код без изменений)
@app.route("/", methods=["GET", "POST"])
def index():
    # ... (весь твой код обработки PDF)
    return render_template("index.html", title="PDF Compressor")

# ------------------- FEEDBACK API -------------------

@app.route("/feedback", methods=["POST"])
def feedback():
    action = request.form.get("action")
    feedback_id = request.form.get("id")

    # 1. Получаем IP пользователя (учитываем прокси Render)
    if request.headers.get('X-Forwarded-For'):
        ip = request.headers.get('X-Forwarded-For').split(',')[0]
    else:
        ip = request.remote_addr

    # 2. Удалить голос (если нужно)
    if action == "remove" and feedback_id:
        delete_feedback(feedback_id)
        stats = get_feedback()
        return jsonify(stats)

    # 3. Поставить лайк/дизлайк с проверкой IP
    if action in ["like", "dislike"]:
        # Передаем IP в функцию add_feedback
        new_id = add_feedback(action, ip)

        # Если функция вернула "already_voted", значит этот IP уже есть в базе
        if new_id == "already_voted":
            stats = get_feedback()
            return jsonify({
                "error": "Already voted", 
                "message": "Du hast bereits abgestimmt!",
                **stats
            }), 200 # Возвращаем 200, чтобы JS мог прочитать статистику

        # Если всё ок, возвращаем ID новой записи и статистику
        stats = get_feedback()
        return jsonify({
            "id": new_id,
            **stats
        })

    return jsonify({"error": "Invalid action"}), 400

@app.route("/feedback", methods=["GET"])
def feedback_stats():
    return jsonify(get_feedback())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

