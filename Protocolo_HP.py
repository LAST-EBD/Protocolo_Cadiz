
import os, shutil, pymongo, re, time, subprocess, pandas, rasterio, sys, stat 
import numpy as np
import seaborn as sns; sns.set(color_codes=True)
import matplotlib.pyplot as plt
from osgeo import gdal, gdalconst
from datetime import datetime, date
from scipy import ndimage
from scipy.stats import linregress
from urllib.request import urlopen
from scipy.stats import mode



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
        
        
        if 'l7etm' in self.escena:
            self.sat = 'L7'
        elif 'l8oli' in self.escena:
            self.sat = 'L8'
        elif 'l5tm' in self.escena:
            self.sat = 'L5'
        else:
            print(' No reconozco el satelite')
        print(self.sat, self.escena)
        self.kl = {}
        self.equilibrado = os.path.join(self.data, 'Equilibrada.tif')
        self.noequilibrado = os.path.join(self.data, 'NoEquilibrada.tif')
        self.parametrosnor = {}
        self.iter = 1
        self.cloud_mask = 'Fmask'
        self.hist = 1000
        
        self.mtl = {}
        for i in os.listdir(self.ruta_escena):
            #print i
            if i.endswith('MTL.txt'):
                mtl = os.path.join(self.ruta_escena,i)
                
                f = open(mtl, 'r') 

                 #Dict
                for line in f.readlines(): 
                    if "=" in line: 
                        l = line.split("=") 
                    self.mtl[l[0].strip()] = l[1].strip() 
        
                    
        print('Ruta escena:', self.ruta_escena, '\nRAD:', self.rad, '\nMOS:', self.mos)
        
                   
          
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
                
                
    def del_mosaic(self):
        
        '''Este metodo borra las bandas que estuvieran previamente en mos'''
        
        for i in os.listdir(self.mos):
            
            sc = os.path.join(self.mos, i)
            os.remove(sc)
            
   
                
    def mosaic(self):
        
        '''Este metodo realiza el mosaico entre las escenas, incluyendo la mascara de nubes'''
        
        #Read the data and write the dicts
        for i in self.args:
            
            escena = os.path.split(i)[1][:10]
            #print(escena)
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
                
                
                
    def projwin(self):
        
        '''En este metodo vamos a darle el extent a la escena. Asi ya podemos usar el mismo DTM para 
        cada escena y posteriormente sobre esta escena se calcularan las rad'''
        
        path_rad = os.path.join(self.rad, self.escena)
        os.makedirs(path_rad, exist_ok=True)
        
  
        for i in os.listdir(self.mos):
            if (re.search('B[1-7]', i) and not 'B6' in i) or re.search('Fmask4', i):

                ins = os.path.join(self.mos, i)
                out = os.path.join(path_rad, i)

                cmd = "gdal_translate -projwin  580485.0 4261215.0 856815.0 3885285.0 {} {}".format(ins, out)
                print(cmd)
                
                os.system(cmd)
                
                
                
                
    def get_kl_csw(self):
        
        '''Este metodo obtiene los Kl para cada banda. Lo hace buscando los valores minimos dentro 
        de las zonas clasificadas como agua y sombra orografica, siempre y cuando la sombra orografica 
        no este cubierta por nubes ni sombra de nubes. La calidad de la mascara e muy importante, por eso
        a las escenas que no se puedan realizar con Fmask habria que revisarles el valor de kl.
        Tambien distingue Landsar 7 de Landsat 8, aplicandole tambien a las Landsat 7 la mascara de Gaps'''
    
        #Empezamos borrando los archivos de temp, la idea de esto es que al acabar una escena queden disponibles
        #por si se quiere comprobar algo. Ya aqui se borran antes de comenzar la siguiente
        t = time.time()

        for i in os.listdir(self.temp):
            arz = os.path.join(self.temp, i)
            os.remove(arz)

        #Hacemos el recorte al dtm para que tenga la misma extension que la escena y poder operar con los arrays
        t = time.time()
             
        dtm = os.path.join(self.data, 'dtm_202_034035.tif') #Por defecto esta en 29 y solo para la 202_34
        azimuth = self.mtl['SUN_AZIMUTH']
        elevation = self.mtl['SUN_ELEVATION']
        
        #Una vez tenemos estos parametros generamos el hillshade
        salida = os.path.join(self.temp, 'hillshade.img')
        cmd = ["gdaldem", "hillshade", "-az", "-alt", "-of", "GTIFF"]
        cmd.append(dtm)
        cmd.append(salida)
        cmd.insert(3, str(azimuth))
        cmd.insert(5, str(elevation))
        proc = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        stdout,stderr=proc.communicate()
        exit_code=proc.wait()

        if exit_code: 
            raise RuntimeError(stderr)
        else:
            print(stdout)
            print('Hillshade generado')
        
        ruta = os.path.join(self.rad, self.escena)
        print('ruta:', ruta)
        
        for i in os.listdir(ruta):
            
            if i.endswith('Fmask4.TIF'): 
                rs = os.path.join(ruta, i)
                Fmask = gdal.Open(rs).ReadAsArray()
                print('Fmask: min, max, size: ', Fmask.min(), Fmask.max(), Fmask.size)
        
        for i in os.listdir(self.temp):
            
            if i.endswith('shade.img'):
                
                hill = os.path.join(self.temp, i)
                Hillshade = gdal.Open(hill).ReadAsArray()
                print('Hillshade: min, max, size: ', Hillshade.min(), Hillshade.max(), Hillshade.size)       

        #Queremos los pixeles de cada banda que esten dentro del valor agua (1) y sin nada definido ((0) 
        #para las sombras) de la Fmask (con lo cual tambien excluimos las nubes y sombras de nubes). 
        #Junto con estos valores, queremos tambien los valores que caen en sombra (se ha decidido que 
        #el valor de corte mas adecuado es el percentil 20)

        #Arriba estamos diciendo que queremos el minimo del agua o de la escena completa sin nubes ni 
        #sombras ni agua pero en sombra orografica
        
        #Ahora vamos a aplicar la mascara y hacer los histogramas
        
        if self.sat == 'L8':
            
            bandas = ['B2', 'B3', 'B4','B5', 'B6', 'B7']
            
        else:
            
            bandas = ['B1', 'B2', 'B3', 'B4','B5', 'B7']
            
            
        lista_kl = []
        for i in os.listdir(ruta):
            banda = i[-6:-4]
            if banda in bandas:
                raster = os.path.join(ruta, i)
                print('Raster:', raster)
                #data = gdal.Open(raster).ReadAsArray()
                data = rasterio.open(raster).read()
                #anadimos la distincion entre Fmask y BQA
                if self.cloud_mask == 'Fmask':
                    
                    if self.sat == 'L8':
                        print('usando Fmask con Landsat 8')
                        data2 = data[(((Fmask==1) | (((Fmask==0) & (data != 0)) & (Hillshade<(np.percentile(Hillshade, 20))))))]
                    else:
                        print('usando Fmask con Landsat', self.sat)
                        #Abrimos la mascara para evitar problemas con los valores bajos en los bordes de Fmask
                        inner = os.path.join(self.data, 'intern_buffer_mos.tif')
                        Inner = gdal.Open(inner).ReadAsArray()
                        data2 = data[(data != 0) & ((Inner == 1) & ((Fmask==1) | (((Fmask==0) & (data != 0)) & (Hillshade<(np.percentile(Hillshade, 20))))))]

                        #mask = np.copy(data)
                        #mask[mask != 0] == 1
                        #print('Ahora viene el erode')
                        #erode = ndimage.grey_erosion(data, size=(5,5,1))
                        #print(type(erode), erode.size, erode.shape)
                        
                        #data2 = data[((erode != 0) & ((Fmask==1) | (((Fmask==0) & (data != 0)) & (Hillshade<(np.percentile(Hillshade, 20))))))]
                    
                        #Aqui iria una alternativa a Fmask si fallara

                        print('data 2 * obtenido')

                        lista = sorted(data2.tolist())
                        print(sorted(lista)[:10])

                        data3 = data2[:self.hist]
                        self.kl[banda] = np.mean(lista[:10000]) #data2.min()

                        print('data3: ', data3.min(), data3.max())

                        df = pandas.DataFrame(lista[:10000])
                        plt.figure(); df.hist(figsize=(10,8), bins = 20, cumulative=False, color="Red"); 
                        plt.title(self.escena + '_gr_' + banda, fontsize = 18)
                        plt.xlabel("Pixel Value", fontsize=16)  
                        plt.ylabel("Count", fontsize=16)
                        path_rad = os.path.join(self.rad, self.escena)
                        os.makedirs(path_rad, exist_ok=True)
                        name = os.path.join(path_rad, self.escena + '_gr_'+ banda.lower() + '.png')
                        plt.savefig(name)

        plt.close('all')
        
        print('Histogramas generados')
        print('kl_values:', sorted(self.kl.items()))
        
        
        
    def get_radiance(self):
                  
        '''-----\n
        Este metodo genera los valores de radiancia de la imagen, calculandolos a partir de
        los coeficientes que aparecen en el MTL'''   
                  
        path_rad = os.path.join(self.rad, self.escena)
        print(path_rad)
        
        #if self.sat == 'L8':
        
        for i in os.listdir(path_rad):

            if re.search('B[1-7].TIF', i):

                banda = i.split('_')[-1].split('.')[0]
                print('BANDA:', banda)


                RADMULT = float(self.mtl['RADIANCE_MULT_BAND_'+ banda[1:]])
                RADADD = float(self.mtl['RADIANCE_ADD_BAND_'+ banda[1:]])


                with rasterio.open(os.path.join(path_rad, i)) as src:

                    B = src.read()
                    RAD = RADMULT * B + RADADD

                    profile = src.meta
                    profile.update(dtype=rasterio.float32)

                    outfile = os.path.join(path_rad, banda + '_rad.tif')
                    print(outfile)                

                    with rasterio.open(outfile, 'w', **profile) as dst:
                        dst.write(RAD.astype(rasterio.float32))
                    
                    
                    
    def corrad(self):
                  
        '''-----\n
        Este metodo genera el equivalente a la Correción Radiométrica realizada por MiraMon, segun el paper
        Pons X, Solé-Sugrañes L (1994) "A Simple Radiometric Correction Model to Improve Automatic Mapping of 
        Vegetation from Multispectral Satellite Data." Remote Sensing of Environment, 48:191-204. Pero presindiendo
        del programa'''      
        
        #Parametros obtenidos del archivo de MiraMon m_atmos_rad
        bandnames = {'B1': 'blue', 'B2': 'green', 'B3': 'red', 'B4': 'nir', 'B5': 'swir1', 'B7': 'swir2'}
        # Se usan los valores existentes en el archivo m_atmos_rad del Corrad de 2014 (Maquina Virtual del LAST)
        essunl8 = {'B2':2081.34, 'B3': 1776.50, 'B4': 1552.82, 'B5': 1113.74, 'B6': 171.061, 'B7': 105.38}
        essunl7 = {'B1':1997, 'B2': 1812, 'B3': 1533, 'B4': 1039, 'B5': 230.8, 'B7': 84.9}
        taul8 = {'B2': 0.4, 'B3': 0.34, 'B4': 0.29, 'B5': 0.21, 'B6': 0.11, 'B7': 0.08}
        taul7 = {'B1': 0.5, 'B2': 0.3, 'B3': 0.25, 'B4': 0.2, 'B5': 0.125, 'B7': 0.075}

        if self.sat == 'L8':
            essun, tau = essunl8, taul8
        else:
            essun, tau = essunl7, taul7
            
            
        path_rad = os.path.join(self.rad, self.escena)
        
        for i in os.listdir(path_rad):
            
            if i.endswith('_rad.tif'):
                banda = i.split('_')[0]
                
                if banda in tau.keys():

                    RADMULT = float(self.mtl['RADIANCE_MULT_BAND_'+ banda[1:]])
                    RADADD = float(self.mtl['RADIANCE_ADD_BAND_'+ banda[1:]])
                    print(banda)
                    with rasterio.open(os.path.join(path_rad, i)) as src:
                        B = src.read()

                    klradiancia = (RADMULT * self.kl[banda]) +  RADADD
                    print(klradiancia)
                    radkl = B - klradiancia
                    NUM = np.pi * radkl * np.power(float(self.mtl['EARTH_SUN_DISTANCE']), 2) #d['EARTH_SUN_DISTANCE']

                    t1 = np.power(np.e, float(tau[banda]) / np.cos(np.deg2rad(float(self.mtl['SUN_AZIMUTH'])))) #FALTA COMPROBAR T1 Y T2 d['SUN_AZIMUTH']
                    t2 = np.power(np.e, float(tau[banda]))
                    DEN = np.cos(np.deg2rad(90 - float(self.mtl['SUN_ELEVATION']))) * essun[banda] * t1 * t2 # VALOR COMPROBADO! d['SUN_ELEVATION']

                    SR = np.divide(NUM, DEN)
                    SR = np.around(SR*10000)
                    SR = np.where(SR>10000, 0, SR)
                    SR = np.where(SR<0, 0, SR)

                    profile = src.meta
                    profile.update(dtype=rasterio.uint16)

                    outfile = os.path.join(path_rad, self.escena + '_gr2_' + banda + '.tif')
                    print(outfile)                

                    with rasterio.open(outfile, 'w', **profile) as dst:
                        dst.write(SR.astype(rasterio.uint16))

    
    
    def clean_rad(self):
        
        '''-----\n
        Este metodo elimina los archivos innecesarios de la carpeta rad y renombra Fmask llevandola a nor'''    
        
        
        path_rad = os.path.join(self.rad, self.escena)
        path_nor = os.path.join(self.nor, self.escena)
        os.makedirs(path_nor, exist_ok=True)

        for i in os.listdir(path_rad):
            
            if 'Mos' in i or 'rad' in i:
                if not 'Fmask4' in i:
                    os.remove(os.path.join(path_rad, i))
                else:
                    old = os.path.join(path_rad, i)
                    new = os.path.join(path_nor, self.escena + '_Fmask4.tif')
                    os.rename(old, new)
                    
                    
                    
    def normalize(self):
        
        '''-----\n
        Este metodo controla el flujo de la normalizacion, si no se llegan a obtener los coeficientes (R>0.85 y N_Pixeles >= 10,
        va pasando hacia el siguiente nivel, hasta que se logran obtener esos valores o hasta que se llega al ultimo paso)'''
        
        path_rad = os.path.join(self.rad, self.escena)
                
        bandasl8 = ['B2', 'B3', 'B4', 'B5', 'B6', 'B7']
        bandasl7 = ['B1', 'B2', 'B3', 'B4', 'B5', 'B7']
        
        if self.sat == 'L8':
            print('landsat 8\n')
            lstbandas = bandasl8
        else:
            print('landsat', self.sat, '\n')
            lstbandas = bandasl7
        
        #Vamos a pasar las bandas recortadas desde temp
        for i in os.listdir(path_rad):
                    
            if re.search('B[1-7].tif$', i):
                
                banda = os.path.join(path_rad, i)
                banda_num = i[-6:-4]
                
                print(banda, ' desde normalize')
                #Primera llamada a nor1
                self.iter = 1
                self.nor1(banda, self.noequilibrado)
                
                #Esto es un poco feo, pero funciona. Probar a hacerlo con una lista de funciones
                if banda_num not in self.parametrosnor.keys():
                    
                    self.iter += 1
                    print('Iteracion', self.iter)
                    self.nor1(banda, self.noequilibrado, coef = 2)
                    if banda_num not in self.parametrosnor.keys():
                        self.iter += 1
                        print('Iteracion', self.iter)
                        self.nor1(banda, self.equilibrado)
                        if banda_num not in self.parametrosnor.keys():
                            self.iter += 1
                            print('Iteracion', self.iter)
                            self.nor1(banda, self.equilibrado, coef = 2)
                            if banda_num not in self.parametrosnor.keys():
                                self.iter += 1
                                print('Iteracion', self.iter)
                                self.nor1(banda, self.noequilibrado, coef = 3)
                                if banda_num not in self.parametrosnor.keys():
                                    self.iter += 1
                                    print('Iteracion', self.iter)
                                    self.nor1(banda, self.equilibrado, coef = 30)
                                else:
                                    print('No se ha podido normalizar la banda ', banda_num)
                                    
            #Una vez acabados los bucles guardamos los coeficientes en un txt. Redundante pero asi hay 
            #que hacerlo porque quiere David
            path_nor = os.path.join(self.nor, self.escena)
            #os.makedirs(path_nor, exist_ok=True)
            arc = os.path.join(path_nor, 'coeficientes.txt')
            f = open(arc, 'w')
            for i in sorted(self.parametrosnor.items()):
                f.write(str(i)+'\n')
            f.close()  
            
            
                
    def nor1(self, banda, mascara, coef = 1):
        
        '''-----\n
        Este metodo busca obtiene los coeficientes necesarios para llevar a cabo la normalizacion,
        tanto en nor1 como en nor1bis'''

        print('comenzando nor1')
        
        #Ruta a las bandas usadas para normalizar
        '''path_b1 = os.path.join(self.data, '20020718l7etm202_34_gr2_B1.tif')
        path_b2 = os.path.join(self.data, '20020718l7etm202_34_gr2_B2.tif')
        path_b3 = os.path.join(self.data, '20020718l7etm202_34_gr2_B3.tif')
        path_b4 = os.path.join(self.data, '20020718l7etm202_34_gr2_B4.tif')
        path_b5 = os.path.join(self.data, '20020718l7etm202_34_gr2_B5.tif')
        path_b7 = os.path.join(self.data, '20020718l7etm202_34_gr2_B7.tif')'''
        
        
        path_b1 = os.path.join(self.data, '20020718l7etm202_34_mos_B1.tif')
        path_b2 = os.path.join(self.data, '20020718l7etm202_34_mos_B2.tif')
        path_b3 = os.path.join(self.data, '20020718l7etm202_34_mos_B3.tif')
        path_b4 = os.path.join(self.data, '20020718l7etm202_34_mos_B4.tif')
        path_b5 = os.path.join(self.data, '20020718l7etm202_34_mos_B5.tif')
        path_b7 = os.path.join(self.data, '20020718l7etm202_34_mos_B7.tif')
        
        dnorbandasl8 = {'B2': path_b1, 'B3': path_b2, 'B4': path_b3, 'B5': path_b4, 'B6': path_b5, 'B7': path_b7}
        dnorbandasl7 = {'B1': path_b1, 'B2': path_b2, 'B3': path_b3, 'B4': path_b4, 'B5': path_b5, 'B7': path_b7}
        
        if self.sat == 'L8':
            dnorbandas = dnorbandasl8
        else:
            dnorbandas = dnorbandasl7
            
        path_nor = os.path.join(self.nor, self.escena)
                    
        mask_nubes = os.path.join(path_nor, self.escena + '_Fmask4.tif')
        print('Mascara de nubes: ', mask_nubes)
        
        if mascara == self.noequilibrado:
            poly_inv_tipo = os.path.join(self.data, 'NoEquilibrada_mos.tif')
        else:
            poly_inv_tipo = os.path.join(self.data, 'Equilibrada_mos.tif')

        print('mascara: ', mascara)
                            
        with rasterio.open(mask_nubes) as nubes:
            CLOUD = nubes.read()
                
        #Abrimos el raster con los rois
        with rasterio.open(poly_inv_tipo) as pias:
            PIAS = pias.read()

        banda_num = banda[-6:-4]
        print(banda_num)
        if banda_num in dnorbandas.keys():
            with rasterio.open(banda) as current:
                CURRENT = current.read()
                print('Banda actual: ', banda, 'Shape:', CURRENT.shape)
            #Aqui con el diccionario nos aseguramos de que estamos comparando cada banda con su homologa del 20020718
            with rasterio.open(dnorbandas[banda_num]) as ref:
                REF = ref.read()
                print('Referencia: ', dnorbandas[banda_num], 'Shape:', REF.shape)
            
            #Ya tenemos todas las bandas de la imagen actual y de la imagen de referencia leidas como array
            REF2 = REF[((CURRENT != 0) & (PIAS != 0)) & ((CLOUD == 0) | (CLOUD == 1))]
            BANDA2 = CURRENT[((CURRENT != 0) & (PIAS != 0)) & ((CLOUD == 0) | (CLOUD == 1))]
            PIAS2 = PIAS[((CURRENT != 0) & (PIAS != 0)) & ((CLOUD == 0) | (CLOUD == 1))]
            
            #Realizamos la primera regresion
            First_slope, First_intercept, r_value, p_value, std_err = linregress(BANDA2,REF2)
            print ('\n++++++++++++++++++++++++++++++++++')
            print('slope: '+ str(First_slope), 'intercept:', First_intercept, 'r', r_value, 'N:', PIAS2.size)
            print ('++++++++++++++++++++++++++++++++++\n')
                        
            esperado = BANDA2 * First_slope + First_intercept
            residuo = REF2 - esperado
            #print('DESVIACION TÍPICA PRIMERA REGRESION:', std_err) COMO DE BUENO ES EL AJUSTE (SLOPE DAVID)
            print('RESIDUO STD:', residuo.std())
            print('RESIDUO STD_DDOF:', residuo.std(ddof=1))
            std = residuo.std() * coef
            print('STD:', std, 'COEF:', coef)
                        
            #Ahora calculamos el residuo para hacer la segunda regresion

            mask_current_PIA_NoData_STD = np.ma.masked_where(abs(residuo)>=std, BANDA2)
            mask_ref_PIA_NoData_STD = np.ma.masked_where(abs(residuo)>=std,REF2)
            mask_pias_PIA_NoData_STD = np.ma.masked_where(abs(residuo)>=std,PIAS2)

            current_PIA_NoData_STD = np.ma.compressed(mask_current_PIA_NoData_STD)
            ref_PIA_NoData_STD = np.ma.compressed(mask_ref_PIA_NoData_STD)
            pias_PIA_NoData_STD = np.ma.compressed(mask_pias_PIA_NoData_STD)
                       
            
            #Hemos enmascarado los resiudos, ahora calculamos la 2 regresion
            slope, intercept, r_value, p_value, std_err = linregress(current_PIA_NoData_STD,ref_PIA_NoData_STD)
            print ('\n++++++++++++++++++++++++++++++++++')
            print ('slope: '+ str(slope), 'intercept:', intercept, 'r', r_value, 'N:', len(ref_PIA_NoData_STD))
            print ('++++++++++++++++++++++++++++++++++\n')
            
            
            #Comprobamos el numero de pixeles por cada area pseudo invariante
            values = {}
            values_str = {1: 'Mar', 2: 'Embalses', 3: 'Pinar', 
                          4: 'Urbano-1', 5: 'Urbano-2', 6: 'Aeropuertos', 7: 'Arena', 8: 'Pastizales', 9: 'Mineria'}
            
            print('Vamos a sacar el count de cada zona (dict)')
            for i in range(1,8):

                mask_pia_= np.ma.masked_where(pias_PIA_NoData_STD != i, pias_PIA_NoData_STD)
                PIA = np.ma.compressed(mask_pia_)
                a = PIA.tolist()
                values[values_str[i]] = len(a)
                print('Values_dict:', values)
            
            #pasamos las claves de cada zona a string
            print(banda_num)
            #Generamos el raster de salida despues de aplicarle la ecuacion de regresion. Esto seria el nor2
            #Por aqui hay que ver como se soluciona
            if r_value > 0.85 and min(values.values()) >= 10:
                self.parametrosnor[banda_num]= {'Parametros':{'slope': slope, 'intercept': intercept, 'std': std,
                        'r': r_value, 'N': len(ref_PIA_NoData_STD), 'iter': self.iter}, 'Tipo_Area': values}
                
                print('parametros en nor1: ', self.parametrosnor)
                print('\comenzando nor2 con la banda:', banda[-6:-4], '\n')
                #Hemos calculado la regresion con las bandas recortadas con Rois_extent
                #Ahora vamos a pasar las bandas de rad (completas) para aplicar la ecuacion de regresion
                path_rad = os.path.join(self.rad, self.escena)
                print('Ruta Rad:', path_rad)
                for r in os.listdir(path_rad):
                    if banda[-6:-4] in r and r.endswith('.tif'):
                        print('banda:', r)
                        raster = os.path.join(path_rad, r)
                        print('La banda que se va a normalizar es:', raster)
                        self.nor2l8(raster, slope, intercept)# Aqui hay que cambiar para que llame a las bandas de rad
                        print('\nNormalizacion de ', banda_num, ' realizada.\n')
                 
                        fig = plt.figure(figsize=(15,10))
                        ax1 = fig.add_subplot(121)
                        ax2 = fig.add_subplot(122)
                        ax1.set_ylim((0, 10000))
                        ax1.set_xlim((0, 10000))
                        ax2.set_ylim((0, 10000))
                        ax2.set_xlim((0, 10000))

                        sns.regplot(BANDA2, REF2, color='g', ax=ax1,
                         line_kws={'color': 'grey', 'label':"y={0:.5f}x+{1:.5f}".format(First_slope,First_intercept)}).set_title('Regresion PIAs')

                        sns.regplot(current_PIA_NoData_STD, ref_PIA_NoData_STD, color='b', ax=ax2,
                         line_kws={'color': 'grey', 'label':"y={0:.5f}x+{1:.5f}".format(slope,intercept)}).set_title('Regresion PIAs-STD')

                        #Legend
                        ax1.legend()
                        ax2.legend()

                        title_ = os.path.split(banda)[1][:-4] + '. Iter: ' + str(self.iter)
                        fig.suptitle(title_, fontsize=15, weight='bold')
                        
                        plt.savefig(os.path.join(path_nor, os.path.split(banda)[1][:-4])+'.png')
                        plt.show()
                            
            else:
                pass
                                       
                    
    def nor2l8(self, banda, slope, intercept):
    
        '''-----\n
        Este metodo aplica la ecuacion de la recta de regresion a cada banda (siempre que los haya podido obtener)'''
        
        
        print('estamos en nor2!')
        path_rad = os.path.join(self.rad, self.escena)
        path_nor = os.path.join(self.nor, self.escena)
        
        banda_num = banda[-6:-4]
        outFile = os.path.join(path_nor, self.escena + '_grn2_' + banda_num + '.tif')
        print('Outfile', outFile)
        
        #Metemos la referencia para el NoData, vamos a coger la banda 5 en rad (... Y por que no?)
        for i in os.listdir(path_rad):
            
            if 'B5' in i:
                ref = os.path.join(path_rad, i)
        
        with rasterio.open(ref) as src:
            ref_rs = src.read()
        
        with rasterio.open(banda) as src:

            rs = src.read()
            rs = rs*slope+intercept

            nd = (ref_rs == 0)
            min_msk =  (rs < 0)             
            max_msk = (rs>=10001)

            rs[min_msk] = 0
            rs[max_msk] = 10000

            rs = np.around(rs)
            rs[nd] = 0

            profile = src.meta
            profile.update(dtype=rasterio.uint16)

            with rasterio.open(outFile, 'w', **profile) as dst:
             
                dst.write(rs.astype(rasterio.uint16))
    
    
            
    def run(self):
        
        self.fmask()
        self.del_mosaic()
        self.mosaic()
        self.projwin()
        self.get_kl_csw()
        self.get_radiance()
        self.corrad()
        self.clean_rad()
        self.normalize()
    
  
