"""HTTP trigger -- Flask endpoint for browser/network ring triggers."""
import json
import logging

logger = logging.getLogger(__name__)


def create_app(controller):
    """Create Flask app with ring endpoints. Accepts controller via DI."""
    from flask import Flask, jsonify

    app = Flask("hushbell")

    @app.post("/ring")
    def ring_endpoint():
        result = controller.ring()
        return jsonify(result)

    @app.get("/status")
    def status_endpoint():
        return jsonify(controller.stats())

    @app.get("/")
    def index():
        return "<h1>HushBell POC</h1><button onclick=\"fetch('/ring',{method:'POST'}).then(r=>r.json()).then(alert)\">Ring</button>"

    return app


def start_server(controller, port: int = 8080) -> None:
    """Start HTTP trigger server."""
    app = create_app(controller)
    logger.info("HTTP trigger starting on port %d", port)
    app.run(host="127.0.0.1", port=port)
