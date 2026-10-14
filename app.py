import glob
import os
import shutil
import subprocess
import threading
import time

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

try:
    import serial
except ImportError:
    serial = None

app = FastAPI(title="Raspberry Pi Remote")
_serial_lock = threading.Lock()
_connection = None
_port = None


def get_temperature():
    try:
        with open('/sys/class/thermal/thermal_zone0/temp') as f:
            return f'{int(f.read().strip()) / 1000:.1f} °C'
    except (OSError, ValueError):
        return 'Unavailable'


def get_uptime():
    try:
        with open('/proc/uptime') as f:
            seconds = int(float(f.read().split()[0]))
        return f'{seconds // 86400}d {(seconds % 86400) // 3600}h {(seconds % 3600) // 60}m'
    except (OSError, ValueError):
        return 'Unavailable'


def get_memory():
    try:
        result = subprocess.run(['free', '-m'], capture_output=True, text=True, check=True, timeout=3)
        line = result.stdout.splitlines()[1].split()
        return f'{int(line[2])} MB / {int(line[1])} MB'
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return 'Unavailable'


def get_cpu_usage():
    try:
        # 1-minute load average, normalized by CPU count; not instantaneous CPU utilization.
        return f'{os.getloadavg()[0] / (os.cpu_count() or 1) * 100:.1f}%'
    except OSError:
        return 'Unavailable'


def get_ip():
    try:
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True, check=True, timeout=3)
        return result.stdout.split()[0] if result.stdout.split() else 'Unavailable'
    except (OSError, IndexError, subprocess.SubprocessError):
        return 'Unavailable'


def get_disk():
    try:
        disk = shutil.disk_usage('/')
        return f'{disk.used // (1024 ** 3)} GB / {disk.total // (1024 ** 3)} GB'
    except OSError:
        return 'Unavailable'


def available_ports():
    return sorted(glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*'))


def close_connection():
    global _connection, _port
    if _connection is not None:
        try:
            _connection.close()
        except Exception:
            pass
    _connection = None
    _port = None


def send_command(command):
    """Serial access is serialized so requests cannot interleave replies."""
    global _connection, _port
    if serial is None:
        raise RuntimeError('pyserial is not installed in the dashboard environment')
    with _serial_lock:
        ports = available_ports()
        if not ports:
            close_connection()
            raise RuntimeError('No Arduino serial port detected')
        # Prefer the port that is already connected, if still present.
        port = _port if _port in ports else ports[0]
        try:
            if _connection is None or not _connection.is_open or _port != port:
                close_connection()
                _connection = serial.Serial(port, 115200, timeout=1, write_timeout=2)
                _port = port
                time.sleep(2)  # Uno resets when a serial connection is opened.
            _connection.reset_input_buffer()
            _connection.write((command + '\n').encode('ascii'))
            _connection.flush()
            reply = _connection.readline().decode('utf-8', errors='replace').strip()
            if not reply:
                raise RuntimeError('Arduino did not respond')
            if not reply.startswith('OK '):
                raise RuntimeError(f'Arduino replied: {reply}')
            return {'port': port, 'reply': reply}
        except Exception as exc:
            close_connection()
            raise RuntimeError(str(exc)) from exc


@app.get('/api/status')
def status():
    ports = available_ports()
    return {
        'temperature': get_temperature(),
        'cpu': get_cpu_usage(),
        'memory': get_memory(),
        'disk': get_disk(),
        'uptime': get_uptime(),
        'ip': get_ip(),
        'arduino_connected': bool(ports),
        'arduino_port': ports[0] if ports else 'Not detected',
    }


@app.post('/api/arduino/{action}')
def arduino_control(action: str):
    commands = {'on': 'LED ON', 'off': 'LED OFF', 'blink': 'LED BLINK', 'status': 'STATUS'}
    if action not in commands:
        raise HTTPException(status_code=400, detail='Unknown action')
    try:
        return send_command(commands[action])
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get('/', response_class=HTMLResponse)
def dashboard():
    return HTMLResponse(content=HTML)


HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Raspberry Pi Remote</title>
<style>
:root {color-scheme:dark;font-family:Arial,sans-serif}
body {background:#111;color:#fff;margin:0;padding:20px}
.container {max-width:700px;margin:auto}
h1 {margin-bottom:5px}
.online,.connected {color:#4caf50;font-weight:bold}
.disconnected {color:#f44336;font-weight:bold}
.card {background:#222;border-radius:12px;padding:20px;margin-top:20px}
.row {display:flex;justify-content:space-between;gap:15px;padding:12px 0;border-bottom:1px solid #444}
.row:last-child {border-bottom:none}
.value {font-weight:bold;text-align:right;overflow-wrap:anywhere}
.refresh {color:#aaa;font-size:13px;margin-top:15px}
.controls {display:flex;flex-wrap:wrap;gap:10px;margin-top:18px}
button {background:#345d91;color:#fff;border:0;border-radius:9px;padding:13px 18px;font-size:15px;cursor:pointer;flex:1;min-width:105px}
button:disabled {opacity:.45;cursor:not-allowed}
button.on {background:#276b41}button.off {background:#923c3c}
#command-result {min-height:20px;color:#ddd;overflow-wrap:anywhere}
</style>
</head>
<body><div class="container">
<h1>Raspberry Pi Remote</h1>
<div class="online">● ONLINE</div>
<div class="card"><h2>System Status</h2>
<div class="row"><span>CPU Temperature</span><span class="value" id="temperature">Loading...</span></div>
<div class="row"><span>CPU Load (1 min)</span><span class="value" id="cpu">Loading...</span></div>
<div class="row"><span>Memory</span><span class="value" id="memory">Loading...</span></div>
<div class="row"><span>Disk</span><span class="value" id="disk">Loading...</span></div>
<div class="row"><span>Uptime</span><span class="value" id="uptime">Loading...</span></div>
<div class="row"><span>IP Address</span><span class="value" id="ip">Loading...</span></div>
<div class="refresh">System readings update every 3 seconds. CPU load is not instantaneous utilization.</div>
</div>
<div class="card"><h2>Arduino Uno</h2>
<div class="row"><span>Status</span><span id="arduino-status" class="disconnected">Checking...</span></div>
<div class="row"><span>Port</span><span class="value" id="arduino-port">Checking...</span></div>
<div class="controls">
<button class="on" data-action="on" disabled>LED ON</button>
<button class="off" data-action="off" disabled>LED OFF</button>
<button data-action="blink" disabled>LED BLINK</button>
<button data-action="status" disabled>CHECK STATUS</button>
</div>
<p id="command-result" role="status" aria-live="polite"></p>
</div></div>
<script>
let busy=false;
const buttons=[...document.querySelectorAll('[data-action]')];
function setButtons(connected){buttons.forEach(b=>b.disabled=busy||!connected)}
async function updateStatus(){
 try{
  const response=await fetch('/api/status',{cache:'no-store'});
  if(!response.ok)throw new Error('Status request failed');
  const data=await response.json();
  for(const key of ['temperature','cpu','memory','disk','uptime','ip'])
   document.getElementById(key).textContent=data[key];
  const status=document.getElementById('arduino-status');
  status.textContent=data.arduino_connected?'● PORT DETECTED':'● DISCONNECTED';
  status.className=data.arduino_connected?'connected':'disconnected';
  document.getElementById('arduino-port').textContent=data.arduino_port;
  setButtons(data.arduino_connected);
 }catch(err){
  document.getElementById('arduino-status').textContent='● STATUS UNAVAILABLE';
  document.getElementById('arduino-status').className='disconnected';
  setButtons(false);
 }
}
async function control(action){
 busy=true;setButtons(false);
 const output=document.getElementById('command-result');
 output.textContent='Sending command...';
 try{
  const response=await fetch('/api/arduino/'+action,{method:'POST'});
  const data=await response.json();
  if(!response.ok)throw new Error(data.detail||'Command failed');
  output.textContent=data.reply;
 }catch(err){output.textContent='Error: '+err.message}
 finally{busy=false;await updateStatus()}
}
buttons.forEach(b=>b.addEventListener('click',()=>control(b.dataset.action)));
updateStatus();setInterval(updateStatus,3000);
</script></body></html>'''

if __name__ == "__main__":
     import uvicorn
     uvicorn.run(app, host="0.0.0.0", port=5000)
