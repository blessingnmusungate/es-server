# File: Tutorial/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import base64
from datetime import datetime, timedelta
from collections import OrderedDict

# create an instance of the flask application
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Load rules from JSON file
def load_rules():
    with open('rules.json', 'r') as f:
        return json.load(f)['rules']

# Load facts from JSON file - preserve order
def load_facts():
    with open('facts.json', 'r') as f:
        return json.load(f, object_pairs_hook=OrderedDict)

# Convert camelCase to PascalCase for fact names
def camel_to_pascal(camel_str):
    """Convert camelCase to PascalCase"""
    if not camel_str:
        return camel_str
    return camel_str[0].upper() + camel_str[1:]

# Convert PascalCase to camelCase
def pascal_to_camel(pascal_str):
    """Convert PascalCase to camelCase"""
    if not pascal_str:
        return pascal_str
    return pascal_str[0].lower() + pascal_str[1:]

# Simple token generation (base64 encoded email + timestamp)
def generate_token(email):
    """Generate a simple token for authentication"""
    timestamp = datetime.now().isoformat()
    token_data = f"{email}:{timestamp}"
    return base64.b64encode(token_data.encode()).decode()

# Match facts against rules (first match wins)
def match_rule(facts, rules):
    """Match provided facts against rules in priority order"""
    # Convert camelCase facts to PascalCase for matching
    pascal_facts = {}
    for key, value in facts.items():
        if value is not None:  # Only include provided facts
            pascal_key = camel_to_pascal(key)
            pascal_facts[pascal_key] = value
    
    # Check each rule in order (priority order)
    for rule in rules:
        conditions = rule.get('conditions', {})
        # Check if all conditions in this rule match the provided facts
        matches = True
        for condition_key, condition_value in conditions.items():
            if condition_key not in pascal_facts:
                matches = False
                break
            if pascal_facts[condition_key] != condition_value:
                matches = False
                break
        
        if matches:
            return rule
    
    # No rule matched - return default
    return None

# Convert prediction to response format
def format_prediction(prediction, actions):
    """Convert rule prediction to API response format"""
    prediction_lower = prediction.lower()
    
    if prediction_lower == "dropout":
        will_dropout = True
        risk_level = "High"
        explanation = f"Based on the provided facts, the expert system predicts a high risk of dropout. {prediction}"
    elif prediction_lower == "graduate":
        will_dropout = False
        risk_level = "Low"
        explanation = f"Based on the provided facts, the expert system predicts the student will graduate successfully. {prediction}"
    elif prediction_lower == "staysenrolled":
        will_dropout = False
        risk_level = "Medium"
        explanation = f"Based on the provided facts, the expert system predicts the student will stay enrolled. {prediction}"
    else:
        # Default case
        will_dropout = False
        risk_level = "Medium"
        explanation = f"Based on the provided facts, the expert system prediction: {prediction}"
    
    return {
        "willDropout": will_dropout,
        "riskLevel": risk_level,
        "explanation": explanation,
        "remedies": actions if actions else []
    }

# Login endpoint
@app.route("/auth/login", strict_slashes=False, methods=["POST"])
def login():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Missing request body"}), 400
        
        email = data.get("email")
        password = data.get("password")
        
        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400
        
        # Hardcoded credentials
        if email == "user@gmail.com" and password == "Pwd4516":
            token = generate_token(email)
            return jsonify({
                "token": token,
                "userName": "User"
            }), 200
        else:
            return jsonify({"error": "Invalid credentials"}), 401
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Risk detector endpoint
@app.route("/expert-system/dropout-risk", strict_slashes=False, methods=["POST"])
def dropout_risk():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Missing request body"}), 400
        
        # Get provided facts (already in camelCase from frontend)
        # Accept any facts dynamically from the request
        provided_facts = {k: v for k, v in data.items() if v is not None}
        
        if len(provided_facts) < 3:
            return jsonify({"error": "At least 3 facts are required"}), 400
        
        # Load rules
        rules = load_rules()
        
        # Match facts against rules
        matched_rule = match_rule(provided_facts, rules)
        
        if matched_rule:
            prediction = matched_rule.get("prediction", "StayEnrolled")
            actions = matched_rule.get("actions", [])
            response = format_prediction(prediction, actions)
            return jsonify(response), 200
        else:
            # No rule matched - return default response
            return jsonify({
                "willDropout": False,
                "riskLevel": "Medium",
                "explanation": "Based on the provided facts, no specific rule matched. General monitoring recommended.",
                "remedies": ["Regular check-ins with academic advisor", "Monitor academic performance"]
            }), 200
    
    except FileNotFoundError:
        return jsonify({"error": "Rules file not found"}), 500
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid rules file format"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Facts endpoint - returns facts in camelCase for frontend
@app.route("/expert-system/facts", strict_slashes=False, methods=["GET"])
def get_facts():
    try:
        facts = load_facts()
        # Convert PascalCase keys to camelCase for frontend
        # Preserve original order from facts.json - iterate in the order they appear
        camel_facts = OrderedDict()
        for key, value in facts.items():
            camel_key = pascal_to_camel(key)
            camel_facts[camel_key] = value
        
        # Manually serialize to JSON to ensure order is preserved
        # json.dumps preserves OrderedDict order
        from flask import make_response
        response = make_response(json.dumps(camel_facts, ensure_ascii=False))
        response.headers['Content-Type'] = 'application/json'
        return response, 200
    except FileNotFoundError:
        return jsonify({"error": "Facts file not found"}), 500
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid facts file format"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Health check endpoint
@app.route("/", strict_slashes=False, methods=["GET"])
def index():
    return jsonify({"message": "Student Dropout Risk Detector API", "status": "running"}), 200

if __name__ == "__main__":
    app.run(debug=False, port=8000)
