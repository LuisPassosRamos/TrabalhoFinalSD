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
    with open(DB_FILE) as f:
        logs = json.load(f)
    return jsonify(logs)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6000)