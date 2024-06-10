#--- GENERIC IMPORT ----------------------------------------------------------------------------------------------+
import os
import sys
import math
import time
import numpy as np
import gmsh
import matplotlib as plt
import datetime as dt
from fichiers_python.classes_bases import DrlBase


        #################################################
        ## ENVIRONMENT TO OPTIMISE AN AIRFOIL WITH DRL ##
        #################################################


class immersion(DrlBase):

#--- CREATE OBJECT ---------------------------------------------------------------------------------------------+
    def __init__(self, path):
        self.name     = 'immersion'                                      # Fill structure
        self.act_size = 10
        self.obs_size = self.act_size
        self.obs      = np.zeros(self.obs_size)

    # Variable structure : une pour l'eading edge et les autres pour les points de contrôle : 
    # La première contrôle le bord d'attaque 
    # De 2 à 8 : contrôle les points 
    # De 9 à 10 si on fait varier la cambrure : jouent sur l'abscisse du point qui définit la cambrure 

        self.x_min       = np.array([0.005, 0, 0, 0, 0, -0.08, -0.1, -0.1, 0, -0.1 ])  # Fin cambrure, attention
        self.x_max       = np.array([0.05, 0.07, 0.12, 0.07, 0.15, 0., 0., 0., 1, 0.1 ]) 
        self.x_0         = np.array([                            # Coord du naca 2412
            0.0234,  0.0821,  0.122,  0.124,
            0.0846, -0.0132,  -0.00811,  -0.0212, 0, 1])
        self.x_camb      = 0.                                     # La cambrure
        self.y_camb      = 0.                                     # La cambrure
        self.area        = 0  
        self.path        = path
        self.finesse_moy = 0
        self.finesse_max = 0
        self.area_target = 0.08 
        self.area_min    = 0.1 
        self.angle       = 0.
        self.alpha       = 200 
        self.episode = 0
        self.time_init   = 0.
        self.time_end    = 0.
        os.makedirs('fichiers_txt', exist_ok=True)       # Pour mettre les fichiers textes de résultats 
        






    def shape_generation_dussauge(self, control_parameters):
        """ Generate shape using the parametrisation in Dessauge paper  modify to take camber in account """
        control_points = self.reconstruct_control_points(control_parameters)  
        if self.episode != 0 :        # on ne veut pas de la première car bug ecriture du fichier
            # On écrit la valeur de l'épisode 
            if not os.path.isfile('fichiers_txt/Values.txt'):
                f = open('fichiers_txt/Values.txt','w')
                head = "Index   episode"
                for k in range(self.act_size):
                    head += f'\t{k}'
                head += '\n'
                f.write(head)
            else:
                f = open('fichiers_txt/Values.txt','a')
            new_line = str(self.episode)+'\t'+str(self.ep)
            for k in range(self.act_size):
                new_line +=  '\t' + "{:.3e}".format(control_parameters[k])   # On écrit les control parameters 
            new_line += '\n'
            f.write(new_line)
            f.close()
        
        # Transforme les actions en control point
        curve          = self.airfoil(control_points,16)                 # Donne la courbe de l'aile
        self.area      = self.polygon_area(curve)
        curve          = self.rotate(curve)                              # Si on met un angle d'attaque
        
        ### On mesh le nouvel airfoil
        mesh_size      = 0.005                                           # Mesh size
        #try:    # Normalement ça marche direct 
        gmsh.initialize(sys.argv)                          # Init GMSH
        gmsh.option.setNumber("General.Terminal", 1)       # Ask GMSH to display information in the terminal
        model = gmsh.model                                 # Create a model and name it "shape"
        model.add("shape")        
        shapepoints = []
        for j in range(len(curve)):
            shapepoints.append(model.geo.addPoint(curve[j][0], curve[j][1], 0.0,mesh_size))
        shapepoints.append(shapepoints[0])
        shapespline = model.geo.addSpline(shapepoints)                    # Curveloop using splines
        model.geo.addCurveLoop([shapespline],1)
        model.geo.addPlaneSurface([1],1)                                  # Surface  

        ### This command is mandatory and synchronize CAD with GMSH Model. 
        ### The less you launch it, the better it is for performance purpose
        model.geo.synchronize()
        gmsh.option.setNumber("Mesh.MshFileVersion", 2.0)                  # gmsh version 2.0
        model.mesh.generate(2)                                             # Mesh (2D)
        gmsh.write(self.output_path+'cfd/airfoil.msh')                     # Write on disk
        gmsh.finalize()                                                    # Finalize GMSH

        # except Exception as e:
        #     ### Finalize GMSH
        #     gmsh.finalize()
        #     print('error: ', e)   ##### Normalement pas besoin 
        #     pass

                

    ### Take one step
    def step(self, actions, ep):
        conv_actions = self.convert_actions(actions)
        reward       = self.cfd_solve(conv_actions, ep)
        return reward, conv_actions

    ### Provide observation
    def observe(self):
        # Always return the same observation
        return self.obs

    ### Convert actions
    def convert_actions(self, actions):
        """ Converti les actions du DRL qui sont entre 0 et 1 """
        # Convert actions
        conv_actions  = self.act_size*[None]
        x_p           = self.x_max - self.x_0
        x_m           = self.x_0   - self.x_min

        for i in range(self.act_size):
            if (actions[i] >= 0.0):
                conv_actions[i] = self.x_0[i] + x_p[i]*actions[i]
            if (actions[i] <  0.0):
                conv_actions[i] = self.x_0[i] + x_m[i]*actions[i]
        return conv_actions

    ### Close environment
    def close(self):
        pass

    ### A function to replace text in files
    ### This function finds line containing string, erases the
    ### whole line it and replaces it with target
    def line_replace(self, string, line, target):
        command = "sed -i '/"+string+"/c\\"+line+"' "+target
        os.system(command)


#--- FONCTION DE PARAMETRISATION ------------------------------------------------------------------------------+

    def reconstruct_control_points(self, control_parameter):
        ### Les points autour desquels on bouge
        if len(control_parameter) == 10 : 
            x_param_cambrure, y_param_cambrure =  control_parameter[-2:]     
            # Les deux points definissant la cambrure 
        else :
            x_param_cambrure, y_param_cambrure =  0., 0.                     
            # Si on n'optimise pas avec la cambrure

        cambrure_coord = self.cambrure(x_param_cambrure, y_param_cambrure,16*40)
        base_points    =[[1,0.001],                                                    # Trailing edge (top)
                        [0.76,None],
                        [0.52,None],
                        [0.25,None],
                        [0.1,None],
                        [0,None],                                                   # Leading edge (top)
                        [0,None],                                                   # Leading edge (bottom)
                        [0.15,None],
                        [0.37,None],
                        [0.69,None],
                        [1,-0.001]] 

        ### Construction des control points pour génerer la courbe 
        control_points             = base_points[::]                                     
        control_points[5][1]       =  control_parameter[0] 
        control_points[5][1]       += self.find_camber_y(control_points[5][0], cambrure_coord)
        control_points[6][1]       = - control_parameter[0] 
        control_points[6][1]       += self.find_camber_y(control_points[6][0], cambrure_coord)
        for k in range(4):
            control_points[k+1][1] =  control_parameter[1+k] 
            control_points[k+1][1] += self.find_camber_y(control_points[k+1][0], cambrure_coord)
        for k in range(3):
            control_points[k+7][1] =  control_parameter[5+k] 
            control_points[k+7][1] +=self.find_camber_y(control_points[k+7][0], cambrure_coord)
        return control_points

    def airfoil(self,ctlPts,numPts):
        """ Crée la courbe de l'airfoil avec numPts nombre de points """
        curve = []
        t     = np.array([i*1/numPts for i in range(0,numPts)])
        
        ### Calculate first Bezier curve
        midX       = (ctlPts[1][0]+ctlPts[2][0])/2
        midY       = (ctlPts[1][1]+ctlPts[2][1])/2
        B_x,B_y    = self.quadraticBezier(t,[ctlPts[0],ctlPts[1],[midX,midY]])
        curve      = curve+list(zip(B_x,B_y))

        ### Calculate middle Bezier Curves
        for i in range(1,len(ctlPts)-3):
            midX_1  = (ctlPts[i][0]+ctlPts[i+1][0])/2
            midY_1  = (ctlPts[i][1]+ctlPts[i+1][1])/2
            midX_2  = (ctlPts[i+1][0]+ctlPts[i+2][0])/2
            midY_2  = (ctlPts[i+1][1]+ctlPts[i+2][1])/2
            B_x,B_y = self.quadraticBezier(t,[[midX_1,midY_1],ctlPts[i+1],[midX_2,midY_2]])
            curve   = curve+list(zip(B_x,B_y))                     
    
        ### Calculate last Bezier curve
        midX    = (ctlPts[-3][0]+ctlPts[-2][0])/2
        midY    = (ctlPts[-3][1]+ctlPts[-2][1])/2
        B_x,B_y = self.quadraticBezier(t,[[midX,midY],ctlPts[-2],ctlPts[-1]])
        curve   = curve+list(zip(B_x,B_y))
        curve.append(ctlPts[-1])
        return curve



