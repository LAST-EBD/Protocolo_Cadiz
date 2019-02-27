
import os
from Protocolo_HP import Mosaic_Landsat


def call_mosaic(path):
    
    
    d = {}
    l = []
    
    for i in os.listdir(path):
        date = i[:12]
        d[date] = []
        
    for i in os.listdir(path):
        date = i[:12]
        d[date].append(i)
        
        
    for lista in d.values():
        for escena in lista:
            
            l.append(str(os.path.join(path, escena)))
        #print(l)    
    #str1 = ', '.join(l)
    
    
    
    t = Mosaic_Landsat(l[0], l[1])
    t.run()


call_mosaic('/media/diego/datos_linux/FranHP/Protocolo_HP/ori') 
