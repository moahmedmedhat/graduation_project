# import config.settings
import time 
import paho.mqtt.client as mqtt
import ssl
import json
# HiveMQ Cloud credentials
BROKER_URL = "9713f3d043bf4e95bc9ef27e29b4654e.s1.eu.hivemq.cloud"
BROKER_PORT = 8883
USERNAME = "smart_attednace_system"
PASSWORD = "Smart#12345"

def start_listening(device_id):
    topic = f"devices/{device_id}/control"
    
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("✅ Connected to broker!")
            client.subscribe(topic)
            print(f"📡 Subscribed to topic: {topic}")
        else:
            print(f"❌ Connection failed with code {rc}")

    def on_message(client, userdata, msg):
        print(f"📨 Message from {msg.topic}: {msg.payload.decode()}")
        try:
            payload = json.loads(msg.payload.decode())
            action = payload.get("action")
            if action:
                userdata.put(action)  # Pass action to queue
        except Exception as e:
            print("❌ Failed to parse payload:", e)

    import queue
    action_queue = queue.Queue()

    client = mqtt.Client(userdata=action_queue)
    client.tls_set(tls_version=ssl.PROTOCOL_TLS)
    client.username_pw_set(USERNAME, PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER_URL, BROKER_PORT)

    client.loop_start()  # Use loop_start instead of blocking loop_forever

    # Generator loop
    while True:
        action = action_queue.get()
        yield action



def send_student_data(method, id):
    topic = f"attendance/{method}/request"
    if (method=="check-in"):
        payload = {
            "rfid_tag": id,
            "device_id" : "4",
            "marked_by" : "rfid"
        }
    elif(method=="check-out"):
        payload = {

            "student_id": id,
            "device_id" : "4",
            "marked_by" : "face_recognition"     
        }

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to broker (publisher)")
            client.publish(topic, json.dumps(payload))
            print(f"Sent to {topic}: {payload}")
            client.disconnect()
        else:
            print("Failed to connect, return code:", rc)

    client = mqtt.Client()
    client.tls_set(tls_version=ssl.PROTOCOL_TLS)
    client.username_pw_set(USERNAME, PASSWORD)
    client.on_connect = on_connect

    import json
    print("Publishing action...")
    client.connect(BROKER_URL, BROKER_PORT)
    client.loop_forever()




def get_attendance_response(method,device_id, timeout=10):
    response = None
    topic = f"attendance/{method}/response/${device_id}"
    done = False  # A flag to break immediately when response comes

    def on_message(client, userdata, msg):
        nonlocal response, done
        response = msg.payload.decode()
        print(f"✅ Received message on topic {msg.topic}: {response}")
        done = True  # Set the flag to True to break the waiting loop
        client.disconnect()  # Disconnect immediately

    client = mqtt.Client()

    # Authentication
    client.username_pw_set(USERNAME, PASSWORD)
    
    # Enable TLS encryption
    client.tls_set(tls_version=ssl.PROTOCOL_TLS)
    
    client.on_message = on_message

    try:
        client.connect(BROKER_URL, BROKER_PORT, keepalive=60)
    except Exception as e:
        print("❌ Error connecting to the broker:", e)
        return None

    client.subscribe(topic)
    print(f"📡 Subscribed to {topic}. Waiting for response...")

    client.loop_start()

    elapsed = 0
    interval = 0.1  # Shorter interval = faster reaction

    while not done and elapsed < timeout:
        time.sleep(interval)
        elapsed += interval

    client.loop_stop()

    if not done:
        print("⌛ No response received within timeout period.")
    return response
