from flask import Flask, request, jsonify, render_template_string
import time

app = Flask(__name__)

# Data received FROM the NodeMCU
node_data = {
    "temp": 0, "level": 0,
    "hStat": "OFF", "cStat": "OFF", "pStat": "OFF",
    "last_seen": 0,
    "current_t_min": 22, "current_t_max": 28, "current_l_min": 12
}

# Values the User WANTS to set (Target)
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
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f4f7f6; display: flex; justify-content: center; padding: 20px; }
            .card { background: white; width: 100%; max-width: 420px; padding: 30px; border-radius: 25px; box-shadow: 0 15px 35px rgba(0,0,0,0.1); text-align: center; }
            .status-bar { display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 10px; }
            .val-container { display: flex; justify-content: space-around; margin: 25px 0; }
            .circle { width: 110px; height: 110px; border-radius: 50%; border: 6px solid #f0f0f0; display: flex; flex-direction: column; justify-content: center; align-items: center; }
            .t-circ { border-color: #ff7675; color: #d63031; }
            .l-circ { border-color: #74b9ff; color: #0984e3; }
            .relay-row { display: flex; justify-content: center; gap: 10px; margin-bottom: 25px; }
            .r-box { padding: 8px 15px; border-radius: 8px; font-size: 12px; font-weight: bold; color: white; background: #dfe6e9; }
            .ON { background: #2ecc71 !important; box-shadow: 0 4px 10px rgba(46, 204, 113, 0.3); }
            .OFF { background: #fab1a0 !important; }
            .settings { background: #f9f9f9; padding: 20px; border-radius: 15px; text-align: left; }
            .set-row { margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center; }
            .set-row label { font-size: 13px; font-weight: bold; color: #636e72; }
            .conf-val { font-size: 10px; color: #b2bec3; display: block; }
            input { width: 60px; padding: 8px; border-radius: 6px; border: 1px solid #ddd; text-align: center; }
            .btn { width: 100%; padding: 14px; background: #0984e3; color: white; border: none; border-radius: 10px; cursor: pointer; font-weight: bold; transition: 0.3s; }
            .btn:disabled { background: #b2bec3; cursor: not-allowed; }
            #msg { font-size: 13px; margin-top: 12px; text-align: center; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="status-bar">
                <span>System: <b id="conn" style="color:#d63031">● Offline</b></span>
                <span id="last-upd">--:--</span>
            </div>
            <h2 style="margin:0; color:#2d3436;">Aqua-Net Pro</h2>
            
            <div class="val-container">
                <div class="circle t-circ"><span style="font-size:11px">TEMP</span><b id="t" style="font-size:24px">--</b></div>
                <div class="circle l-circ"><span style="font-size:11px">LEVEL</span><b id="l" style="font-size:24px">--</b></div>
            </div>

            <div class="relay-row">
                <div class="r-box" id="h-b">HEATER</div>
                <div class="r-box" id="c-b">COOLER</div>
                <div class="r-box" id="p-b">PUMP</div>
            </div>

            <div class="settings">
                <div class="set-row">
                    <div><label>Min Temp</label><span class="conf-val">Active: <span id="cur-tmin">--</span>°C</span></div>
                    <input type="number" id="in-tmin" value="22">
                </div>
                <div class="set-row">
                    <div><label>Max Temp</label><span class="conf-val">Active: <span id="cur-tmax">--</span>°C</span></div>
                    <input type="number" id="in-tmax" value="28">
                </div>
                <div class="set-row">
                    <div><label>Min Level</label><span class="conf-val">Active: <span id="cur-lmin">--</span>cm</span></div>
                    <input type="number" id="in-lmin" value="12">
                </div>
                <button id="save-btn" class="btn" onclick="save()">Save Settings</button>
                <div id="msg"></div>
            </div>
        </div>

        <script>
            async function refresh() {
                const res = await fetch('/get_full_state');
                const d = await res.json();

                document.getElementById('t').innerText = d.node.temp + "°C";
                document.getElementById('l').innerText = d.node.level + "cm";
                
                document.getElementById('cur-tmin').innerText = d.node.current_t_min;
                document.getElementById('cur-tmax').innerText = d.node.current_t_max;
                document.getElementById('cur-lmin').innerText = d.node.current_l_min;

                document.getElementById('h-b').className = "r-box " + d.node.hStat;
                document.getElementById('c-b').className = "r-box " + d.node.cStat;
                document.getElementById('p-box').className = "r-box " + d.node.pStat;

                // FIX: Account for Render latency (30s)
                const online = (Date.now()/1000) - d.node.last_seen < 30;
                const conn = document.getElementById('conn');
                conn.innerText = online ? "● Online" : "● Offline";
                conn.style.color = online ? "#2ecc71" : "#d63031";

                const btn = document.getElementById('save-btn');
                const changed = 
                    document.getElementById('in-tmin').value != d.target.t_min ||
                    document.getElementById('in-tmax').value != d.target.t_max ||
                    document.getElementById('in-lmin').value != d.target.l_min;
                
                if(!btn.dataset.syncing) btn.disabled = !changed;
            }

            async function save() {
                const btn = document.getElementById('save-btn');
                const msg = document.getElementById('msg');
                const payload = {
                    t_min: parseInt(document.getElementById('in-tmin').value),
                    t_max: parseInt(document.getElementById('in-tmax').value),
                    l_min: parseInt(document.getElementById('in-lmin').value)
                };

                btn.dataset.syncing = "true"; btn.disabled = true;
                msg.innerText = "⏳ Syncing with Device..."; msg.style.color = "#f39c12";

                await fetch('/update_targets', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });

                // Source of Truth Handshake Polling
                let confirmed = false;
                for(let i=0; i<40; i++) { 
                    await new Promise(r => setTimeout(r, 1000));
                    const check = await fetch('/get_full_state').then(r => r.json());
                    if(check.node.current_t_min == payload.t_min && 
                       check.node.current_t_max == payload.t_max && 
                       check.node.current_l_min == payload.l_min) {
                        confirmed = true; break;
                    }
                }

                btn.dataset.syncing = "";
                msg.innerText = confirmed ? "✔ Confirmed & Saved" : "✖ Sync Timeout";
                msg.style.color = confirmed ? "#2ecc71" : "#e74c3c";
                setTimeout(() => { msg.innerText = ""; }, 5000);
            }
            setInterval(refresh, 2000);
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
    node_data.update({
        "temp": data.get("t"), "level": data.get("l"),
        "hStat": data.get("h"), "cStat": data.get("c"), "pStat": data.get("p"),
        "current_t_min": data.get("t_min"), "current_t_max": data.get("t_max"), "current_l_min": data.get("l_min"),
        "last_seen": time.time()
    })
    return jsonify(target_thresholds)

if __name__ == '__main__':
    app.run()
