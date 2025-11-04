from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import os
try:
    from flask_pocket import FlaskPocket
except Exception:
    FlaskPocket = None

app = Flask(__name__)

# Configuration
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:password@db:5432/postgres")
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# PocketBase / Flask-Pocket configuration
app.config["POCKETBASE_URL"] = os.environ.get("POCKETBASE_URL", "http://localhost:8090")
app.config["POCKETBASE_ADMIN_EMAIL"] = os.environ.get("POCKETBASE_ADMIN_EMAIL", "")
app.config["POCKETBASE_ADMIN_PASSWORD"] = os.environ.get("POCKETBASE_ADMIN_PASSWORD", "")

# Initialize Flask-Pocket if available
if FlaskPocket is not None:
    try:
        pocket = FlaskPocket(app)
    except Exception:
        pocket = None
else:
    pocket = None

# Model
class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)

    def to_dict(self):
        return {"id": self.id, "name": self.name}

# Routes
@app.route('/')
def index():
    info = {"status": "ok"}
    if pocket is not None:
        info['pocket'] = 'enabled'
    else:
        info['pocket'] = 'disabled'
    return jsonify(info)

@app.route('/items', methods=['GET'])
def list_items():
    items = Item.query.all()
    return jsonify([i.to_dict() for i in items])

@app.route('/items', methods=['POST'])
def create_item():
    data = request.get_json() or {}
    name = data.get('name')
    if not name:
        return jsonify({"error": "name is required"}), 400
    item = Item(name=name)
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


# --- PocketBase-backed endpoints (use Flask-Pocket) ---
@app.route('/pb/items', methods=['GET'])
def pb_list_items():
    if pocket is None:
        return jsonify({"error": "PocketBase not configured"}), 503
    try:
        data = pocket.collection("items").get_full_list()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/pb/items', methods=['POST'])
def pb_create_item():
    if pocket is None:
        return jsonify({"error": "PocketBase not configured"}), 503
    payload = request.get_json() or {}
    try:
        created = pocket.collection("items").create(payload)
        return jsonify(created), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/pb/items/<item_id>', methods=['GET'])
def pb_get_item(item_id):
    if pocket is None:
        return jsonify({"error": "PocketBase not configured"}), 503
    try:
        obj = pocket.collection("items").get_one(item_id)
        return jsonify(obj)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/pb/items/<item_id>', methods=['PUT'])
def pb_update_item(item_id):
    if pocket is None:
        return jsonify({"error": "PocketBase not configured"}), 503
    payload = request.get_json() or {}
    try:
        updated = pocket.collection("items").update(item_id, payload)
        return jsonify(updated)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/pb/items/<item_id>', methods=['DELETE'])
def pb_delete_item(item_id):
    if pocket is None:
        return jsonify({"error": "PocketBase not configured"}), 503
    try:
        pocket.collection("items").delete(item_id)
        return jsonify({"status": "deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # For local development only
    app.run(host='0.0.0.0', port=8000, debug=True)
