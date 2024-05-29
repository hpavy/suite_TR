#--- GENERIC IMPORT ----------------------------------------------------------------------------------------------+
import os
import numpy as np

class DrlBase :

    def solve_problem_cimlib(self):
        """ Solve problem using cimlib and move vtu and drag folder. It changes properties."""
        os.system(
            'cd '+self.output_path+
            'cfd/.; touch run.lock; mpirun -n 8 /softs/cemef/cimlibxx/master/bin/cimlib_CFD_driver'+ 
            ' Principale.mtc > trash.txt;'
            )
        os.system('mv '+self.output_path+'cfd/Resultats/2d/* '+self.vtu_path+'.')
        os.system('mv '+self.output_path+'cfd/Resultats/Efforts.txt '+self.effort+'.')
        os.system('rm -r '+self.output_path+'cfd')
        os.system('cp -r '+self.vtu_path+'bulles_00500.vtu ./video/')                                  
        os.system('mv ./video/bulles_00500.vtu '+'./video/video_'+str(self.episode)+'.vtu')
        
    
    def compute_reward(self, control_parameters):
        """ Calcule le reward """
       #  try :            # Normalement pas besoin
        with open(self.effort+'/Efforts.txt', 'r') as f:
            next(f)                                        # Skip header
            L_finesse    = [] 
            f.readline()
            for ligne in f :
                cx, cy   = ligne.split()[-2:]
                cx, cy   = -float(cx), -float(cy)
                if cx*cy == 0.:
                    L_finesse.append(-100)                 # Si un des deux est nul on met un reward très faible  
                else :
                    L_finesse.append(cy/cx)
            finesse = np.array(L_finesse)                   
            
        # except :                                                # Si ça n'a pas marché 
        #     finesse = None
        

        #--- CALCUL DU REWARD -----------------------------------------------------------------------------------+

        begin_take_finesse = 400                                      # When we begin to take the reward 

        if finesse is not None :  
            self.reward      = finesse[begin_take_finesse:].mean() 
            self.reward      -= self.punition_affine_marge(marge=0.1) # Punition affine avec une marge de 10 % 
            self.finesse_moy = finesse[begin_take_finesse:].mean()
            self.finesse_max = finesse[begin_take_finesse:].max()

        else:                                                          # Si ça n'a pas tourné  
            self.reward      = -1000
            self.finesse_moy = -1000
            self.finesse_max = -1000

        ### Ecriture dans Reward
        if not os.path.isfile('fichiers_txt/reward.txt'):
            
            f = open('fichiers_txt/reward.txt','w')
            f.write(
                'Index'+'\t'+'finesse_moy'+'\t'+'finesse_max'+'\t'+'Area'+'\t'+'Reward'+'\n'
                )
        else:
            f = open('fichiers_txt/reward.txt','a')
        f.write(f"{str(self.episode)}\t{self.finesse_moy:.3e}\t"
                +f"{self.finesse_max:.3e}\t{self.area:.3e}\t"
                +f"{self.reward}\n"
                )
        f.close()
        self.episode += 1 
    
    
    #--- FONCTION DE PARAMETRISATION -----------------------------------------------------------------------------+

    def quadraticBezier(self,t,points):
        B_x = (1-t)*((1-t)*points[0][0]+t*points[1][0])+t*((1-t)*points[1][0]+t*points[2][0])
        B_y = (1-t)*((1-t)*points[0][1]+t*points[1][1])+t*((1-t)*points[1][1]+t*points[2][1])
        return B_x,B_y

    def cambrure(self, x, y, numPts):
        """ Donne la cambrure avec le point qui la contrôle """ 
        curve   = []
        t       = np.array([i*1/numPts for i in range(0,numPts)])
        B_x,B_y = self.quadraticBezier(t,[(0.,0.),(x,y),(1.,0.)])
        curve   = list(zip(B_x,B_y))
        return curve

    def find_camber_y(self, x, cambrure_coord):
        """ Pour un x donné il donne le y de la cambrure le plus proche """
        for k,coord_camber in enumerate(cambrure_coord):
            if coord_camber[0] > x :
                return (coord_camber[1]+cambrure_coord[k-1][1])/2           # On prend la moyenne des deux 
        return 0.
    
    def rotate(self,curve):
        """ Met un angle d'attaque en multipliant la courbe par une matrice de rotation """
        curve         = np.array(curve)
        rotate_matrix = np.array([
            [np.cos(self.angle), np.sin(self.angle)], [-np.sin(self.angle), np.cos(self.angle)]
            ])
        return curve @ rotate_matrix

    def polygon_area(self,curve):
        """ Crée un polynôme avec la courbe et calcul son aire """
        curve      = np.array(curve)
        x          = curve [:,0]
        y          = curve[:,1]
        correction = x[-1] * y[0] - y[-1]* x[0]
        main_area  = np.dot(x[:-1], y[1:]) - np.dot(y[:-1], x[1:])
        return 0.5*np.abs(main_area + correction)
    
#--- FONCTION DE PUNITION POUR LA SURFACE -----------------------------------------------------------------------+

    def punition_exponentielle(self):
        """ Donne la punition que l'on doit mettre dans le reward (exponentielle) """
        if self.area < self.area_min :
            return np.exp((self.area_min/self.area) -1) - 1       # vaut 0 au début 
        else : 
            return 0. 

    def punition_affine_marge(self, marge):
        """ Donne une punition affine de alpha * (S-Sref) avec marge de marge %"""
        if self.area_target * (1 - marge) < self.area < self.area_target * (1 + marge) : 
            return 0
        elif self.area < self.area_target * (1 - marge) : 
            return self.alpha * abs((1 - marge) * self.area_target - self.area)
        else : 
            return self.alpha * abs((1 + marge) * self.area_target - self.area)

    def punition_affine(self) : 
        """ Donne une punition de la forme alpha * abs(S-Sref) """
        return self.alpha * abs(self.area - self.area_target)
        
        