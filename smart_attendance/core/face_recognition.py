import cv2
import picamera2
import time


def camera_test():

        cv2.startWindowThread()

        picam2 = picamera2.Picamera2()
        picam2.configure(picam2.create_preview_configuration(main={"format": 'XRGB8888', "size": (800, 600)}))
        picam2.start()

        while True:
                im= picam2.capture_array()
                cv2.imshow("Camera", im)
                
                key = cv2.waitKey(1)
                if key==ord('s'):
                        timeStamp = time.strftime("%Y%m%d-%H%M%S")
                        targetPath="/home/pi5/Desktop/img" + "_"+timeStamp+".jpg"
                        cv2.imwrite(targetPath, im)
                        print("- Saved:", targetPath)

                elif key==ord('q'):
                        print("Quit")
                        break

        cv2.destroyAllWindows()


camera_test()
