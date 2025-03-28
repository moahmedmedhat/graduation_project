import time
from core.MFRC522 import MFRC522


def read_card(stop_flag):
    reader = MFRC522()
    try:
        # Detect if a card is present
        (status, _) = reader.MFRC522_Request(reader.PICC_REQIDL)
        if status == reader.MI_OK:
            # Get UID of the card
            (status, uid) = reader.MFRC522_Anticoll1()
            if status == reader.MI_OK:
                return "-".join(str(i) for i in uid)
    except Exception as e:
        print(f"RFID Error: {e}")
    return None



