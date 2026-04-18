from flask import Flask, request, jsonify, render_template_string
import time
import math

app = Flask(__name__)

# Shared Data Storage
system_state = {
    "temp": 0, "level": 0,
    "hStat": "OFF", "cStat": "OFF", "pStat": "OFF",
    "last_seen": 0
}

# User-Defined Thresholds (Defaults)
thresholds = {
    "t_min": 22, "t_max": 28, "l_min": 12
}

@app.route('/')
def dashboard():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Aqua-Net Cloud</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: sans-serif; background: #f0f2f5; display: flex; justify-content: center; padding: 20px; }
            .card { background: white; width: 100%; max-width: 400px; padding: 25px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); text-align: center; }
            .val { font-size: 32px; font-weight: bold; margin: 10px 0; }
            .status { padding: 10px; border-radius: 8px; color: white; margin: 5px; display: inline-block; width: 80px; }
            .ON { background: #2ecc71; } .OFF { background: #e74c3c; }
            input { width: 60px; padding: 5px; border-radius: 5px; border: 1px solid #ccc; }
            .settings { margin-top: 20px; padding-top: 20px; border-top: 1px solid #eee; text-align: left; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>Aqua-Net Live</h2>
            <p id="net">Checking Connection...</p>
            <div style="color: #e74c3c;">Temp: <div class="val" id="t">0</div></div>
            <div style="color: #3498db;">Water Level: <div class="val" id="l">0</div></div>
            
            <div id="relays">
                <div class="status" id="h-box">HEAT</div>
                <div class="status" id="c-box">COOL</div>
                <div class="status" id="p-box">PUMP</div>
            </div>

            <div class="settings">
                <h4>Set Thresholds</h4>
                <p>Min Temp: <input type="number" id="in-tmin" value="{{ t_min }}"> °C</p>
                <p>Max Temp: <input type="number" id="in-tmax" value="{{ t_max }}"> °C</p>
                <p>Min Level: <input type="number" id="in-lmin" value="{{ l_min }}"> cm</p>
                <button onclick="saveSettings()" style="width:100%; padding:10px; background:#3498db; color:white; border:none; border-radius:5px;">Save Settings</button>
            </div>
        </div>

        <script>
            async function update() {
                const res = await fetch('/get_data');
                const data = await res.json();
                document.getElementById('t').innerText = data.temp + "°C";
                document.getElementById('l').innerText = data.level + "cm";
                
                document.getElementById('h-box').className = "status " + data.hStat;
                document.getElementById('c-box').className = "status " + data.cStat;
                document.getElementById('p-box').className = "status " + data.pStat;
                
                const online = (Date.now()/1000) - data.last_seen < 15;
                document.getElementById('net').innerText = online ? "✔ Online" : "✖ Offline";
                document.getElementById('net').style.color = online ? "#2ecc71" : "#e74c3c";
            }

            async function saveSettings() {
                const payload = {
                    t_min: parseInt(document.getElementById('in-tmin').value),
                    t_max: parseInt(document.getElementById('in-tmax').value),
                    l_min: parseInt(document.getElementById('in-lmin').value)
                };
                await fetch('/set_thresholds', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                alert("Settings Updated!");
            }
            setInterval(update, 2000);
        </script>
    </body>
    </html>
    """, **thresholds)

@app.route('/get_data')
def get_data():
    return jsonify(system_state)

@app.route('/set_thresholds', methods=['POST'])
def set_thresh():
    global thresholds
    thresholds.update(request.json)
    return "OK", 200

@app.route('/sync', methods=['POST'])
def sync():
    data = request.json
    system_state.update({
        "temp": data.get("t"), "level": data.get("l"),
        "hStat": data.get("h"), "cStat": data.get("c"), "pStat": data.get("p"),
        "last_seen": time.time()
    })
    return jsonify(thresholds)

if __name__ == '__main__':
    app.run()