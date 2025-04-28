from core.MFRC522 import MFRC522
def read_card(stop_flag):
    """ Waits for an RFID card and returns its UID """
    reader = MFRC522()

    while not stop_flag.is_set():  # Check stop flag
        try:
            (status, _) = reader.MFRC522_Request(reader.PICC_REQIDL)
            if status == reader.MI_OK:
                (status, uid) = reader.MFRC522_Anticoll1()
                if status == reader.MI_OK:
                    return "-".join(str(i) for i in uid)
            sleep(0.5)  # Reduce CPU usage
        except Exception as e:
            print(f"RFID Error: {e}")

    return None  # Return None when stopping


