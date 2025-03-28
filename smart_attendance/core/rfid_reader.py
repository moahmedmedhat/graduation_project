import RPi.GPIO as gpio
from mfrc522 import SimpleMFRC522
from time import sleep


gpio.setwarnings(False)

def read_card():
    reader=SimpleMFRC522()
    try:
        print("hold your tag near to reader")
        id,txt=reader.read()
        # print(f"your id is {id}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        gpio.cleanup()
    return id
