from flask import Flask, request, jsonify, render_template_string
import time

app = Flask(__name__)

node_data = {
    "temp": 0, "level": 0,
    "hStat": "OFF", "cStat": "OFF", "pStat": "OFF",
    "last_seen": 0,
    "current_t_min": 0, "current_t_max": 0, "current_l_min": 0 
}

target_thresholds = {
    "t_min": 22, "t_max": 28, "l_min": 12
}

@app.route('/')
def dashboard():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Aqua-Net Ultra-Fast</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: #f4f7f6; display: flex; justify-content: center; padding: 20px; }
            .card { background: white; width: 100%; max-width: 420px; padding: 30px; border-radius: 25px; box-shadow: 0 15px 35px rgba(0,0,0,0.1); text-align: center; }
            .status-bar { display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 10px; }
            .circle-container { display: flex; justify-content: space-around; margin: 25px 0; }
            .circle { width: 110px; height: 110px; border-radius: 50%; border: 6px solid #eee; display: flex; flex-direction: column; justify-content: center; align-items: center; }
            .settings { background: #f9f9f9; padding: 20px; border-radius: 15px; text-align: left; }
            input { width: 60px; padding: 8px; border-radius: 6px; border: 1px solid #ddd; float: right; font-weight: bold; }
            .btn { width: 100%; padding: 14px; background: #0984e3; color: white; border: none; border-radius: 10px; cursor: pointer; font-weight: bold; margin-top: 10px; }
            .btn:disabled { background: #b2bec3; cursor: not-allowed; }
            #msg { font-size: 13px; margin-top: 12px; text-align: center; font-weight: bold; min-height: 1.5em; }
            .conf-val { font-size: 10px; color: #b2bec3; display: block; margin-top: 2px; }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="status-bar">
                <span>System: <b id="conn" style="color:#d63031">● Offline</b></span>
                <span id="ts" style="color:#b2bec3">--</span>
            </div>
            <h2 style="margin:0; color:#2d3436;">Aqua-Net Pro</h2>
            
            <div class="circle-container">
                <div class="circle" style="border-color:#ff7675"><span style="font-size:11px">TEMP</span><b id="t" style="font-size:24px; color:#d63031">--</b></div>
                <div class="circle" style="border-color:#74b9ff"><span style="font-size:11px">LEVEL</span><b id="l" style="font-size:24px; color:#0984e3">--</b></div>
            </div>

            <div class="settings">
                <div style="margin-bottom:15px">
                    <label style="font-weight:bold; font-size:13px">Min Temp</label>
                    <input type="number" id="in-tmin" value="22">
                    <span class="conf-val">In Hardware: <span id="cur-tmin">--</span>°C</span>
                </div>
                <div style="margin-bottom:15px">
                    <label style="font-weight:bold; font-size:13px">Max Temp</label>
                    <input type="number" id="in-tmax" value="28">
                    <span class="conf-val">In Hardware: <span id="cur-tmax">--</span>°C</span>
                </div>
                <div style="margin-bottom:15px">
                    <label style="font-weight:bold; font-size:13px">Min Level</label>
                    <input type="number" id="in-lmin" value="12">
                    <span class="conf-val">In Hardware: <span id="cur-lmin">--</span>cm</span>
                </div>
                
                <button id="save-btn" class="btn" onclick="save()" disabled>Save Settings</button>
                <div id="msg"></div>
            </div>
        </div>

        <script>
            let isOnline = false;

            async function refresh() {
                try {
                    const res = await fetch('/get_full_state');
                    const d = await res.json();

                    document.getElementById('t').innerText = d.node.temp + "°C";
                    document.getElementById('l').innerText = d.node.level + "cm";
                    document.getElementById('cur-tmin').innerText = d.node.current_t_min;
                    document.getElementById('cur-tmax').innerText = d.node.current_t_max;
                    document.getElementById('cur-lmin').innerText = d.node.current_l_min;

                    // --- SPEED FIX: Detection Threshold reduced to 10 seconds ---
                    const secondsAgo = Math.round(Date.now()/1000 - d.node.last_seen);
                    isOnline = secondsAgo < 10;
                    
                    const conn = document.getElementById('conn');
                    conn.innerText = isOnline ? "● Online" : "● Offline";
                    conn.style.color = isOnline ? "#2ecc71" : "#d63031";
                    document.getElementById('ts').innerText = isOnline ? "Live" : secondsAgo + "s ago";

                    const btn = document.getElementById('save-btn');
                    const isChanged = 
                        document.getElementById('in-tmin').value != d.target.t_min ||
                        document.getElementById('in-tmax').value != d.target.t_max ||
                        document.getElementById('in-lmin').value != d.target.l_min;
                    
                    if(!btn.dataset.syncing) btn.disabled = !isChanged || !isOnline;
                } catch(e) {}
            }

            async function save() {
                const btn = document.getElementById('save-btn');
                const msg = document.getElementById('msg');
                const tmin = parseInt(document.getElementById('in-tmin').value);
                const tmax = parseInt(document.getElementById('in-tmax').value);
                const lmin = parseInt(document.getElementById('in-lmin').value);

                btn.dataset.syncing = "true"; btn.disabled = true;
                msg.innerText = "⏳ Syncing..."; msg.style.color = "#f39c12";

                await fetch('/update_targets', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({t_min: tmin, t_max: tmax, l_min: lmin})
                });

                let success = false;
                for(let i=0; i<30; i++) { 
                    await new Promise(r => setTimeout(r, 1000));
                    const check = await fetch('/get_full_state').then(r => r.json());
                    if(check.node.current_t_min == tmin && 
                       check.node.current_t_max == tmax && 
                       check.node.current_l_min == lmin) {
                        success = true; break;
                    }
                }

                btn.dataset.syncing = "";
                msg.innerText = success ? "✔ Saved to Hardware" : "✖ Timeout";
                msg.style.color = success ? "#2ecc71" : "#d63031";
                setTimeout(() => { msg.innerText = ""; }, 4000);
            }
            // --- SPEED FIX: Refresh every 1 second ---
            setInterval(refresh, 1000);
        </script>
    </body>
    </html>
    """, **target_thresholds)

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
