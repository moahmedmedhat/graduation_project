from time import sleep
import paho.mqtt.client as mqtt
import ssl

# HiveMQ Cloud credentials
BROKER_URL = "your_broker_url"
BROKER_PORT = 8883
USERNAME = "your_username"
PASSWORD = "your_pass"

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





def send_action(method, id):
    topic = f"attendance/{method}/request"
    if (method=="check-in"):
        payload = {
            "method": method,
            "rfid_tag": id
        }
    elif(method=="check-out"):
        payload = {
            "method": method,
            "student_id": id
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







