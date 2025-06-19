# RingCX gRPC Streaming Implementation Guide

This guide will walk you through setting up a gRPC streaming service for RingCX, allowing you to receive real-time audio streams from calls.

This guide uses `python 3.11`.

At the moment only G.711 is supported end to end. Even if Workflow can set the auido property (though disabled at moment), it will be ignored and `g711u/a`, `ptime=100ms` and `sampling=8000hz` is used by RingCX VRU.

> **⚠️ Extra Notes:** 
> 
> **Cloud Platform Considerations:** While the server can theoretically run on any cloud platform, some platforms have restrictions on which ports can be exposed. For example, Heroku doesn't allow developers to specify custom port numbers but we only support connecting to port `443` at the moment.
> 
> **Local Development with ngrok:** Running locally via ngrok presents challenges due to port restrictions as well. TCP tunnels use their own port numbers rather than the required port 443. ngrok HTTPS tunnels use port 443 but encounter SSL certificate complications that prevent proper functionality.


## 1. Create a Virtual Environment and Install Dependencies

```bash
# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# On Windows:
.venv/Scripts/activate
# On Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install grpcio==1.71.0 grpcio-tools==1.29.0 protobuf==5.29.0
```

> **Note:** If you encounter build errors with grpcio-tools on Windows, use pre-compiled wheels instead:
> ```bash
> pip install --use-pep517 grpcio-tools
> ```
> Alternatively, install Microsoft Visual C++ Build Tools from [visualstudio.microsoft.com](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

For more advanced functionality (will be mentioned later), install additional dependencies:

```bash
# For transcription functionality
pip install google-cloud-speech==2.26.1

# For file serving functionality
pip install flask==2.3.3 requests==2.31.0
```

Alternatively, create a `requirements.txt` file with:

```
grpcio==1.71.0
grpcio-tools==1.71.0
protobuf==5.29.0
google-cloud-speech==2.26.1
requests==2.31.0
flask==2.3.3
```

And install with:

```bash
pip install -r requirements.txt
```

## 2. Generate gRPC Code from Protocol Buffers

First, save the following protobuf definition to a file named `ringcx_streaming.proto`:

```protobuf
syntax = "proto3";

import "google/protobuf/empty.proto";

package ringcentral.ringcx.streaming.v1beta2;

enum Codec {
  CODEC_UNSPECIFIED = 0;
  OPUS = 1;
  PCMA = 2;
  PCMU = 3;
  L16 = 4;
  FLAC = 5;
}

enum ProductType {
  PRODUCT_TYPE_UNSPECIFIED = 0;
  QUEUE = 1;
  CAMPAIGN = 2;
  IVR = 3; // RFU
}

enum DialogType {
  DIALOG_TYPE_UNSPECIFIED = 0;
  INBOUND = 1;
  OUTBOUND = 2;
}

enum ParticipantType {
  PARTICIPANT_TYPE_UNSPECIFIED = 0;
  CONTACT = 1;
  AGENT = 2;
  BOT = 5; // yes, value is 5
}

message Account {
  string id = 1;
  string sub_account_id = 2;
  string rc_account_id = 3;
}

message Product {
  string id = 1;
  ProductType type = 2;
}

message Dialog {
  string id = 1;
  DialogType type = 2;
  optional string ani = 3;
  optional string dnis = 4;
  optional string language = 5; // https://www.rfc-editor.org/rfc/bcp/bcp47.txt
  map<string, string> attributes = 6;
}

message Participant {
  string id = 1;
  ParticipantType type = 2;
  optional string name = 3;
}

message AudioFormat {
  Codec codec = 1;
  uint32 rate = 2;  // must be 8000 for now
  uint32 ptime = 3; // size of audio chunks in msec
}

message AudioContent {
  bytes payload = 1;
  uint32 seq = 2;      // could be repeated
  uint32 duration = 3; // in msec
}

service Streaming {
  // For each Dialog, gRPC client makes single 'Stream' call toward server and all 'StreamEvent' messages are sent over the established stream
  // Server does not return any response/stream back
  rpc Stream(stream StreamEvent) returns (google.protobuf.Empty);
}

message StreamEvent {
  string session_id = 1;
  oneof event {
    DialogInitEvent dialog_init = 2;
    SegmentStartEvent segment_start = 3;
    SegmentMediaEvent segment_media = 4;
    SegmentInfoEvent segment_info = 5;
    SegmentStopEvent segment_stop = 6;
  }
}

message DialogInitEvent {
  Account account = 1;
  Dialog dialog = 2;
}

message SegmentStartEvent {
  string segment_id = 1;
  optional Product product = 2;
  Participant participant = 3;
  optional AudioFormat audio_format = 4;
}

message SegmentMediaEvent {
  string segment_id = 1;
  AudioContent audio_content = 2;
}

message SegmentInfoEvent {
  string segment_id = 1;
  string event = 2;
  optional string data = 3;
}

message SegmentStopEvent {
  string segment_id = 1;
}
```

Now generate the Python gRPC code:

```bash
python -m grpc_tools.protoc -I. --python_out=. --pyi_out=. --grpc_python_out=. ringcx_streaming.proto
```

This will create three files:
- `ringcx_streaming_pb2.py`: Contains message classes
- `ringcx_streaming_pb2_grpc.py`: Contains service classes
- `ringcx_streaming_pb2.pyi`: Type hints for the generated code

## 3. Set Up Simple Server with SSL

Create `simple_server.py`:

<details>
<summary>Click to expand simple_server.py</summary>

```python
import grpc
import concurrent.futures
import signal
import sys
import traceback
import os
import ringcx_streaming_pb2_grpc
from google.protobuf.empty_pb2 import Empty
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('simple-speech-server')

class StreamingService(ringcx_streaming_pb2_grpc.StreamingServicer):
    def Stream(self, request_iterator, context):
        logger.info("Server started, waiting for audio stream...")
        
        try:
            for stream_event in request_iterator:
                if stream_event.HasField('segment_media'):
                    payload_size = len(stream_event.segment_media.audio_content.payload)
                    logger.info(f"Received segment media with payload size: {payload_size} bytes")
                else:
                    logger.info(f"Received other stream event type")
            
            logger.info("Stream completed.")
            
        except Exception as e:
            logger.error(f"Error during stream processing: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Stream processing error: {str(e)}")
            
        return Empty()

def serve():
    server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
    ringcx_streaming_pb2_grpc.add_StreamingServicer_to_server(
        StreamingService(), server
    )
    
    port = int(os.environ.get("PORT", 443))
    host = '0.0.0.0'
    server_address = f'{host}:{port}'
    
    cert_file = os.environ.get('SSL_CERT_FILE')
    key_file = os.environ.get('SSL_KEY_FILE')
    
    if cert_file and key_file and os.path.exists(cert_file) and os.path.exists(key_file):
        with open(cert_file, 'rb') as f:
            cert_data = f.read()
        with open(key_file, 'rb') as f:
            key_data = f.read()
            
        server_credentials = grpc.ssl_server_credentials([(key_data, cert_data)])
        server.add_secure_port(server_address, server_credentials)
        logger.info(f"Server started with SSL at {server_address}")
    else:
        server.add_insecure_port(server_address)
        logger.info(f"Server started without SSL at {server_address} (insecure)")
    
    server.start()
    
    def graceful_shutdown(signum, frame):
        logger.info("Received signal to terminate. Shutting down server gracefully...")
        server.stop(grace=5)
        logger.info("Server stopped successfully")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down server gracefully...")
        server.stop(grace=5)
        logger.info("Server stopped successfully")
    except Exception as e:
        logger.error(f"Server error: {e}")
        traceback.print_exc()

if __name__ == '__main__':
    try:
        logger.info("Starting simple server")
        serve()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Exiting...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Critical error in main loop: {e}")
        traceback.print_exc()
        sys.exit(1)
```

</details>

### Generate Local SSL Certificates

For production, use a proper SSL certificate from a trusted certificate authority. For testing, generate self-signed certificates (fields can all be empty for a default registration):

```bash
# Generate private key
openssl genrsa -out server.key 2048

# Generate certificate signing request
openssl req -new -key server.key -out server.csr

# Generate self-signed certificate (valid for 365 days)
openssl x509 -req -days 365 -in server.csr -signkey server.key -out server.crt
```

#### For Online Instances (AWS EC2)

When generating certificates on EC2, you need to specify the Common Name (CN) that matches your server's public DNS or IP:

```bash
# Generate private key
openssl genrsa -out server.key 2048

# Generate CSR with specific info (especially Common Name)
openssl req -new -key server.key -out server.csr -subj "/C=US/ST=State/L=City/O=Organization/OU=Unit/CN=your-ec2-public-dns-or-ip"
# Example: "/CN=ec2-12-34-56-78.compute-1.amazonaws.com" or "/CN=12.34.56.78"

# Generate self-signed certificate
openssl x509 -req -days 365 -in server.csr -signkey server.key -out server.crt
```

Note: If using an IP address, some clients might still show security warnings since they expect domain names.

### Run the Server with SSL

```bash
# Set environment variables for SSL certificate paths
export SSL_CERT_FILE=/path/to/server.crt
export SSL_KEY_FILE=/path/to/server.key
export PORT=443

# Run the server
python simple_server.py
```

## 4. Configure RingCX Workflow

Now that our gRPC server is up and running, we want to configure RingCX:

1. Log in to your RingCX admin portal
2. In Routing, create a new voice queue. Assign number and agents to it.
3. Navigate to "Workflows" section and create a new workflow
4. Assign a number to it (the number is what you would call later in test)
5. Go to Workflow Studio, we want 2 lanes:
   - Start -> Route (route to the voice queue you just created)
   - On_Agent_Connected -> Start_streaming (URL: `grpc://your-server-domain:443`, only port `443` is supported at the moment)
6. Save the workflow

## 5. Test the Setup

1. Make a test call to the queue you configured
2. Monitor your server logs for incoming audio streams
3. You should see log messages indicating receipt of stream events and audio data:
   ```bash
   # Upon call connection, it will show logs like this
   2025-04-29 06:12:17,007 - simple-speech-server - INFO - Received segment media with payload size: 800 bytes
   ```

## 6. Advanced Server Implementations

### 6.1 File Server (Save and Playback Audio)

For a more advanced implementation that saves audio segments as WAV files and hosts them for playback:

Create `file_server.py`:

<details>
<summary>Click to expand file_server.py</summary>

```python
import os
import grpc
import logging
import threading
import wave
from pathlib import Path
from concurrent import futures
from google.protobuf.empty_pb2 import Empty
from flask import Flask, send_file, Response, render_template_string, jsonify
import time
import ringcx_streaming_pb2
import ringcx_streaming_pb2_grpc
import audioop
import queue

app = Flask(__name__)
OUTPUT_FOLDER = 'saved_audio'

# HTML template for the web page
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Audio Recordings</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
        }
        h1, h2, h3 {
            color: #333;
        }
        ul {
            list-style-type: none;
            padding: 0;
        }
        li {
            border: 1px solid #ddd;
            margin-bottom: 10px;
            padding: 10px;
            border-radius: 4px;
        }
        audio {
            width: 100%;
        }
        .timestamp {
            color: #666;
            font-size: 0.8em;
        }
        .session {
            margin-bottom: 30px;
            border: 1px solid #eee;
            padding: 15px;
            border-radius: 8px;
            background-color: #f9f9f9;
        }
    </style>
</head>
<body>
    <h1>Recorded Audio Files</h1>
    
    {% if sessions %}
        {% for session_id, files in sessions.items() %}
            <div class="session">
                <h2>Session: {{ session_id }}</h2>
                
                {% if files.wav_files %}
                    <h3>WAV Files (Playable)</h3>
                    <ul>
                    {% for file_path in files.wav_files %}
                        {% set file_name = file_path.split('/')[-1] %}
                        <li>
                            <div>{{ file_name }}</div>
                            <audio controls>
                                <source src="/files/{{ file_path }}" type="audio/wav">
                                Your browser does not support the audio element.
                            </audio>
                        </li>
                    {% endfor %}
                    </ul>
                {% endif %}
                
                {% if files.bin_files %}
                    <h3>Raw Binary Files</h3>
                    <ul>
                    {% for file_path in files.bin_files %}
                        {% set file_name = file_path.split('/')[-1] %}
                        <li>
                            <a href="/files/{{ file_path }}">{{ file_name }}</a>
                        </li>
                    {% endfor %}
                    </ul>
                {% endif %}
            </div>
        {% endfor %}
    {% else %}
        <p>No audio recordings found.</p>
    {% endif %}
</body>
</html>
"""

class StreamingService(ringcx_streaming_pb2_grpc.StreamingServicer):
    def __init__(self):
        self.segments = {}  # Dictionary to track all active segments

    def Stream(self, request_iterator, context):
        # Create output directory
        Path(OUTPUT_FOLDER).mkdir(exist_ok=True)
        
        for event in request_iterator:
            session_id = event.session_id
            
            if event.HasField('dialog_init'):
                dialog_id = event.dialog_init.dialog.id
                logger.info(f"{session_id}: DialogInit, dialog_id: {dialog_id}")
                create_session_dir(session_id)
                write_session_logs(session_id, f"DialogInit: {event}")
                
            elif event.HasField('segment_start'):
                segment_id = event.segment_start.segment_id
                logger.info(f"{session_id}: SegmentStart, segment_id: {segment_id}")
                
                # Create entry for this segment
                segment_key = f"{session_id}_{segment_id}"
                self.segments[segment_key] = {
                    'session_id': session_id,
                    'segment_id': segment_id,
                    'audio_format': {},
                    'audio_data': bytearray()
                }
                
                # Extract audio format from segment_start if available
                if event.segment_start.HasField('audio_format'):
                    fmt = event.segment_start.audio_format
                    codec_name = ringcx_streaming_pb2.Codec.Name(fmt.codec)
                    
                    # Store audio format for this specific segment
                    self.segments[segment_key]['audio_format'] = {
                        'encoding': codec_name,
                        'sample_rate': fmt.rate,
                        'channels': 1  # Default to mono
                    }
                    
                    # Set sample width based on codec
                    if codec_name in ['PCMA', 'PCMU']:  # A-law and μ-law are 8-bit
                        self.segments[segment_key]['audio_format']['sample_width'] = 1
                    elif codec_name in ['L16', 'LINEAR16']:  # 16-bit PCM
                        self.segments[segment_key]['audio_format']['sample_width'] = 2
                
            elif event.HasField('segment_media'):
                segment_id = event.segment_media.segment_id
                payload = event.segment_media.audio_content.payload
                seq = event.segment_media.audio_content.seq
                
                segment_key = f"{session_id}_{segment_id}"
                logger.debug(f"{session_id}: SegmentMedia, segment_id: {segment_id}, seq: {seq}")
                
                # Store audio data
                if segment_key in self.segments:
                    # Save audio content to file
                    write_audio_content(session_id, segment_id, payload)
                    # Append to in-memory buffer
                    self.segments[segment_key]['audio_data'].extend(payload)
                
            elif event.HasField('segment_stop'):
                segment_id = event.segment_stop.segment_id
                logger.info(f"{session_id}: SegmentStop, segment_id: {segment_id}")
                
                # Process completed segment
                segment_key = f"{session_id}_{segment_id}"
                if segment_key in self.segments:
                    # Convert audio to WAV for playback
                    audio_format = self.segments[segment_key]['audio_format']
                    convert_bin_to_wav(session_id, segment_id, audio_format)
                    
                    # Clean up
                    del self.segments[segment_key]
        
        # Clean up any remaining segments
        segments_to_remove = list(self.segments.keys())
        for segment_key in segments_to_remove:
            segment_data = self.segments[segment_key]
            session_id = segment_data['session_id']
            segment_id = segment_data['segment_id']
            
            # Convert to WAV
            audio_format = segment_data['audio_format']
            convert_bin_to_wav(session_id, segment_id, audio_format)
            
            # Clean up
            del self.segments[segment_key]
            
        return Empty()


def serve(server_ip, grpc_port, grpc_secure_port):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    ringcx_streaming_pb2_grpc.add_StreamingServicer_to_server(StreamingService(), server)
    
    # Insecure port
    server_address = f'{server_ip}:{grpc_port}'
    server.add_insecure_port(server_address)
    logger.info(f'gRPC server started at {server_address} (insecure)')
    
    # Secure port if SSL certificates are available
    cert_file = os.environ.get('SSL_CERT_FILE')
    key_file = os.environ.get('SSL_KEY_FILE')
    
    if cert_file and key_file and os.path.exists(cert_file) and os.path.exists(key_file):
        secure_address = f'{server_ip}:{grpc_secure_port}'
        with open(cert_file, 'rb') as f:
            cert_data = f.read()
        with open(key_file, 'rb') as f:
            key_data = f.read()
            
        server_credentials = grpc.ssl_server_credentials([(key_data, cert_data)])
        server.add_secure_port(secure_address, server_credentials)
        logger.info(f'gRPC server started with SSL at {secure_address}')
    
    server.start()
    return server

def configure_logger(log_level, log_filename):
    _logger = logging.getLogger(__name__)
    _logger.setLevel(log_level)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)

    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(log_level)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    _logger.addHandler(console_handler)
    _logger.addHandler(file_handler)
    return _logger


def create_session_dir(session_id):
    output_folder_path = Path(f"{OUTPUT_FOLDER}/{session_id}")
    output_folder_path.mkdir(parents=True, exist_ok=True)

def write_session_logs(session_id, msg):
    with open(f'{OUTPUT_FOLDER}/{session_id}/session.log', 'a') as file:
        file.write(f"{msg}\n")

def write_audio_content(session_id, segment_id, payload):
    with open(f'{OUTPUT_FOLDER}/{session_id}/{segment_id}.bin', 'ab') as file:
        file.write(payload)

def convert_bin_to_wav(session_id, segment_id, audio_format):
    """Convert binary audio file to WAV format"""
    bin_file = f'{OUTPUT_FOLDER}/{session_id}/{segment_id}.bin'
    wav_file = f'{OUTPUT_FOLDER}/{session_id}_{segment_id}.wav'
    
    # Check if binary file exists and has content
    if not os.path.exists(bin_file) or os.path.getsize(bin_file) == 0:
        logger.warning(f"Binary file {bin_file} is empty or doesn't exist")
        return
    
    # Ensure we have the minimum required audio format parameters
    if not audio_format or 'sample_rate' not in audio_format:
        logger.warning(f"Missing audio format information for {session_id}_{segment_id}")
        return
    
    # Set default values if not provided
    channels = audio_format.get('channels', 1)  # Default to mono
    sample_width = audio_format.get('sample_width', 1)  # Default to 8-bit
    sample_rate = audio_format.get('sample_rate', 8000)  # Default to 8kHz
    encoding = audio_format.get('encoding', 'PCMU')  # Default to PCM
    
    try:
        # Read binary data
        with open(bin_file, 'rb') as f:
            audio_data = f.read()
        
        # Convert based on codec type
        if encoding == 'PCMA':  # A-law
            # Convert A-law to PCM (2 bytes per sample)
            audio_data = audioop.alaw2lin(audio_data, 2)
            sample_width = 2  # A-law conversion results in 16-bit PCM
        
        elif encoding == 'PCMU':  # μ-law
            # Convert μ-law to PCM (2 bytes per sample)
            audio_data = audioop.ulaw2lin(audio_data, 2)
            sample_width = 2  # μ-law conversion results in 16-bit PCM
            
        elif encoding not in ['L16', 'LINEAR16']:
            logger.warning(f"Unsupported codec: {encoding}, using raw data")
        
        # Create WAV file
        with wave.open(wav_file, 'wb') as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data)
        
        logger.info(f"Converted {bin_file} to WAV format: {wav_file}")
    except Exception as e:
        logger.error(f"Error converting {bin_file} to WAV: {e}")


def get_all_files(directory):
    if not os.path.exists(directory):
        return []
        
    file_list = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            creation_time = os.path.getctime(file_path)
            file_list.append((file_path, creation_time))

    file_list.sort(reverse=True, key=lambda x: x[1])
    return [file[0] for file in file_list]


def run_flask(http_port):
    logger.info(f"Starting Flask server on port {http_port}")
    app.run(host="0.0.0.0", port=http_port, threaded=True)

@app.route('/health')
def healthcheck():
    return '', 200

@app.route('/')
def list_files():
    # Group files by session ID
    sessions = {}
    
    # Get all files
    all_files = get_all_files(OUTPUT_FOLDER)
    
    for file_path in all_files:
        # Skip session log files from the main listing
        if file_path.endswith('/session.log'):
            continue
            
        parts = file_path.split('/')
        file_name = parts[-1]
        
        if '_' in file_name:
            # For session_segment named files
            session_segment = file_name.split('.')[0]  # Remove extension
            if session_segment:
                parts = session_segment.split('_')
                if len(parts) >= 2:
                    session_id = parts[0]
                    if session_id not in sessions:
                        sessions[session_id] = {'wav_files': [], 'bin_files': []}
                    
                    if file_name.endswith('.wav'):
                        sessions[session_id]['wav_files'].append(file_path)
                    elif file_name.endswith('.bin'):
                        sessions[session_id]['bin_files'].append(file_path)
        elif len(parts) > 2:
            # For files organized in session directories
            session_id = parts[-2]
            if session_id not in sessions:
                sessions[session_id] = {'wav_files': [], 'bin_files': []}
                
            if file_name.endswith('.wav'):
                sessions[session_id]['wav_files'].append(file_path)
            elif file_name.endswith('.bin'):
                sessions[session_id]['bin_files'].append(file_path)
    
    # Sort sessions and files
    sorted_sessions = {}
    for session_id in sorted(sessions.keys(), reverse=True):
        sorted_sessions[session_id] = {
            'wav_files': sorted(sessions[session_id]['wav_files']),
            'bin_files': sorted(sessions[session_id]['bin_files'])
        }
    
    return render_template_string(HTML_TEMPLATE, sessions=sorted_sessions)

@app.route('/files/<path:filename>')
def download_file(filename):
    if filename.endswith('.log'):
        with open(filename, 'r') as f:
            file_content = f.read()
        return Response(file_content, content_type='text/plain')
    return send_file(filename)

@app.route('/api/files')
def api_list_files():
    """API endpoint to list all audio files"""
    wav_files = []
    for root, _, files in os.walk(OUTPUT_FOLDER):
        for file in files:
            if file.endswith('.wav'):
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, OUTPUT_FOLDER)
                wav_files.append(relative_path)
                
    return jsonify({"files": wav_files})

if __name__ == '__main__':
    # Configuration with hardcoded values
    log_level = 'INFO'
    log_filename = "server.log"
    server_ip = '0.0.0.0'
    grpc_port = 10080
    grpc_secure_port = 443
    http_port = 8080
    
    # Configure logger
    logger = configure_logger(log_level, log_filename)
    
    # Create output folders if they don't exist
    Path(OUTPUT_FOLDER).mkdir(exist_ok=True)
    
    # Start gRPC server
    grpc_server = serve(server_ip, grpc_port, grpc_secure_port)
    
    # Start Flask server in a separate thread
    flask_thread = threading.Thread(target=run_flask, args=(http_port,))
    flask_thread.daemon = True
    flask_thread.start()
    
    # Keep the main thread running
    try:
        while True:
            time.sleep(86400)  # Sleep for a day
    except KeyboardInterrupt:
        logger.info("Server shutdown initiated")
        grpc_server.stop(0)
```

</details>

```bash
# Install additional required packages (if you haven't done this above)
pip install flask

# Export SSL environment variables as before
export SSL_CERT_FILE=/path/to/server.crt
export SSL_KEY_FILE=/path/to/server.key
export PORT=443

# Run the file server
python file_server.py
```

The `file_server.py` script will:
- Save incoming audio streams as binary files
- Convert them to WAV format for playback
- Host a simple web server to browse and play recorded files

Access the web interface at: `http://your-server-address:8080/`

### 6.2 Transcription Server (Real-time Speech-to-Text)

Create `transcribe_server.py`:

<details>
<summary>Click to expand transcribe_server.py</summary>

```python
import grpc
import concurrent.futures
import signal
import sys
import traceback
import os
from google.cloud import speech
import ringcx_streaming_pb2_grpc
from google.protobuf.empty_pb2 import Empty
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('speech-server')

class StreamingService(ringcx_streaming_pb2_grpc.StreamingServicer):
    def Stream(self, request_iterator, context):
        logger.info("Server started, waiting for audio stream...")
        
        client = speech.SpeechClient()
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.MULAW,
            sample_rate_hertz=8000,
            language_code="en-US",
            enable_automatic_punctuation=True,
        )
        streaming_config = speech.StreamingRecognitionConfig(
            config=config,
            interim_results=True,
        )
        
        def audio_generator():
            for stream_event in request_iterator:
                if stream_event.HasField('segment_media'):
                    yield speech.StreamingRecognizeRequest(
                        audio_content=stream_event.segment_media.audio_content.payload
                    )
        
        try:            
            responses = client.streaming_recognize(
                config=streaming_config,
                requests=audio_generator()
            )
            
            for response in responses:
                if not response.results:
                    continue
                    
                result = response.results[0]
                if result.is_final:
                    transcript = result.alternatives[0].transcript
                    logger.info(f"Transcription: {transcript}")
            
            logger.info("Transcription completed.")
            
        except Exception as e:
            logger.error(f"Error during transcription: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Transcription error: {str(e)}")
            
        return Empty()

def serve():
    server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
    ringcx_streaming_pb2_grpc.add_StreamingServicer_to_server(
        StreamingService(), server
    )
    
    port = int(os.environ.get("PORT", 443)) # We only support 443 port at the moment
    host = '0.0.0.0'
    server_address = f'{host}:{port}'
    
    cert_file = os.environ.get('SSL_CERT_FILE')
    key_file = os.environ.get('SSL_KEY_FILE')
    
    if cert_file and key_file and os.path.exists(cert_file) and os.path.exists(key_file):
        with open(cert_file, 'rb') as f:
            cert_data = f.read()
        with open(key_file, 'rb') as f:
            key_data = f.read()
            
        server_credentials = grpc.ssl_server_credentials([(key_data, cert_data)])
        server.add_secure_port(server_address, server_credentials)
        logger.info(f"Server started with SSL at {server_address}")
    else:
        server.add_insecure_port(server_address)
        logger.info(f"Server started without SSL at {server_address} (insecure)")
    
    server.start()
    
    def graceful_shutdown(signum, frame):
        logger.info("Received signal to terminate. Shutting down server gracefully...")
        server.stop(grace=5)
        logger.info("Server stopped successfully")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down server gracefully...")
        server.stop(grace=5)
        logger.info("Server stopped successfully")
    except Exception as e:
        logger.error(f"Server error: {e}")
        traceback.print_exc()

if __name__ == '__main__':
    try:
        logger.info("Starting server")
        serve()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Exiting...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Critical error in main loop: {e}")
        traceback.print_exc()
        sys.exit(1) 
```

</details>

To implement real-time transcription using Google Speech-to-Text:

1. Set up Google Cloud account and create a project
2. Enable the Speech-to-Text API for your project
3. Create a service account and download credentials JSON file
4. Set the environment variable to point to your credentials:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your-credentials.json
export SSL_CERT_FILE=/path/to/server.crt
export SSL_KEY_FILE=/path/to/server.key
export PORT=443

# Run the transcription server
python transcribe_server.py
```

The transcription server will convert incoming audio to text in real-time and log the transcriptions. 

For design simplicity, it transcribes all content from both parties, which would have better text output if one party is audible and the other is muted.

## Troubleshooting

- **SSL Connection Issues**: Ensure your certificates are valid and properly configured
- **gRPC Connection Failures**: Check that your server is accessible from RingCX network and ports are properly opened
- **No Audio Data**: Verify that the workflow is correctly associated with the call queue
- **Transcription Issues**: Check your Google Cloud credentials and ensure the Speech-to-Text API is enabled

## Further Development

You can extend the provided server implementations to:
- Store transcriptions in a database
- Perform sentiment analysis on transcriptions
- Integrate with other services via webhooks
- Implement custom audio processing logic

For any questions or support, please contact your RingCX representative. 