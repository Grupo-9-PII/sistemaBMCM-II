from app import create_app
import os

app = create_app()

if __name__ == "__main__":
    # Debug apenas se solicitado explicitamente com FLASK_DEBUG=1 (nunca por padrão em produção).
    app.run(
        host="0.0.0.0",
        port=8080,
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
