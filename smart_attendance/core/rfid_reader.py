from time import sleep
from core.MFRC522 import MFRC522

def read_card(stop_flag):
    """ Waits for an RFID card and returns its UID """
    from core.MFRC522 import MFRC522
    import time
    
    try:
        # Initialize reader outside the loop
        reader = MFRC522(bus=0, dev=0, spd=500000)  # Try lower SPI speed for better stability
        
        # Ensure proper initialization
        reader.MFRC522_Init()
        
        consecutive_errors = 0
        max_errors = 3
        
        while not stop_flag.is_set():
            try:
                # Reset on too many errors
                if consecutive_errors >= max_errors:
                    print("Too many errors, reinitializing reader...")
                    reader.MFRC522_Init()
                    consecutive_errors = 0
                    time.sleep(0.5)
                    continue
                
                # Request card
                (status, _) = reader.MFRC522_Request(reader.PICC_REQIDL)
                
                if status == reader.MI_OK:
                    # Card detected, try to get UID
                    (status, uid) = reader.MFRC522_Anticoll1()
                    if status == reader.MI_OK:
                        consecutive_errors = 0  # Reset error count on success
                        uid_string = "-".join(str(i) for i in uid)
                        print(f"Card detected: {uid_string}")
                        return uid_string
                
                # Use a shorter sleep for more responsive reading
                time.sleep(0.1)
            
            except Exception as e:
                consecutive_errors += 1
                print(f"RFID Error {consecutive_errors}/{max_errors}: {e}")
                time.sleep(0.2)  # Short delay before retry
    
    except Exception as e:
        print(f"Critical RFID setup error: {e}")
    finally:
        # Clean up resources when stopping
        if 'reader' in locals():
            try:
                reader.spi.close()
                print("RFID reader resources released")
            except:
                pass
    
    return None  # Return None when stopping
