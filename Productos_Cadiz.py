
import os, shutil, re, time, subprocess, pandas, rasterio, sys, math
import numpy as np


class Product(object):
    
    
    
    
    '''This class is made to generate NDVI, Flood Masks and Water Turbidity Masks from Landsat normalized scenes'''
    
        
    def __init__(self, ruta_nor):
        
        self.ruta_escena = ruta_nor
        self.escena = os.path.split(self.ruta_escena)[1]
        self.raiz = os.path.split(os.path.split(self.ruta_escena)[0])[0]
        #print(self.raiz)
        self.nor = os.path.join(self.raiz, os.path.join('nor', self.escena))
        #print(self.nor)
        self.ori = os.path.join(self.raiz, os.path.join('ori', self.escena))
        self.data = os.path.join(self.raiz, 'data')
        self.temp = os.path.join(self.raiz, 'temp')
        self.productos = os.path.join(self.raiz, 'pro')
        self.pro_esc = os.path.join(self.productos, self.escena)
        os.makedirs(self.pro_esc, exist_ok=True)
        
        if 'l7etm' in self.escena:
            self.sat = 'L7'
        elif 'l5tm' in self.ruta_escena:
            self.sat =  'L5'
        elif 'l4tm' in self.ruta_escena:
            self.sat =  'L5'
        else:
            print('No identifico el satelite')
        
        print(self.sat)
        
       
       

        for i in os.listdir(self.nor):
            if re.search('tif$', i):

                banda = i[-6:-4].lower()

                if banda == 'b1':
                    self.blue = os.path.join(self.nor, i)
                elif banda == 'b2':
                    self.green = os.path.join(self.nor, i)
                elif banda == 'b3':
                    self.red = os.path.join(self.nor, i)
                elif banda == 'b4':
                    self.nir = os.path.join(self.nor, i)
                elif banda == 'b5':
                    self.swir1 = os.path.join(self.nor, i)
                elif banda == 'b7':
                    self.swir2 = os.path.join(self.nor, i)
                elif banda == 'k4' or banda == 'sk':
                    self.fmask = os.path.join(self.nor, i)
        
        
        print('escena importada para productos correctamente')
        
        
        
    def ndvi(self):

        outfile = os.path.join(self.pro_esc, self.escena + '_nd2_ndvi_.tif')
        print(outfile)
        
        with rasterio.open(self.fmask) as fmask:
            FMASK = fmask.read()
        
        with rasterio.open(self.nir) as nir:
            NIR = nir.read()
            
        with rasterio.open(self.red) as red:
            RED = red.read()

        num = NIR.astype(float)-RED.astype(float)
        den = NIR+RED
        ndvi = np.true_divide(num, den)
        ndvi_ = np.where((FMASK == 2) | (FMASK == 4) | (FMASK == 255), 0, ndvi)
                
        profile = nir.meta
        profile.update(nodata=-9999)
        profile.update(dtype=rasterio.float32)

        with rasterio.open(outfile, 'w', **profile) as dst:
            dst.write(ndvi_.astype(rasterio.float32))
            
            
        print('NDVI Generado')
        
        
        
    def flood(self):
        
        
        print('amos en Flood!')
        
        waterMask = os.path.join(self.data, 'HP_FloodMask.tif')
        outfile = os.path.join(self.pro_esc, self.escena + '_nd_flood.tif')
        print(outfile)
        
        with rasterio.open(waterMask) as wmask:
            WMASK = wmask.read()
                        
        with rasterio.open(self.fmask) as fmask:
            FMASK = fmask.read()
            
        with rasterio.open(self.swir1) as swir1:
            SWIR1 = swir1.read()
            

        flood = np.where(((FMASK != 2) & (FMASK != 4)) & ((SWIR1 != 0) & (SWIR1 <= 1300)) & (WMASK > 0), 1, 0)
        flood_ = np.where((FMASK == 2) | (FMASK == 4) | (FMASK == 255), 2, flood)
        
        profile = swir1.meta
        profile.update(nodata=2)
        profile.update(dtype=rasterio.ubyte)

        with rasterio.open(outfile, 'w', **profile) as dst:
            dst.write(flood_.astype(rasterio.ubyte))
            
        
        print('Flood Mask Generada')
        
        return outfile
       
        
    def turbidity(self, flood):
        
        waterMask = os.path.join(self.data, 'water_mask_turb.tif')
        outfile = os.path.join(self.productos, self.escena + '_turbidity.tif')
        print(outfile)
        
        with rasterio.open(flood) as flood:
            FLOOD = flood.read()
        
        with rasterio.open(waterMask) as wmask:
            WMASK = wmask.read()
            
        with rasterio.open(self.blue) as blue:
            BLUE = blue.read()
            BLUE = np.where(BLUE == 0, 1, BLUE)
            BLUE = np.true_divide(BLUE, 10000)
                        
        with rasterio.open(self.green) as green:
            GREEN = green.read()
            GREEN = np.where(GREEN == 0, 1, GREEN)
            GREEN = np.true_divide(GREEN, 10000)
            GREEN_R = np.where((GREEN<0.1), 0.1, GREEN)
            GREEN_RECLASS = np.where((GREEN_R>=0.4), 0.4, GREEN_R)

        with rasterio.open(self.red) as red:
            RED = red.read()
            RED = np.where(RED == 0, 1, RED)
            RED = np.true_divide(RED, 10000)
            RED_RECLASS = np.where((RED>=0.2), 0.2, RED)
            
        with rasterio.open(self.nir) as nir:
            NIR = nir.read()
            NIR = np.where(NIR == 0, 1, NIR)
            NIR = np.true_divide(NIR, 10000)
            NIR_RECLASS = np.where((NIR>0.5), 0.5, NIR)
            
        with rasterio.open(self.swir1) as swir1:
            SWIR1 = swir1.read()
            SWIR1 = np.where(SWIR1 == 0, 1, SWIR1)
            SWIR1 = np.true_divide(SWIR1, 10000)
            SWIR_RECLASS = np.where((SWIR1>=0.09), 0.09, SWIR1)
        
        
        #Turbidez para la el rio
        rio = (-4.3 + (85.22 * GREEN_RECLASS) - (455.9 * np.power(GREEN_RECLASS,2)) \
            + (594.58 * np.power(GREEN_RECLASS,3)) + (32.3 * RED) - (15.36 * NIR_RECLASS)  \
            + (21 * np.power(NIR_RECLASS,2))) - 0.01        
        #RIO = np.power(math.e, rio)
        
        #Turbidez para la marisma        
        marisma = (4.1263574 + (18.8113118 * RED_RECLASS) - (32.2615219 * SWIR_RECLASS) \
        - 0.0114108989999999 * np.true_divide(BLUE, NIR)) - 0.01
        #MARISMA = np.power(math.e, marisma)
        
        
        TURBIDEZ = np.where(((FLOOD == 1) & (WMASK == 1)), marisma, 
                             np.where(((FLOOD == 1) & (WMASK == 2)), rio, 0))
        
        profile = swir1.meta
        profile.update(nodata=0)
        profile.update(dtype=rasterio.float32)
                             
        with rasterio.open(outfile, 'w', **profile) as dst:
            dst.write(TURBIDEZ.astype(rasterio.float32))
            
            
        print('Turbidity Mask Generada')
        
        
        
    def depth(self, flood, septb4, septwmask):

            outfile = os.path.join(self.productos, self.escena + '_depth_.tif')
            print(outfile)

            with rasterio.open(flood) as flood:
                FLOOD = flood.read()
                
            with rasterio.open(septb4) as septb4:
                SEPTB4 = septb4.read()
                SEPTB4 = np.true_divide(SEPTB4, 10000)
                SEPTB4 = np.where(SEPTB4 >= 0.830065359, 0.830065359, SEPTB4)
                SEPTB4 = SEPTB4 * 306
            
            with rasterio.open(septwmask) as septwater:
                SEPTWMASK = septwater.read()
                
            #Banda 1
            with rasterio.open(self.blue) as blue:
                BLUE = blue.read()
                BLUE = np.true_divide(BLUE, 10000)
                BLUE = np.where(BLUE >= 0.638190955, 0.638190955, BLUE)
                BLUE = BLUE * 398
                BLUE = np.where(BLUE >= 50, 50, BLUE)
                
            #Banda 2
            with rasterio.open(self.green) as green:
                GREEN = green.read()
                GREEN = np.true_divide(GREEN, 10000)
                GREEN = np.where(GREEN >= 0.638190955, 0.638190955, GREEN)
                GREEN = GREEN * 398
                #GREEN = np.where(GREEN == 0, 1, GREEN)
                #GREEN = np.true_divide(GREEN, 10000)
                #GREEN_R = np.where((GREEN<0.1), 0.1, GREEN)
                #GREEN_RECLASS = np.where((GREEN_R>=0.4), 0.4, GREEN_R)
            
            #Banda 4
            with rasterio.open(self.nir) as nir:
                NIR = nir.read()
                NIR = np.true_divide(NIR, 10000)
                NIR = np.where(NIR >= 0.830065359, 0.830065359, NIR)
                NIR = NIR * 306
                #NIR = np.where(NIR == 0, 1, NIR)
                #NIR = np.true_divide(NIR, 10000)
                #NIR_RECLASS = np.where((NIR>0.5), 0.5, NIR)
            
            #Banda 5
            with rasterio.open(self.swir1) as swir1:
                SWIR1 = swir1.read()
                SWIR1 = np.true_divide(SWIR1, 10000)
                SWIR1 = np.where(SWIR1 >= 0.601895735, 0.601895735, SWIR1)
                SWIR1 = SWIR1 * 422
                #SWIR1 = np.where(SWIR1 == 0, 1, SWIR1)
                #SWIR1 = np.true_divide(SWIR1, 10000)
                #SWIR_RECLASS = np.where((SWIR1>=0.09), 0.09, SWIR1)

            
            #Ratios
            RATIO_GREEN_NIR = np.true_divide(GREEN, NIR)
            RATIO_GREEN_NIR = np.where(RATIO_GREEN_NIR >= 2.5, 2.5, RATIO_GREEN_NIR)
            
            RATIO_NIR_SEPTNIR = np.true_divide(NIR, SEPTB4)           
            

            #Profundidad para la marisma        
            #depth = 5.293739862 - (0.038684824 * BLUE) - (0.007525455 * SEPTB4) + (0.02826867 * SWIR1) + \
                #(1.023724916 * RATIO_GREEN_NIR) - (1.041844944 * RATIO_NIR_SEPTNIR)
                
            a = ((-0.038684824 * BLUE) + 5.293739862) + (0.02826867 * SWIR1) + (-0.007525455 * SEPTB4) + \
                (1.023724916 * RATIO_GREEN_NIR) + (-1.041844944 * RATIO_NIR_SEPTNIR)
            
                
            DEPTH = np.exp(a) - 0.01
            
            #PASAR A NODATA EL AGUA DE SEPTIEMBRE!!!!
            DEPTH_ = np.where((FLOOD == 1) & (SEPTWMASK == 0), DEPTH, 0)


            profile = swir1.meta
            profile.update(nodata=0)
            profile.update(dtype=rasterio.float32)

            with rasterio.open(outfile, 'w', **profile) as dst:
                dst.write(DEPTH_.astype(rasterio.float32))


            print('Depth Mask Generada')
        
        
   
