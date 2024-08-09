from funciones.funciones import *
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw
import random
import json
import os

#uvicorn V2createGeoserver:app --reload
#pm2 start "uvicorn createGeoserver:app --host 0.0.0.0" --name api
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/mapas/{mapas_id}")
async def read_user(mapas_id: int):       
    sqlPoligono = f"SELECT mapas_poligono.mapas_id, mapas_poligono.poligono_id, mapas_poligono.nombre, mapas_poligono.estilo, mapas_poligono.borde,poligono.ruta_archivo FROM public.mapas_poligono inner join poligono on mapas_poligono.poligono_id = poligono.id WHERE mapas_poligono.mapas_id = {mapas_id}"
    sqlLinea = f"SELECT mapas_linea.mapas_id, mapas_linea.linea_id, mapas_linea.nombre, mapas_linea.estilo, mapas_linea.borde,linea.ruta_archivo FROM public.mapas_linea inner join linea on mapas_linea.linea_id = linea.id WHERE mapas_linea.mapas_id = {mapas_id}"
    sqlPunto = f"SELECT mapas_punto.mapas_id, mapas_punto.punto_id, mapas_punto.nombre, mapas_punto.estilo, mapas_punto.borde,punto.ruta_archivo FROM public.mapas_punto inner join punto on mapas_punto.punto_id = punto.id WHERE mapas_punto.mapas_id = {mapas_id}"
    try:
        cursor = connectBF()
        cursor.execute(f"{sqlPoligono} UNION {sqlLinea} UNION {sqlPunto};")
        resultados = cursor.fetchall()
        resultado_json = []
        for row in resultados:
            resultado_json.append({
                'mapas_id': row[0],
                'nombre': row[2],
                'estilo': row[3],
                'borde': row[4],
                'ruta_archivo': row[5]
            })
        return resultado_json    
    except Exception as err:
        return f"Unexpected {err=}, {type(err)=}"

@app.get("/cargaCapas/{file_Name}/{tipo}")
async def cargaCapas(file_Name : str, tipo:str):
    
    ruta_archivo = f"/Capas/{file_Name}.geojson"
    
    try:
        cursor = cursor = connectBF()
        if tipo == "Poligono":
            query = f"""INSERT INTO poligono (nombre, ruta_archivo,tipo) values (%s, %s,'Poligono')"""
        elif tipo == "Linea":
            query = f"""INSERT INTO linea (nombre, ruta_archivo,tipo) values (%s, %s,'Linea')"""
        elif tipo == "Punto":
            query = f"""INSERT INTO punto (nombre, ruta_archivo,tipo) values (%s, %s,'Punto')"""
        else:
            return "No se ingresó una geometría válida"

        cursor.execute(query, (file_Name, ruta_archivo))
        cursor.close()
        return "Se guardo exitosamente"
    except Exception as err:
        return f"Unexpected {err=}, {type(err)=}"
    

@app.get("/dataJSON/{capa}")
def get_json(capa:str):
    try:
        JSON = f"/var/www/visor.inn.com.co/public_html/Capas/{capa}.geojson"
        #JSON = f"C:/xampp/htdocs/Geoportal2/js/visor/{capa}.geojson"
        with open(JSON, 'r') as JSONOpen:
            exJSON = json.load(JSONOpen)
        return exJSON
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
@app.get("/estiloCategoria/{capa}")
def getStyle(capa:str):
    try:
        JSON = f"/var/www/visor.inn.com.co/public_html/Capas/{capa}.geojson"
        #JSON = f"C:/xampp/htdocs/Geoportal2/Capas/{capa}.geojson"
        with open(JSON, 'r') as JSONOpen:
            exJSON = json.load(JSONOpen)
            categorias = []
            for i in exJSON['features']:
                categorias.append(i['properties'])

        return categorias
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/estilos/{nombreArchivo}/{idCapaMapa}/{id}/{tipo}")
def getStyle(nombreArchivo:str, idCapaMapa:str, id:str, tipo:str):
    
    rutaSLD = f"/var/www/visor.inn.com.co/public_html/Estilos/{nombreArchivo}"
    #rutaSLD =f"C:/Users/Juan Pablo/Downloads/aptitud_arrozsecano_dic2019/Estilos/{nombreArchivo}"
    rutaLeyenda = f"../../Leyendas/{id}_{idCapaMapa}.png"
    
    senJavaScript = ""
    try:
        # Abrir y leer el contenido del archivo XML
        with open(rutaSLD, "r") as file:
            sld_content = file.read()

        # Analizar el contenido del archivo XML
        root = ET.fromstring(sld_content)    
        namespace = {'se': 'http://www.opengis.net/se', 'ogc': 'http://www.opengis.net/ogc'}

        feature =root.find('.//ogc:PropertyName', namespace)
        values = root.findall('.//se:Description/se:Title', namespace)
        fills = root.findall('.//se:PolygonSymbolizer/se:Fill/se:SvgParameter[@name="fill"]', namespace)

        #SE DECLARAN DOS ARREGLOS VACÍOS QUE CONTIENEN LOS VALORES DE LOS COLORES Y LOS VALORES DE CADA COLOR
        colores = []
        valores = []

        if (feature is None) or (values is None):
            colores.append(fills[0].text)
            valores.append("Single Symbol")
            
            senJavaScript = f'''var nombre = feature.get('NA'); 
                    switch (nombre) 
                    {{case 'Single Symbol':
                        color = '#FF0000';
                        break;
                    default:
                        color = '{fills[0].text}'; // Gris por defecto
                    }}'''
            crearLeyenda(colores, valores, f"{id}_{idCapaMapa}")
        else:
            senJavaScript = f'''var nombre = feature.get('{feature.text}'); 
                        switch (nombre) {{'''
        
            for fill, value in zip(fills, values):
                #AÑADE LOS VALORES DE CADA COLOR Y EL COLOR AL ARRAY CORRESPONDIENTE
                colores.append(fill.text)
                valores.append(value.text)
                
                senJavaScript = senJavaScript + f'''case '{value.text}':
                        color = '{fill.text}';
                        break;'''
            
            senJavaScript = senJavaScript+ '''default:
                        color = '#FF0000'; // Gris por defecto
                }
                '''
            crearLeyenda(colores, valores, f"{id}_{idCapaMapa}")
            
        cursor = cursor = connectBF()
        if tipo == "Poligono":
            query = f"""UPDATE mapas_poligono SET estilo = %s, borde = %s  WHERE mapas_id = %s AND poligono_id = %s"""
        elif tipo == "Linea":
            query = f"""UPDATE mapas_linea SET estilo = %s, borde = %s WHERE mapas_id = %s AND linea_id = %s"""
        elif tipo == "Punto":
            query = f"""UPDATE mapas_punto SET estilo = %s, borde = %s WHERE mapas_id = %s AND punto_id = %s"""
        else:
            return "No se ingresó una geometría válida"

        cursor.execute(query, (senJavaScript, rutaLeyenda, id,idCapaMapa))
        cursor.close()

        os.remove(rutaSLD)

        return "Se guardó correctamente"
    except Exception as err:
        print(f"Unexpected {err=}, {type(err)=}")


@app.get("/crearEstilo/{id}/{id_capa}/{nombre}/{tipo}")
def crearEstilo(id:str, id_capa:str, nombre:str, tipo:str):
    try:
        colors = ['233D4D','FE7F2D','FCCA46','A1C181','619B8A','2191FB','BA274A','841C26','B2ECE1','8CDEDC']
        
        estilo = f'''var nombre = feature.get('NA');
                    switch (nombre) {{
                    case 'Single Symbol':
                        color = '#FF0000';
                        break;
                    default:
                        color = '#{colors[random.randint(0, len(colors))]}'; // Gris por defecto
            }}
        '''
                
        cursor = cursor = connectBF()
        if tipo == "Poligono":
            query = f""" INSERT INTO mapas_poligono (mapas_id, poligono_id, nombre, estilo, borde) VALUES (%s, %s, %s, %s, '#000000')"""
        elif tipo == "Linea":
            query = f""" INSERT INTO mapas_linea (mapas_id, linea_id, nombre, estilo, borde) VALUES (%s, %s, %s, %s, '#000000')"""
        elif tipo == "Punto":
            query = f""" INSERT INTO mapas_punto (mapas_id, punto_id, nombre, estilo, borde) VALUES (%s, %s, %s, %s, '#000000')"""
        else:
            return "No se ingresó una geometría válida"
        
        cursor.execute(query,(id, id_capa, nombre, estilo))
        cursor.close()
        return estilo
    except Exception as err:
        print(f"Unexpected {err=}, {type(err)=}")
        
def crearLeyenda(fills, values, nameLayer):
    img = Image.new('RGBA', (150, 150), color=(255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    positionText = 5
    vertical_increment = 30
    for fill, value in zip(fills,values):
        d.rectangle([10, positionText, 30, positionText + 20], fill=fill)
        d.text((40, positionText), value, fill=(0, 0, 0))
        positionText += vertical_increment
    img.save(f'/var/www/visor.inn.com.co/public_html/Leyendas/{nameLayer}.png')