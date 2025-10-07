from flask import Flask, request, jsonify
import subprocess

app = Flask(__name__)

@app.route("/check-updates", methods=["POST"])
def check_updates():
    data = request.get_json()
    check_type = data.get("checkType", "DSM")

    try:
        # Run your original script
        result = subprocess.run(
            ["python3", "FeelGood_Update_Checker.py", check_type],
            capture_output=True,
            text=True
        )
        output = result.stdout if result.stdout else "No output."
        return jsonify({"status": "success", "checkType": check_type, "output": output})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
