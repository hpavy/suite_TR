###### Fonction qui regarde si le range est bon ######

# Importer la class 
import os
import sys
import numpy as np
import shutil

dossier_parent = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(dossier_parent)
from immersion import immersion



# On va modifier la classe pour juste tester la génération de forme 

class immersion_modified(immersion):
    
    def __init__(self, range_min, range_max):
        self.range_min = range_min # le range min qu'on veut tester 
        self.range_max = range_max # le range max qu'on veut tester 
        super().__init__(path = 'test_range')
        
    def create_shape(self, control_parameter, ep):
        self.output_path = self.path+'/'+str(ep)+'/'
        os.makedirs(self.output_path + 'cfd/')
        self.shape_generation_dussauge(control_parameter)
        
    def test_a_lot(self):
        for k in range(15):
            vect_random = np.random.rand(len(self.range_min))
            control_parameter = vect_random * self.range_min + (1-vect_random) * self.range_max
            self.create_shape(control_parameter, k)
        print('OK tout bon')
        shutil.rmtree(self.path)
        shutil.rmtree('fichiers_txt')
    
        



if __name__ == '__main__':
    #### range à tester : 
    range_min = np.array([0.005, 0, 0, 0, 0, -0.15, -0.1, -0.1, 0, -0.1 ])
    range_max = np.array([0.05, 0.09, 0.17, 0.09, 0.15, 0., 0., 0., 1, 0.1 ])
    test = immersion_modified(range_min, range_max)
    test.test_a_lot()




