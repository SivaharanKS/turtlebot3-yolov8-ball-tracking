#!/usr/bin/env python3

import rospy
from geometry_msgs.msg import Twist, Point

class ControleurMouvement:
    def __init__(self):
        self.rate = rospy.Rate(rospy.get_param('freq_control'))
        
        self.MODE_RECHERCHE = 1
        self.MODE_SUIVI = 2
        self.mode = self.MODE_RECHERCHE
        
        self.velocity = Twist()
        self.publisher = rospy.Publisher('cmd_vel', Twist, queue_size=1)
                
        # Variables de navigation
        self.balle_detectee = False
        self.ball_dx = 0.0 
        self.taille_balle = 0.0
        
        # REGLAGES
        self.K_ROT = 0.015  # Sensibilite de la rotation        
        self.TAILLE_CIBLE = 20.0  # Taille cible : pixels pour laquelle il s'arrete.
        self.VITESSE_LIN = 0.2  # Vitesse pour avancer
        self.VITESSE_ROTA_RECHERCHE = 0.3 # Vitesse rotation pour la recherche
        
        # Subscriber qui recoit le Point du detecteur
        self.sub_info = rospy.Subscriber('/ball_info', Point, self.callback_ball)

    def callback_ball(self, msg):
        self.ball_dx = msg.x       # Erreur horizontale (pixels)
        self.taille_balle = msg.y  # Taille de la boite
        
        # Si z=1.0, la balle est detectee
        if msg.z > 0.5:
            self.balle_detectee = True
            self.mode = self.MODE_SUIVI
        else:
            self.balle_detectee = False
            self.mode = self.MODE_RECHERCHE 
            
    def run(self):
        while not rospy.is_shutdown():
            try:
                ## Le cas ou le robot cherche la balle
                
                if self.mode == self.MODE_RECHERCHE:
                    self.drive(0.0, self.VITESSE_ROTA_RECHERCHE)
                    rospy.loginfo("Mode Recherche")
                    
                ## Le cas ou le robot voit la balle
                
                elif self.mode == self.MODE_SUIVI:
                    
                    # ROTATION
                    vit_ang = -self.ball_dx * self.K_ROT
                    
                    # AVANCE
                    if self.taille_balle < self.TAILLE_CIBLE:
                        vit_lin = self.VITESSE_LIN
                    else:
                        vit_lin = 0.0 
                        
                    self.drive(vit_lin, vit_ang)
                    rospy.loginfo(f"Suivi: dx={self.ball_dx:.1f} | Dist={self.taille_balle:.1f}/{self.TAILLE_CIBLE}")
                        
                self.publisher.publish(self.velocity)
                self.rate.sleep()
                
            except rospy.ROSInterruptException:
                pass

    def drive(self, x, z):
        self.velocity.linear.x = x
        self.velocity.angular.z = z

if __name__ == '__main__':
    rospy.init_node('ctl_mouv_node')
    cm = ControleurMouvement()
    cm.run()
    rospy.spin()
