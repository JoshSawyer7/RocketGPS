from flask import Flask, render_template_string, jsonify
import socket
import threading
from collections import deque

app = Flask(__name__)

# Shared data storage
latest_coords = (0.0, 0.0)
history = deque(maxlen=50)
data_lock = threading.Lock()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Live GPS Tracker</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css"/>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: Arial, sans-serif;
            background-color: #2f2f2f;
            color: #ffffff;
            height: 100vh;
        }

        #map {
            height: 100vh; /* Make map fill the entire screen */
        }

        .info-panel {
            position: absolute;
            top: 20px;
            right: 20px;
            background: rgba(0, 0, 0, 0.6);
            color: white;
            padding: 20px;
            z-index: 1000;
            border-radius: 8px;
            box-shadow: 0 0 15px rgba(0,0,0,0.7);
        }

        h3 {
            font-size: 20px;
            margin-bottom: 10px;
        }

        #sat-info, #coord-info {
            font-size: 16px;
        }

        #coord-info {
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="info-panel">
        <h3>GPS Info</h3>
        <div id="sat-info">Satellites: 0</div>
        <div id="coord-info">Coordinates: 0, 0</div>
    </div>
    <div id="map"></div>

    <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
    <script>
        var map = L.map('map').setView([0, 0], 13);

        // Use ESRI World Imagery for satellite view
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: '&copy; <a href="https://www.esri.com/en-us/home">Esri</a>',
            maxZoom: 19,  // Allow more zoom-in
            minZoom: 3     // Allow zoom-out to a more distant level
        }).addTo(map);
        
        var marker = L.marker([0, 0]).addTo(map);
        var path = L.polyline([], {color: 'red'}).addTo(map);

        function updateDisplay(lat, lng, sats) {
            marker.setLatLng([lat, lng]);
            map.panTo([lat, lng]);
            path.addLatLng([lat, lng]).redraw();
            document.getElementById('sat-info').textContent = `Satellites: ${sats}`;
            document.getElementById('coord-info').textContent = 
                `Coordinates: ${lat.toFixed(6)}, ${lng.toFixed(6)}`;
        }

        function fetchData() {
            fetch('/get_coords')
                .then(response => response.json())
                .then(data => {
                    if(data.lat && data.lng) {
                        updateDisplay(data.lat, data.lng, data.sats);
                    }
                })
                .catch(console.error);
        }

        setInterval(fetchData, 2000);
        fetchData();
    </script>
</body>
</html>

"""

def parse_gps_data(data):
    """Parse your existing ESP8266 format: 'Lat: x, Lng: y, Sats: z'"""
    try:
        decoded = data.decode().strip()
        parts = [p.strip() for p in decoded.split(',')]
        
        lat = float(parts[0].split(': ')[1])
        lng = float(parts[1].split(': ')[1])
        sats = int(parts[2].split(': ')[1])
        
        return (lat, lng, sats)
    except Exception as e:
        print(f"Parse error: {e}")
        return None

def handle_client(conn):
    global latest_coords, history
    print("Connected to ESP8266")
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            parsed = parse_gps_data(data)
            if parsed:
                lat, lng, sats = parsed
                with data_lock:
                    latest_coords = (lat, lng)
                    history.append((lat, lng, sats))
                print(f"Received: {lat}, {lng}, Sats: {sats}")
    finally:
        conn.close()

def socket_server():
    """Socket server to handle incoming ESP8266 connections"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('0.0.0.0', 1234))
        s.listen()
        print("Socket server started, waiting for connections...")
        while True:
            conn, addr = s.accept()
            print(f"Connection from {addr}")
            client_thread = threading.Thread(target=handle_client, args=(conn,))
            client_thread.daemon = True
            client_thread.start()

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/get_coords')
def get_coords():
    with data_lock:
        if history:
            lat, lng, sats = history[-1]
            return jsonify({
                'lat': lat,
                'lng': lng,
                'sats': sats,
                'history': [{'lat': h[0], 'lng': h[1]} for h in history]
            })
        return jsonify({'lat': 0, 'lng': 0, 'sats': 0})

if __name__ == '__main__':
    # Start socket server in a separate thread
    socket_thread = threading.Thread(target=socket_server)
    socket_thread.daemon = True
    socket_thread.start()
    

    # Start Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)
