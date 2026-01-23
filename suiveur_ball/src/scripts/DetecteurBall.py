#!/usr/bin/env python3

# Python packages
import cv2
import numpy as np

import rospy
from cv_bridge import CvBridge
from sensor_msgs.msg import CompressedImage
from geometry_msgs.msg import Point 

from ultralytics import YOLO

class DetecteurBall:
    def __init__(self):
        rospy.init_node('detecteur_ball_node')
        self.bridge = CvBridge()
        
        # Chargement du modele
        try:
            # Assurez-vous que le fichier best.onnx est accessible
            self.model = YOLO('best.onnx', task='detect') 
            rospy.loginfo("Modele charge.")
        except Exception as e:
            rospy.logerr(f"Erreur chargement modele: {e}")

        # Publishers
        # Pour voir l'image 
        self.img_publisher = rospy.Publisher('/ball_detector/image/compressed', CompressedImage, queue_size=10)
        # Pour le robot (Donnees x, y, z) 
        self.data_publisher = rospy.Publisher('/ball_info', Point, queue_size=10)
        
        # Subscriber
        self.subscriber = rospy.Subscriber('/raspicam_node/image/compressed', CompressedImage, self.camera_callback, queue_size=10)

    def localiserLaBallParYolo8(self, msg, display=False):
        try:
            # Conversion unique pour gagner du temps
            frame_orig = self.bridge.compressed_imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            rospy.logerr(f"Erreur conversion image: {e}")
            return

        # Resize pour correspondre a la taille du modele et accelerer le calcul
        frame = cv2.resize(frame_orig, (128, 128))

        # Prediction
        results = self.model.predict(frame, imgsz=128, conf=0.5, verbose=False)
        
        # Message Point a envoyer
        target_msg = Point()
        target_msg.z = 0.0 # Par defaut: 0 (pas de balle)
        
        # Si on a des resultats
        if len(results) > 0:
            for r in results:
                # Recuperation des boites
                box = r.boxes.cpu()
                box_sz = box.xyxy.numpy()

                if box_sz.size != 0: # Si au moins un objet est detecte
                    
                    # On plot pour l'affichage humain
                    res_plotted = r.plot() 

                    # Calculer le centre de la bounding box
                    x_center = int((box_sz[0][0] + box_sz[0][2]) / 2)
                    y_center = int((box_sz[0][1] + box_sz[0][3]) / 2)

                    # Centre de l'image (128 / 2 = 64)
                    img_center_x = res_plotted.shape[1] // 2
                    img_center_y = res_plotted.shape[0] // 2

                    # Distance par rapport au centre (commande de suivi)
                    dx = x_center - img_center_x
                    dy = y_center - img_center_y
                    
                    # Calcul de la taille de la boite (pour estimer la distance)
                    box_width = box_sz[0][2] - box_sz[0][0]

                    # VISUEL
                    cv2.circle(res_plotted, (x_center, y_center), 4, (0, 0, 255), -1)
                    cv2.line(res_plotted, (x_center, y_center), (img_center_x, img_center_y), (255, 0, 0), 2)

                    target_msg.x = float(dx)        # Erreur horizontale
                    target_msg.y = float(box_width) # Taille (proxy distance)
                    target_msg.z = 1.0              # Flag "Balle trouvee"

                    # Mise a jour de l'image pour l'affichage
                    frame = res_plotted 
                    break 
        
        # PUBLICATION DES DONNEES
        # On envoie le Point au ControleurMouvement
        self.data_publisher.publish(target_msg)

        # PUBLICATION DE L'IMAGE
        out_msg = self.bridge.cv2_to_compressed_imgmsg(frame)
        self.img_publisher.publish(out_msg)
        
        if display: 
            cv2.imshow('YOLO V8 Detection', frame)
            cv2.waitKey(1)
            
    def camera_callback(self, img):
        # On appelle la fonction de traitement
        self.localiserLaBallParYolo8(img, display=True)

if __name__ == '__main__':
    detecteur = DetecteurBall()
    rospy.spin()