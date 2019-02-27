
import os, shutil, pymongo, re, time, subprocess, pandas, rasterio, sys, stat 
import numpy as np
import seaborn as sns; sns.set(color_codes=True)
import matplotlib.pyplot as plt
from osgeo import gdal, gdalconst
from datetime import datetime, date
from scipy import ndimage
from scipy.stats import linregress
from urllib.request import urlopen



class Mosaic_Landsat(object):
    
    
    '''Clase para mosaicar escenas Landsat. En principio está pensada para mosaicar las bandas del optico de Landsats
    TM, ETM+ y OLI. Se asume que las imagenes de entrada comparten el mismo sistema de coordenadas. En nuestro caso será para 
    trabajar sobre las escenas 202-034 y 202-035'''
    
    
    def __init__(self, *args):
        
        
        '''Instanciamos la clase con la escena que vayamos a procesar, hay que introducir la ruta a la escena en ori
        y de esa ruta el constructor obtiene el resto de rutas que necesita para ejecutarse. Los parametros marcados por defecto son el 
        umbral para la mascara de nubes Fmask y el numero de elementos a incluir en el histograma de las bandas'''
       
        #Create the dicts to store the path for every bands
        self.d = {}
        self.args = args
        self.ruta_escena = args[0]
        self.ori = os.path.split(args[0])[0]
        self.escena = os.path.split(args[0])[1]
        self.raiz = os.path.split(self.ori)[0]
        self.rad = os.path.join(self.raiz, 'rad')
        self.nor = os.path.join(self.raiz, 'nor')
        self.data = os.path.join(self.raiz, 'data')
        self.temp = os.path.join(self.raiz, 'temp')
        self.mos = os.path.join(self.raiz, 'mos')
        self.cloud_mask = 'None'
                    
        for i in self.args:
            print('Escena:', i)
                   
          
    def fmask(self):

        '''-----\n
        Este metodo genera el algortimo Fmask que sera el que vendra por defecto en la capa de calidad de
        las landsat a partir del otono de 2015'''

        for i in self.args:
            
            os.chdir(i)

            print('comenzando Fmask')

            try:

                print('comenzando Fmask')
                t = time.time()
                #El valor (el ultimo valor, que es el % de confianza sobre el pixel (nubes)) se pedira desde la interfaz que se haga. 
                a = os.system('/usr/GERS/Fmask_4_0/application/run_Fmask_4_0.sh /usr/local/MATLAB/MATLAB_Runtime/v93 3 3 1 50')
                a
                if a == 0:
                    self.cloud_mask = 'Fmask'
                    print('Mascara de nubes (Fmask) generada en ' + str(t-time.time()) + ' segundos')

                else:

                    #Aqui iria la alternativa a Fmask, pero ya no falla nunca
                    t = time.time()
                    print('comenzando Fmask NoTIRS')
                    a = os.system('C:/Cloud_Mask/Fmask_3_2')
                    a
                    if a == 0:
                        self.cloud_mask = 'Fmask NoTIRS'
                        print('Mascara de nubes (Fmask NoTIRS) generada en ' + str(t-time.time()) + ' segundos')
                    else:
                        print('La jodimos, no hay Fmask')
                        print('comenzando BQA')
                        for i in os.listdir(self.ruta_escena):
                            if i.endswith('BQA.TIF'):
                                masker = LandsatMasker(os.path.join(self.ruta_escena, i))
                                mask = masker.get_cloud_mask(LandsatConfidence.high, cirrus = True, cumulative = True)
                                masker.savetif(mask, os.path.join(self.ruta_escena, self.escena + '_Fmask.TIF'))
                        self.cloud_mask = 'BQA'
                        print('Mascara de nubes (BQA) generada en ' + str(t-time.time()) + ' segundos')


            except Exception as e:

                print("Unexpected error:", type(e), e)
                
                
                
    def mosaic(self):
        
        '''Este metodo realiza el mosaico entre las escenas, incluyendo la mascara de nubes'''
        
        #Read the data and write the dicts
        for i in self.args:
            
            print('IIIIIII!!!!!!!!:', i)
            
            escena = os.path.split(i)[1][:10]
            print('ESCENA:', escena)
            for banda in os.listdir(i):
                if (banda.endswith('.TIF') or banda.endswith('.tif')) and not 'BQA' in banda:
                    b = banda.split('_')[-1].split('.')[0]
                    self.d[b] = []

        for i in self.args:

            #escena = i.split('_')[4] + '_' + i.split('_')[3]
            #print(escena)
            for banda in os.listdir(i):
                if (banda.endswith('.TIF') or banda.endswith('.tif')) and not 'BQA' in banda:
                    print(banda)
                    b = banda.split('_')[-1].split('.')[0]
                    
                    self.d[b].append(os.path.join(i, banda))

        for k, v in self.d.items():
            str1 = ' '.join(v)
            print(str1)
            
            if 'Fmask' in str1:
                
                output = os.path.join(self.mos, escena + '_Mos_' + k + '.TIF') #+ i.split('_')[3]
                print(output)

                os.system('gdal_merge.py -n 255 -a_nodata 255 {} -o {}'.format(str1, output))
                
            else:
                
                output = os.path.join(self.mos, escena + '_Mos_' + k + '.TIF') #+ i.split('_')[3]
                print(output)

                os.system('gdal_merge.py -n 0 {} -o {}'.format(str1, output))
            
            
    def run(self):
        
        self.fmask()
        self.mosaic()
    
  
