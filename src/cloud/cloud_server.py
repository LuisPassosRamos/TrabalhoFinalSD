"""API de replicação de logs e snapshots do SISD."""

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from filelock import FileLock, Timeout
from flask import Flask, jsonify, request


def create_app(db_path=None):
    app = Flask(__name__)
    replica_path = Path(db_path or Path(__file__).with_name("cloud_db.json"))
    lock = FileLock(f"{replica_path}.lock", timeout=5)

    def read_replica():
        try:
            with replica_path.open(encoding="utf-8") as file:
                entries = json.load(file)
        except FileNotFoundError:
            return []
        if not isinstance(entries, list):
            raise ValueError("Formato inválido para a réplica")
        return entries

    def write_replica(entries):
        file = NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=replica_path.parent, delete=False
        )
        temporary_path = Path(file.name)
        try:
            with file:
                json.dump(entries, file, ensure_ascii=False, indent=2)
            os.replace(temporary_path, replica_path)
        finally:
            temporary_path.unlink(missing_ok=True)

    @app.post("/replica")
    def replica():
        entry = request.get_json(silent=True)
        if not isinstance(entry, dict):
            return jsonify(status="error", error="Envie um objeto JSON."), 400

        try:
            with lock:
                entries = read_replica()
                entries.append(entry)
                write_replica(entries)
        except Timeout:
            return jsonify(status="error", error="Réplica ocupada. Tente novamente."), 503
        except (OSError, ValueError):
            app.logger.exception("Falha ao gravar a réplica")
            return jsonify(status="error", error="Falha ao gravar a réplica."), 500
        return jsonify(status="ok")

    @app.get("/replica")
    def get_replica():
        try:
            with lock:
                return jsonify(read_replica())
        except Timeout:
            return jsonify(status="error", error="Réplica ocupada. Tente novamente."), 503
        except (OSError, ValueError):
            app.logger.exception("Falha ao ler a réplica")
            return jsonify(status="error", error="Falha ao ler a réplica."), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6000)
