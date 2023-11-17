# Import the library
from fastapi import FastAPI
from geo.Geoserver import Geoserver
import psycopg2

from typing import List
from pydantic import BaseModel
from sqlalchemy import create_engine, MetaData, Table, select, union_all
from databases import Database

DATABASE_URL = "postgresql://postgres:admin@localhost:5432/geoportal"

engine = create_engine(DATABASE_URL)
metadata = MetaData()
mapas_poligono = Table("mapas_poligono", metadata, autoload_with=engine)
mapas_linea = Table("mapas_linea", metadata, autoload_with=engine)
mapas_punto = Table("mapas_punto", metadata, autoload_with=engine)

database = Database(DATABASE_URL)



#uvicorn createGeoserver:app --reload
app = FastAPI()
   
#FUNCION QUE EJECUTA LA ACCION PARA CARGAR LAS CAPAS EN GEOSERVER, Y ADEMAS ADICIONA EN LA BASE DE DATOS LA INFORMACION CORRESPONDIENTE A LA CAPA
#se recomienda no dejar espacios en los nombres tanto del archivo como del nombre en el formulario
@app.get("/{store_name}/{file_Name}/{tipo}")
def loadLayers(store_name: str, file_Name : str, tipo:str):
    try:
        #Conexión a la base de datos
        connection = psycopg2.connect(
            host = "localhost",
            user = "postgres",
            password = "admin",
            database = "geoportal",
            port = "5432" 
        )
        connection.autocommit = True        
        
        #Insercion de datos a la tabla capas
        cursor = connection.cursor()
        if tipo == "Poligono":
            query = f"""INSERT INTO poligono (nombre, ruta_archivo,tipo) values (%s, %s,'Poligono')"""
        elif tipo == "Linea":
            query = f"""INSERT INTO linea (nombre, ruta_archivo,tipo) values (%s, %s,'Linea')"""
        else:
            query = f"""INSERT INTO punto (nombre, ruta_archivo,tipo) values (%s, %s,'Punto')"""
            
        cursor.execute(query, (store_name, file_Name))
        cursor.close()
        
        # Initialize the library
        geo = Geoserver('http://127.0.0.1:8080/geoserver', username='admin', password='geoserver')
        # Crear Espacio de trabajo
        #geo.create_workspace(workspace='demo1')
        ruta = r"C:/xampp/htdocs/Geoportal/python/"+file_Name
        #NOTA: El store es el nombre del almacen
        #Cargar la capa .shp NOTA:Los archivos que se suben deben estar comprimidos en .ZIP
        geo.create_shp_datastore(path=ruta, store_name={store_name}, workspace='geoportal')

        return "Se guardo exitosamente"
    except Exception as err:
        return f"Unexpected {err=}, {type(err)=}"



@app.get("/style/{file_Name}")
def loadStyles(file_Name : str):
    geo = Geoserver('http://127.0.0.1:8080/geoserver', username='admin', password='geoserver')
    
    ruta = r"C:/xampp/htdocs/Geoportal/python/"+file_Name
    nombre = file_Name.split(".")
    
    geo.delete_style(style_name=nombre[0], workspace='geoportal')
    
    geo.upload_style(path=ruta,workspace='geoportal')
    geo.publish_style(layer_name=nombre[0], style_name=nombre[0], workspace='geoportal')


#------------------------------------------------------------
#FUNCIONES PARA TRAER LA INFORMACION DE LAS CAPAS EN EL VISOR
class UserIn(BaseModel):
    nombre: str
    estilo: str
    borde: str
    #url: str

class UserOut(UserIn):
    mapas_id: int

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()
    
    
@app.get("/mapas/{mapas_id}", response_model=List[UserOut])
async def read_user(mapas_id: int):
    query = mapas_poligono.select().where(mapas_poligono.c.mapas_id == mapas_id)
    query2 = mapas_linea.select().where(mapas_linea.c.mapas_id == mapas_id)
    query3 = mapas_punto.select().where(mapas_punto.c.mapas_id == mapas_id)
    final_query = union_all(query,query2,query3)

    table = await database.fetch_all(final_query)
    return table
