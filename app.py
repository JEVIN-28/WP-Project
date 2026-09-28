import os
import io
import json
import qrcode
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Initialize the Groq client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# In-memory mock database for the MVP
passport_db = {
    "WP-EAR-001": {
        "name": "Wireless Earphones",
        "category": "E-Waste",
        "materials": ["Plastic casing (40%)", "Lithium battery (30%)", "Copper/Wiring (30%)"],
        "instructions": "Remove lithium battery; do not place in household bin.",
        "collectionPoint": "GreenSpark E-Waste Center"
    },
    "WP-JEV-002":{
        "name":"PET Plastic Bottles ",
        "category":"Recyclable Waste",
        "materials":[" 100% Polyethelene Terephthalate"],
        "reusability":"2-3 times",
        "instructions":"Separate the label from the bottle before disposing",
        "collectionPoint":"Local plastic collector station",
    },
    "WP-KEY-003":{
        "name":"KEYBOARD ",
        "category":"E-Waste",
        "materials":["Plastic/polymers(40-55%)","Metal/Alloys(25-50%)","Glass-Reinforced Organics(6-11%)"],
        "instructions":"Remove Batteries; Dispose the batteries at a nearby e-waste center",
        "collectionPoint":"GreenSpark E-Waste Center",
    }
}

# 1. Generate QR Code for a Product
@app.route('/api/qr/<product_id>', methods=['GET'])
def generate_qr(product_id):
    try:
        qr = qrcode.make(product_id,box_size=10,border=4)
        img_io = io.BytesIO()
        qr.save(img_io, 'PNG')
        img_io.seek(0)

        response = send_file(img_io, mimetype='image/png')
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    except Exception as e:
        print(f"CRITICAL QR ERROR: {e}")
        return jsonify({"error": str(e)}), 500
   

# 2. Fetch Waste Passport Data
@app.route('/api/passport/<product_id>', methods=['GET'])
def get_passport(product_id):
    item = passport_db.get(product_id)
    if not item:
        return jsonify({"error": "Passport not found"}), 404
    return jsonify(item)

# 3. AI Assistant Route
@app.route('/api/ai/classify', methods=['POST'])
def classify_waste():
    data = request.json
    user_query = data.get("userQuery", "")

    try:
        completion = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {
                    "role": "system",
                    "content": """You are the Waste Passport AI. Return ONLY valid JSON:
                    {
                        "detected_item": "string",
                        "waste_category": "E-Waste | Plastic | Organic | General",
                        "materials": ["string"],
                        "separation_instructions": "string",
                        "action": "string"
                    }"""
                },
                {"role": "user", "content": user_query}
            ],
            response_format={"type": "json_object"}
        )
        
        parsed_response = json.loads(completion.choices[0].message.content)
        return jsonify(parsed_response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 4. Add New Product Data (Manufacturer Portal)
@app.route('/api/passport/add', methods=['POST'])
def add_passport():
    if request.method == 'OPTIONS':
        return jsonify({}),200
    data = request.json
    product_id = data.get('id')
    
    # Saves the new product into your Python dictionary
    passport_db[product_id] = {
        "name": data.get('name', 'Unknown Product'),
        "category": data.get('category', 'General Waste'),
        "materials": [m.strip() for m in data.get('materials', '').split(',')],
        "instructions": data.get('instructions', 'Dispose of responsibly.'),
        "collectionPoint": data.get('collectionPoint', 'Local Facility')
    }
    
    return jsonify({"status": "success", "message": f"Product {product_id} added!"})

if __name__=='__main__':
    app.run(port=5000, debug=True)