from flask import Flask, request, jsonify, send_from_directory
from markupsafe import escape
import re
import os
import logging
from datetime import datetime
from math import radians, cos, sin, asin, sqrt

app = Flask(__name__, static_folder='public', static_url_path='/')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🇿🇲 Enhanced Zambian destinations with activities and accommodations
ZAMBIA_PLACES = {
    "victoria falls": {
        "name": "Victoria Falls",
        "desc": "One of the largest waterfalls in the world, locally known as Mosi-oa-Tunya.",
        "lat": -17.9243,
        "lng": 25.8572,
        "difficulty": "moderate",
        "best_season": "May-August",
        "activities": [
            {"name": "Devil's Pool Swim", "cost": 150, "difficulty": "hard"},
            {"name": "Bungee Jump", "cost": 120, "difficulty": "extreme"},
            {"name": "Sunset Cruise", "cost": 80, "difficulty": "easy"},
            {"name": "Gorge Swing", "cost": 110, "difficulty": "hard"}
        ],
        "accommodations": [
            {"name": "The Victoria Falls Hotel", "rating": 4.8, "price": 250},
            {"name": "Livingstone Safari Lodge", "rating": 4.5, "price": 180},
            {"name": "Royal Livingstone Hotel", "rating": 4.6, "price": 220}
        ]
    },
    "lusaka": {
        "name": "Lusaka",
        "desc": "The capital city of Zambia, vibrant and full of culture.",
        "lat": -15.3875,
        "lng": 28.3228,
        "difficulty": "easy",
        "best_season": "April-October",
        "activities": [
            {"name": "National Museum Visit", "cost": 15, "difficulty": "easy"},
            {"name": "Lusaka Shopping Mall", "cost": 0, "difficulty": "easy"},
            {"name": "Munda Wanga Wildlife Park", "cost": 20, "difficulty": "easy"}
        ],
        "accommodations": [
            {"name": "Taj Pamodzi Hotel", "rating": 4.4, "price": 180},
            {"name": "The Radisson Blu", "rating": 4.6, "price": 210},
            {"name": "Intercontinental Lusaka", "rating": 4.5, "price": 195}
        ]
    },
    "south luangwa": {
        "name": "South Luangwa National Park",
        "desc": "A premier safari destination known for walking safaris.",
        "lat": -13.0636,
        "lng": 31.8072,
        "difficulty": "moderate",
        "best_season": "June-October",
        "activities": [
            {"name": "Game Drive", "cost": 120, "difficulty": "moderate"},
            {"name": "Walking Safari", "cost": 110, "difficulty": "moderate"},
            {"name": "Night Safari", "cost": 140, "difficulty": "hard"},
            {"name": "Bird Watching", "cost": 80, "difficulty": "easy"}
        ],
        "accommodations": [
            {"name": "Nkwali Camp", "rating": 4.7, "price": 350},
            {"name": "Mfuwe Lodge", "rating": 4.6, "price": 320},
            {"name": "Crested Crane Lodge", "rating": 4.5, "price": 280}
        ]
    },
    "lower zambezi": {
        "name": "Lower Zambezi National Park",
        "desc": "A stunning park along the Zambezi River with rich wildlife.",
        "lat": -15.7667,
        "lng": 29.4167,
        "difficulty": "hard",
        "best_season": "May-October",
        "activities": [
            {"name": "Canoeing Safari", "cost": 180, "difficulty": "hard"},
            {"name": "Fishing", "cost": 150, "difficulty": "moderate"},
            {"name": "Wildlife Viewing", "cost": 140, "difficulty": "moderate"}
        ],
        "accommodations": [
            {"name": "Chirundu Safari Lodge", "rating": 4.5, "price": 400},
            {"name": "Sausage Tree Camp", "rating": 4.6, "price": 380}
        ]
    },
    "kafue": {
        "name": "Kafue National Park",
        "desc": "One of Africa's largest national parks, rich in biodiversity.",
        "lat": -14.0333,
        "lng": 25.8000,
        "difficulty": "hard",
        "best_season": "June-November",
        "activities": [
            {"name": "Game Drive", "cost": 110, "difficulty": "moderate"},
            {"name": "Bushwalk", "cost": 100, "difficulty": "hard"},
            {"name": "River Cruise", "cost": 90, "difficulty": "easy"}
        ],
        "accommodations": [
            {"name": "Mukambi Safari Lodge", "rating": 4.4, "price": 300},
            {"name": "Kafue River Lodge", "rating": 4.3, "price": 280}
        ]
    }
}

# Intent classification patterns
INTENT_PATTERNS = {
    'add_place': r'\b(visit|go|explore|see|head to|journey to|travel to|add)\b',
    'list_places': r'\b(list|show|display|what.*visited|where.*been|all places|summary)\b',
    'greeting': r'\b(hi|hello|hey|greet|welcome|start)\b',
    'budget': r'\b(cost|budget|price|expense|money)\b',
    'activities': r'\b(activities|things to do|what.*do|adventure|active)\b',
}

# In-memory user sessions
user_sessions = {}

def get_or_create_session(session_id: str):
    """Get or create a user session."""
    if session_id not in user_sessions:
        user_sessions[session_id] = {
            "story": "You arrive in Zambia, a land of vast rivers, wild safaris, and powerful waterfalls. Your journey is about to begin.",
            "places": [],
            "created_at": datetime.now().isoformat()
        }
    return user_sessions[session_id]


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates in km."""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in km
    return c * r


def calculate_journey_stats(places):
    """Calculate distance and other journey statistics."""
    if len(places) < 1:
        return {
            "total_distance_km": 0, 
            "total_cost_low": 0, 
            "total_cost_high": 0,
            "estimated_days": 0
        }
    
    total_distance = 0
    
    if len(places) >= 2:
        for i in range(len(places) - 1):
            dist = haversine_distance(
                places[i]['lat'], places[i]['lng'],
                places[i+1]['lat'], places[i+1]['lng']
            )
            total_distance += dist
    
    # Estimate costs
    activity_costs = []
    accommodation_costs = []
    
    for place in places:
        place_name = place['name'].lower()
        if place_name in ZAMBIA_PLACES:
            place_data = ZAMBIA_PLACES[place_name]
            if 'activities' in place_data and place_data['activities']:
                activity_costs.extend([a['cost'] for a in place_data['activities']])
            if 'accommodations' in place_data and place_data['accommodations']:
                accommodation_costs.extend([a['price'] for a in place_data['accommodations']])
    
    total_accommodation = sum(accommodation_costs) if accommodation_costs else 0
    min_activity = min(activity_costs) if activity_costs else 0
    max_activity = max(activity_costs) if activity_costs else 0
    
    return {
        "total_distance_km": round(total_distance, 2),
        "total_cost_low": total_accommodation + min_activity,
        "total_cost_high": total_accommodation + max_activity,
        "estimated_days": max(1, len(places) * 2)
    }


def classify_intent(message: str) -> str:
    """Classify user intent using pattern matching."""
    msg = message.lower()
    
    for intent, pattern in INTENT_PATTERNS.items():
        if re.search(pattern, msg, re.IGNORECASE):
            return intent
    
    return "unknown"


def match_zambia_place(message: str):
    """Match message to a Zambian place using word boundaries."""
    msg = message.lower()
    
    for key, place in ZAMBIA_PLACES.items():
        if re.search(rf'\b{re.escape(key)}\b', msg, re.IGNORECASE):
            return place
    
    return None


def validate_message(msg: str) -> tuple:
    """Validate user message. Returns (is_valid, error_message)."""
    if not msg or not msg.strip():
        return False, "Message cannot be empty."
    
    if len(msg) > 500:
        return False, "Message exceeds 500 character limit."
    
    return True, ""


@app.route("/")
def index():
    """Serve the frontend."""
    return send_from_directory('public', 'index.html')


@app.route("/api/respond", methods=["POST"])
def respond():
    """Main endpoint for processing user messages and updating journey state."""
    
    # Extract and validate input
    data = request.get_json(silent=True) or {}
    msg = data.get("message", "").strip()
    session_id = data.get("session_id", "default")
    
    # Validate message
    is_valid, error_msg = validate_message(msg)
    if not is_valid:
        return jsonify({"error": error_msg}), 400
    
    # Get or create session
    session = get_or_create_session(session_id)
    
    # Sanitize message for output
    safe_msg = escape(msg)
    
    try:
        # Classify intent
        intent = classify_intent(msg)
        
        # Update story based on intent
        if intent == "greeting":
            session["story"] = "A warm Zambian welcome greets you. Where shall we explore? Try mentioning places like Victoria Falls, South Luangwa, or Kafue!"
        
        elif intent == "list_places":
            if session["places"]:
                place_names = ", ".join(p["name"] for p in session["places"])
                stats = calculate_journey_stats(session["places"])
                session["story"] = (
                    f"You've visited: {place_names}. "
                    f"Total distance: {stats['total_distance_km']} km. "
                    f"Budget range: ${stats['total_cost_low']} - ${stats['total_cost_high']}."
                )
            else:
                session["story"] = "Your journey has just begun. No places visited yet. Where would you like to explore?"
        
        elif intent == "budget":
            if session["places"]:
                stats = calculate_journey_stats(session["places"])
                session["story"] = (
                    f"For your {stats['estimated_days']}-day journey ({stats['total_distance_km']} km), "
                    f"budget approximately ${stats['total_cost_low']} - ${stats['total_cost_high']} "
                    f"(includes accommodation and activities)."
                )
            else:
                session["story"] = "Add some destinations first to estimate your budget!"
        
        elif intent == "activities":
            if session["places"]:
                all_activities = []
                for place in session["places"]:
                    place_name = place['name'].lower()
                    if place_name in ZAMBIA_PLACES:
                        activities = ZAMBIA_PLACES[place_name].get('activities', [])
                        all_activities.extend([f"{a['name']} (${a['cost']})" for a in activities])
                
                if all_activities:
                    session["story"] = f"Activities at your destinations: {', '.join(all_activities[:5])}"
                else:
                    session["story"] = "No activities found for your current destinations."
            else:
                session["story"] = "Add some destinations first to see available activities!"
        
        elif intent == "add_place":
            place = match_zambia_place(msg)
            
            if place:
                if place["name"] not in [p["name"] for p in session["places"]]:
                    session["places"].append(place)
                    stats = calculate_journey_stats(session["places"])
                    session["story"] = (
                        f"You journey toward {place['name']}, a highlight of Zambia. "
                        f"Best visited in {place.get('best_season', 'any season')}. "
                        f"Journey so far: {stats['total_distance_km']} km."
                    )
                else:
                    session["story"] = f"You've already added {place['name']} to your journey. Pick another destination?"
            else:
                session["story"] = (
                    "Your thoughts drift across the world, but your journey draws you back to Zambia's "
                    "remarkable landscapes. Try mentioning Victoria Falls, Lusaka, South Luangwa, Lower Zambezi, or Kafue."
                )
        
        else:
            session["story"] = (
                f"You reflect on '{safe_msg}', as the Zambian horizon stretches before you."
            )
        
        # Calculate stats
        stats = calculate_journey_stats(session["places"])
        
        logger.info(f"Session {session_id}: intent={intent}, places={len(session['places'])}")
        
        return jsonify({
            "story": session["story"],
            "places": session["places"],
            "session_id": session_id,
            "stats": {
                "total_places": len(session["places"]),
                "total_distance_km": stats["total_distance_km"],
                "estimated_budget_low": stats["total_cost_low"],
                "estimated_budget_high": stats["total_cost_high"],
                "estimated_days": stats["estimated_days"]
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error. Please try again."}), 500


@app.route("/api/places", methods=["GET"])
def get_all_places():
    """Get all available Zambian places."""
    return jsonify({
        "places": [
            {
                "name": v["name"],
                "description": v["desc"],
                "difficulty": v.get("difficulty", "moderate"),
                "best_season": v.get("best_season", "year-round"),
                "activity_count": len(v.get("activities", [])),
                "accommodation_count": len(v.get("accommodations", []))
            }
            for v in ZAMBIA_PLACES.values()
        ]
    }), 200


@app.route("/api/place/<place_name>", methods=["GET"])
def get_place_details(place_name):
    """Get detailed information about a specific place."""
    place_key = place_name.lower()
    
    if place_key not in ZAMBIA_PLACES:
        return jsonify({"error": "Place not found"}), 404
    
    place = ZAMBIA_PLACES[place_key]
    
    return jsonify({
        "name": place["name"],
        "description": place["desc"],
        "coordinates": {"lat": place["lat"], "lng": place["lng"]},
        "difficulty": place.get("difficulty", "moderate"),
        "best_season": place.get("best_season", "year-round"),
        "activities": place.get("activities", []),
        "accommodations": place.get("accommodations", [])
    }), 200


@app.route("/api/reset", methods=["POST"])
def reset_session():
    """Reset a user's journey."""
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id", "default")
    
    if session_id in user_sessions:
        del user_sessions[session_id]
    
    return jsonify({"message": "Session reset."}), 200


@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "Message too large."}), 413


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found."}), 404


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Method not allowed."}), 405


if __name__ == "__main__":
    app.run(port=5000, debug=False)