# import cv2

# # Alternative GStreamer pipeline
# try:
#     cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) 

#     windo_name="camera preview"

#     while True:
#         ret,frame=cap.read()
        
#         if not ret:
#             print("error unable to capture frame")
#             break
        
#         cv2.imshow(windo_name,frame)
        
#         key=cv2.waitKey(1)
        
#         if key == ord('c'):
#             cv2.imwrite('photo.jpg',frame)
#             print('image captured successfuly')
        
        
#         if key == ord('q'):
#             break
        
#     cap.release()
#     cv2.destroyAllWindows()
# except:
#     if not cap.isOpened():
#         print('error unable to access the cameta')
    
# import cv2

# cap = cv2.VideoCapture(0)  # Try default camera

# if not cap.isOpened():
#     print("Error: Unable to access the camera")
# else:
#     print("Camera successfully accessed")

#     ret, frame = cap.read()
#     if not ret:
#         print("Error: Unable to capture frame")
#     else:
#         print("Frame captured successfully")
#         cv2.imshow("Test Frame", frame)
#         cv2.waitKey(0)
#         cv2.destroyAllWindows()

# cap.release()

# import cv2

# cams_test=100
# for i in range (-1,cams_test):
#     cap=cv2.VideoCapture(i,cv2.CAP_DSHOW)
#     test, frame=cap.read()
#     print("i : "+str(i)+" // result: " +str(test))
#     if test:
#         print("SUCCESSFULL!")




import cv2
cam_port = 0
cam = cv2.VideoCapture(cam_port)
print(cam.isOpened())
print(cam.grab())
print(cam.read())
cam.release()