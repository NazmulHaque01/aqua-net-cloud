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
    <title>Aqua-Net Pro | High-Vis</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            background: #f4f7f6;
            display: flex;
            justify-content: center;
            padding: 20px;
        }

        .card {
            background: white;
            width: 100%;
            max-width: 500px;
            padding: 40px;
            border-radius: 30px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
            text-align: center;
        }

        .status-bar {
            display: flex;
            justify-content: space-between;
            font-size: 18px;
            margin-bottom: 25px;
            border-bottom: 2px solid #eee;
            padding-bottom: 15px;
        }

        .circle-container {
            display: flex;
            justify-content: space-around;
            margin: 35px 0;
        }

        .circle {
            width: 150px;
            height: 150px;
            border-radius: 50%;
            border: 8px solid #eee;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            transition: 0.3s;
        }

        /* Value Font Sizes */
        #t,
        #l {
            font-size: 42px;
            font-weight: 800;
        }

        .label-text {
            font-size: 14px;
            font-weight: bold;
            letter-spacing: 1px;
        }

        .settings {
            background: #f9f9f9;
            padding: 25px;
            border-radius: 20px;
            text-align: left;
        }

        .set-row {
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .set-row label {
            font-size: 18px;
            font-weight: bold;
            color: #2d3436;
        }

        .conf-val {
            font-size: 13px;
            color: #636e72;
            display: block;
            margin-top: 5px;
        }

        /* Input styling */
        input {
            width: 80px;
            padding: 12px;
            font-size: 18px;
            font-weight: bold;
            border-radius: 10px;
            border: 2px solid #ddd;
            text-align: center;
            color: #2d3436;
        }

        /* Button styling */
        .btn {
            width: 100%;
            padding: 20px;
            font-size: 20px;
            background: #0984e3;
            color: white;
            border: none;
            border-radius: 15px;
            cursor: pointer;
            font-weight: bold;
            margin-top: 15px;
            transition: 0.3s;
        }

        .btn:disabled {
            background: #b2bec3;
            cursor: not-allowed;
            opacity: 0.7;
        }

        #msg {
            font-size: 16px;
            margin-top: 20px;
            text-align: center;
            font-weight: bold;
            min-height: 1.5em;
        }
    </style>
</head>

<body>
    <div class="card">
        <div class="status-bar">
            <span>System: <b id="conn" style="color:#d63031">● Offline</b></span>
            <span id="ts" style="color:#636e72">Last: --</span>
        </div>

        <h1 style="margin:0; font-size: 32px; color:#2d3436;">Aqua-Net Pro</h1>

        <div class="circle-container">
            <div class="circle" style="border-color:#ff7675"><span class="label-text">TEMP</span><b id="t">--</b></div>
            <div class="circle" style="border-color:#74b9ff"><span class="label-text">LEVEL</span><b id="l">--</b></div>
        </div>

        <div class="settings">
            <div class="set-row">
                <div><label>Min Temp</label><span class="conf-val">In Device: <span id="cur-tmin">--</span>°C</span>
                </div>
                <input type="number" id="in-tmin" value="22">
            </div>
            <div class="set-row">
                <div><label>Max Temp</label><span class="conf-val">In Device: <span id="cur-tmax">--</span>°C</span>
                </div>
                <input type="number" id="in-tmax" value="28">
            </div>
            <div class="set-row">
                <div><label>Min Level</label><span class="conf-val">In Device: <span id="cur-lmin">--</span>cm</span>
                </div>
                <input type="number" id="in-lmin" value="12">
            </div>

            <button id="save-btn" class="btn" onclick="save()" disabled>SAVE SETTINGS</button>
            <div id="msg"></div>
        </div>
    </div>

    <script>
        let deviceOnline = false;

        async function refresh() {
            try {
                const res = await fetch('/get_full_state');
                const d = await res.json();

                document.getElementById('t').innerText = d.node.temp + "°C";
                document.getElementById('l').innerText = d.node.level + "cm";
                document.getElementById('cur-tmin').innerText = d.node.current_t_min;
                document.getElementById('cur-tmax').innerText = d.node.current_t_max;
                document.getElementById('cur-lmin').innerText = d.node.current_l_min;

                const secondsAgo = Math.round(Date.now() / 1000 - d.node.last_seen);
                deviceOnline = secondsAgo < 10;

                const conn = document.getElementById('conn');
                conn.innerText = deviceOnline ? "● Online" : "● Offline";
                conn.style.color = deviceOnline ? "#2ecc71" : "#d63031";
                document.getElementById('ts').innerText = deviceOnline ? "Live" : secondsAgo + "s ago";

                const btn = document.getElementById('save-btn');
                const isChanged =
                    document.getElementById('in-tmin').value != d.target.t_min ||
                    document.getElementById('in-tmax').value != d.target.t_max ||
                    document.getElementById('in-lmin').value != d.target.l_min;

                if (!btn.dataset.syncing) btn.disabled = !isChanged || !deviceOnline;
            } catch (e) { }
        }

        async function save() {
            const btn = document.getElementById('save-btn');
            const msg = document.getElementById('msg');
            const tmin = parseInt(document.getElementById('in-tmin').value);
            const tmax = parseInt(document.getElementById('in-tmax').value);
            const lmin = parseInt(document.getElementById('in-lmin').value);

            btn.dataset.syncing = "true"; btn.disabled = true;
            msg.innerText = "⏳ Syncing with NodeMCU..."; msg.style.color = "#f39c12";

            await fetch('/update_targets', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ t_min: tmin, t_max: tmax, l_min: lmin })
            });

            let success = false;
            for (let i = 0; i < 30; i++) {
                await new Promise(r => setTimeout(r, 1000));
                const check = await fetch('/get_full_state').then(r => r.json());
                if (check.node.current_t_min == tmin && check.node.current_t_max == tmax && check.node.current_l_min == lmin) {
                    success = true; break;
                }
            }

            btn.dataset.syncing = "";
            msg.innerText = success ? "✔ CONFIRMED & SAVED" : "✖ SYNC TIMEOUT";
            msg.style.color = success ? "#2ecc71" : "#d63031";
            setTimeout(() => { msg.innerText = ""; refresh(); }, 4000);
        }
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
