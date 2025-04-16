"""
Servidor Cloud do SISD.

Responsabilidades:
- Receber e armazenar réplicas de logs/snapshots enviados por sensores e cliente.
- Disponibilizar os logs via API REST (GET).
- Concorrência garantida via filelock.
"""

from flask import Flask, request, jsonify
import json
import os
from filelock import FileLock

app = Flask(__name__)
DB_FILE = os.path.join(os.path.dirname(__file__), "cloud_db.json")
LOCK_FILE = DB_FILE + ".lock"

# Garante que o arquivo existe
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump([], f)

@app.route("/replica", methods=["POST"])
def replica():
    """
    Endpoint para receber réplicas de logs/snapshots.
    """
    data = request.json
    try:
        with FileLock(LOCK_FILE):
            with open(DB_FILE, "r+") as f:
                try:
                    logs = json.load(f)
                except Exception as e:
                    return jsonify({"status": "error", "error": f"Erro ao ler o banco de dados: {e}"}), 500
                logs.append(data)
                f.seek(0)
                json.dump(logs, f, indent=4)
                f.truncate()
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500
    return jsonify({"status": "ok"})

@app.route("/replica", methods=["GET"])
def get_replica():
    """
    Endpoint para consultar todos os logs/snapshots armazenados.
    """
    with open(DB_FILE) as f:
        logs = json.load(f)
    return jsonify(logs)

if __name__ == "__main__":
    # Ponto de entrada do servidor cloud
    app.run(host="0.0.0.0", port=6000)