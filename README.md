# PDF Compressor Web App

![Tests](https://github.com/fin325/pdf-compressor-web/actions/workflows/python-tests.yml/badge.svg)

Ein webbasierter PDF-Kompressor mit Feedback-System und automatischen Tests.

-----

## 🚀 Live-Demo

🔗 [pdf-compressor-web.onrender.com](https://pdf-compressor-web.onrender.com)

-----

## ⚙️ Tech Stack

|Komponente      |Technologie          |
|----------------|---------------------|
|Backend         |Python, Flask        |
|PDF-Verarbeitung|PyMuPDF (fitz)       |
|Datenbank       |Supabase (PostgreSQL)|
|Hosting         |Render               |
|Tests           |pytest, pytest-flask |
|CI/CD           |GitHub Actions       |

-----

## 📋 Features

- **3 Qualitätsstufen** — Niedrig (50%), Mittel (30%), Gut (25%)
- **Keine Datenspeicherung** — Verarbeitung im RAM, kein Upload auf Server
- **Feedback-System** — Like/Dislike mit IP-basierter Duplikaterkennung (Supabase)
- **Wakeup-Endpunkt** — `/wakeup` für Render Free Tier
- **Automatische Tests** — 11 pytest-Tests mit GitHub Actions CI

-----

## 🗂️ Projektstruktur

```
pdf-compressor-web/
├── app.py                    # Flask-Anwendung
├── templates/
│   └── index.html            # Frontend
├── static/
│   └── bg.JPG                # Hintergrundbild
├── test_app.py               # pytest-Tests
├── requirements.txt          # Abhängigkeiten
└── .github/
    └── workflows/
        └── python-tests.yml  # CI/CD Pipeline
```

-----

## 🧪 Tests

```bash
pip install pytest pytest-flask
pytest test_app.py -v
```

**Testabdeckung:**

- Route `/` → 200
- Route `/wakeup` → OK
- Komprimierung ohne Datei → 400
- Alle 3 Qualitätsstufen → gültige PDF
- Gut (25%) ergibt kleinere Datei als Niedrig (50%)
- Feedback GET/POST → JSON

-----

## 🔧 Lokale Entwicklung

```bash
git clone https://github.com/fin325/pdf-compressor-web.git
cd pdf-compressor-web
pip install -r requirements.txt
export DATABASE_URL=postgresql://...
python app.py
```

-----

## 📡 API Endpunkte

|Methode |Endpunkt   |Beschreibung    |
|--------|-----------|----------------|
|GET     |`/`        |Hauptseite      |
|POST    |`/compress`|PDF komprimieren|
|GET     |`/wakeup`  |Server aufwecken|
|GET/POST|`/feedback`|Bewertungen     |

-----

## 👨‍💻 Autor

**Artem Finevych** — Hattingen, NRW

🔗 [digital-mobil-deutschland.vercel.app](https://digital-mobil-deutschland.vercel.app)
