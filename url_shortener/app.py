from flask import Flask, request, jsonify, redirect
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from models import db, User
from auth import auth_bp
import pymongo.errors
from db import urls
from cache import redis_client 
from kafka_producer import send_click_event
from utils import generate_short_code
from config import BASE_URL, SHORT_CODE_LENGTH
from datetime import datetime, timedelta
import pymongo
import logging

app=Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"]="sqlite:///users.db"
app.config["JWT_SECRET_KEY"]="super_secret_key"
db.init_app(app)
jet=JWTManager(app)
app.register_blueprint(auth_bp)

with app.app_context():
    db.create_all()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@app.route('/shorten', methods=['POST'])
@jwt_required()
def shorten_url():
    data=request.get_json()
    long_url=data.get("url")
    custom_code=data.get("custom_code")
    expire_in_days=data.get("expire_days", 30)
    if not long_url:
        return jsonify({"error": "URL is required"}), 400
    short_code=custom_code or generate_short_code(SHORT_CODE_LENGTH)
    if custom_code and urls.find_one({"_id":short_code}):
        return jsonify({"error": "Custom short code already taken"}), 409
    url_doc={
        "_id": short_code,
        "long_url": long_url,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow()+timedelta(days=expire_in_days),
        "clicks":0
    }
    try:
        urls.insert_one(url_doc)
        redis_client.setex(short_code, expire_in_days*86400, long_url)
    except pymongo.errors.DuplicateKeyError:
        return jsonify({"error": "Short code conflict"}), 409
    
    return jsonify({
        "short_url": f"{BASE_URL}/{short_code}",
        "expire_in_days": expire_in_days
    })

@app.route('/<short_code>')
def redirect_to_long(short_code):
    long_url=redis_client.get(short_code)
    if long_url:
        urls.update_one({"_id":short_code},{"$inc":{"clicks":1}})
        event={
            "short_code": short_code,
            "timestamp": datetime.utcnow().isoformat(),
            "ip": request.remote_addr,
            "user_agent": request.headers.get('User-Agent')
        }
        send_click_event(event)
        return redirect(long_url)
    url_doc=urls.find_one({"_id":short_code})
    if url_doc:
        redis_client.setex(short_code,86400,url_doc['long_url'])
        urls.update_one({"_id":short_code},{"$inc":{"clicks":1}})
        event={
            "short_code":short_code,
            "timestamp": datetime.utcnow().isoformat(),
            "ip":request.remote_addr,
            "user_agent":request.headers.get('User-Agent')
        }
        send_click_event(event)
        return redirect(url_doc['long_url'])
    return jsonify({"error":"URL not found"}), 404

@app.route('/stats/<short_code>', methods=['GET'])
@jwt_required()
def get_stats(short_code):
    user_name=get_jwt_identity()
    logging.info("User checking stats:",user_name)
    doc=urls.find_one({"_id": short_code})
    if not doc:
        return jsonify({"error": "Short code not found"}), 404
    return jsonify({
        "short_code": short_code,
        "long_url": doc["long_url"],
        "clicks": doc.get("clicks",0),
        "created_at": doc["created_at"].isoformat(),
        "expires_at": doc["expires_at"].isoformat()
    })

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5050)
