from flask import Flask, request, jsonify, render_template_string
import time

app = Flask(__name__)

# Data coming FROM the NodeMCU
node_data = {
    "temp": 0, "level": 0,
    "hStat": "OFF", "cStat": "OFF", "pStat": "OFF",
    "last_seen": 0,
    "current_t_min": 22, "current_t_max": 28, "current_l_min": 12 # Confirmed values
}

# Values the User WANTS (Target)
target_thresholds = {
    "t_min": 22, "t_max": 28, "l_min": 12
}

@app.route('/')
def dashboard():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Aqua-Net Cloud Pro</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: #f4f7f6; display: flex; justify-content: center; padding: 20px; }
            .card { background: white; width: 100%; max-width: 400px; padding: 25px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); text-align: center; }
            .val-group { display: flex; justify-content: space-around; margin: 20px 0; }
            .sensor-circle { width: 100px; height: 100px; border-radius: 50%; border: 5px solid #eee; display: flex; flex-direction: column; justify-content: center; align-items: center; }
            .temp-circle { border-color: #e74c3c; color: #e74c3c; }
            .level-circle { border-color: #3498db; color: #3498db; }
            .settings { background: #fafafa; padding: 15px; border-radius: 12px; text-align: left; margin-top: 20px; }
            input { width: 50px; padding: 5px; border-radius: 4px; border: 1px solid #ddd; float: right; }
            .btn { width: 100%; padding: 12px; background: #3498db; color: white; border: none; border-radius: 8px; cursor: pointer; margin-top: 10px; font-weight: bold; }
            .btn:disabled { background: #bdc3c7; cursor: not-allowed; }
            #sync-msg { font-size: 12px; margin-top: 8px; font-weight: bold; min-height: 15px; }
            .confirmed-label { font-size: 10px; color: #7f8c8d; display: block; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2 style="margin-bottom:5px;">Aqua-Net Live</h2>
            <span id="conn" style="font-size:12px; color:#e74c3c;">● Offline</span>
            
            <div class="val-group">
                <div class="sensor-circle temp-circle"><span style="font-size:10px">TEMP</span><b id="t" style="font-size:20px">0</b></div>
                <div class="sensor-circle level-circle"><span style="font-size:10px">LEVEL</span><b id="l" style="font-size:20px">0</b></div>
            </div>

            <div class="settings">
                <div style="font-size:13px; font-weight:bold; margin-bottom:10px; color:#2c3e50;">Set Device Thresholds</div>
                
                <p>Min Temp <span class="confirmed-label">Active: <span id="cur-tmin">--</span>°C</span> 
                <input type="number" id="in-tmin" value="22"></p>
                
                <p>Max Temp <span class="confirmed-label">Active: <span id="cur-tmax">--</span>°C</span> 
                <input type="number" id="in-tmax" value="28"></p>
                
                <p>Min Level <span class="confirmed-label">Active: <span id="cur-lmin">--</span>cm</span> 
                <input type="number" id="in-lmin" value="12"></p>
                
                <button id="save-btn" class="btn" onclick="saveSettings()">Save Settings</button>
                <div id="sync-msg"></div>
            </div>
        </div>

        <script>
            let serverData = {};

            async function refresh() {
                const res = await fetch('/get_full_state');
                const data = await res.json();
                serverData = data;

                document.getElementById('t').innerText = data.node.temp + "°C";
                document.getElementById('l').innerText = data.node.level + "cm";
                
                document.getElementById('cur-tmin').innerText = data.node.current_t_min;
                document.getElementById('cur-tmax').innerText = data.node.current_t_max;
                document.getElementById('cur-lmin').innerText = data.node.current_l_min;

                const online = (Date.now()/1000) - data.node.last_seen < 15;
                const conn = document.getElementById('conn');
                conn.innerText = online ? "● Online" : "● Offline";
                conn.style.color = online ? "#2ecc71" : "#e74c3c";

                // Validation: Check if inputs match current server targets
                const btn = document.getElementById('save-btn');
                const changed = 
                    document.getElementById('in-tmin').value != data.target.t_min ||
                    document.getElementById('in-tmax').value != data.target.t_max ||
                    document.getElementById('in-lmin').value != data.target.l_min;
                
                if(!btn.dataset.syncing) {
                    btn.disabled = !changed;
                }
            }

            async function saveSettings() {
                const btn = document.getElementById('save-btn');
                const msg = document.getElementById('sync-msg');
                
                const payload = {
                    t_min: parseInt(document.getElementById('in-tmin').value),
                    t_max: parseInt(document.getElementById('in-tmax').value),
                    l_min: parseInt(document.getElementById('in-lmin').value)
                };

                btn.dataset.syncing = "true";
                btn.disabled = true;
                msg.innerText = "⏳ Sending to NodeMCU...";
                msg.style.color = "#f39c12";

                await fetch('/update_targets', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });

                // Polling for confirmation (Source of Truth check)
                let success = false;
                for(let i=0; i<30; i++) { // Wait up to 30 seconds
                    await new Promise(r => setTimeout(r, 1000));
                    const check = await fetch('/get_full_state').then(r => r.json());
                    if(check.node.current_t_min == payload.t_min && 
                       check.node.current_t_max == payload.t_max && 
                       check.node.current_l_min == payload.l_min) {
                        success = true;
                        break;
                    }
                }

                btn.dataset.syncing = "";
                msg.innerText = success ? "✔ Settings Updated Locally" : "✖ Sync Failed (Timeout)";
                msg.style.color = success ? "#2ecc71" : "#e74c3c";
                setTimeout(() => { msg.innerText = ""; }, 4000);
            }

            setInterval(refresh, 1500);
        </script>
    </body>
    </html>
    """)

@app.route('/get_full_state')
def get_full_state():
    return jsonify({"node": node_data, "target": target_thresholds})

@app.route('/update_targets', methods=['POST'])
def update_targets():
    global target_thresholds
    target_thresholds.update(request.json)
    return "OK", 200

@app.route('/sync', methods=['POST'])
def sync():
    data = request.json
    # NodeMCU sends its CURRENT thresholds so we can confirm them
    node_data.update({
        "temp": data.get("t"), "level": data.get("l"),
        "hStat": data.get("h"), "cStat": data.get("c"), "pStat": data.get("p"),
        "current_t_min": data.get("t_min"), 
        "current_t_max": data.get("t_max"), 
        "current_l_min": data.get("l_min"),
        "last_seen": time.time()
    })
    return jsonify(target_thresholds)

if __name__ == '__main__':
    app.run()
