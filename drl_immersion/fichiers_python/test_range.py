###### Fonction qui regarde si le range est bon ######

# Importer la class 
from immersion import immersion
import os
import numpy as np
import random



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
        for k in range(500):
            vect_random = np.random.rand(len(self.range_min))
            control_parameter = vect_random * self.range_min + (1-vect_random) * self.range_max
            self.create_shape(control_parameter, k)



if __name__ == '__main__':
    
    
    
    #### range à tester : 
    range_min = np.array([0.005, 0, 0, 0, 0, -0.15, -0.1, -0.1, 0, -0.1 ])
    range_max = np.array([0.05, 0.09, 0.17, 0.09, 0.15, 0., 0., 0., 1, 0.1 ])
    test = immersion_modified(range_min, range_max)
    test.test_a_lot()
    # essayer de générer un profil :
    # test.create_shape(np.array([                            # Coord du naca 2412
    #         0.0234,  0.0821,  0.122,  0.124,
    #         0.0846, -0.0132,  0.00811,  0.0212, 0, 0]), -3)
    
    #test.test_a_lot()



