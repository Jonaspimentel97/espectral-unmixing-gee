import ee
import geemap.foliumap as geemap
import streamlit as st
from google.oauth2 import service_account
from ee import oauth

# Função para autenticar no Google Earth Engine
def get_auth():
    try:
        # Acessa as credenciais a partir dos segredos configurados no Streamlit
        service_account_keys = st.secrets["service_account_json"]
        credentials = service_account.Credentials.from_service_account_info(
            service_account_keys, scopes=oauth.SCOPES
        )
        
        # Inicializa o Google Earth Engine com as credenciais
        ee.Initialize(credentials)
        return "Autenticação bem-sucedida!"
    except Exception as e:
        st.error(f"Erro ao autenticar: {e}")
        return None

# Inicializa o GEE antes de qualquer outra operação
auth_status = get_auth()
st.write(auth_status)

# Configuração do Streamlit
st.title('Mistura Espectral')

# Carregar a geometria do Pantanal
pantanal = ee.FeatureCollection("users/jonaspimentel97/pantanal")

# Definir as regiões para solo, vegetação e água
bare = ee.FeatureCollection('users/jonaspimentel97/bare')
vegetation = ee.FeatureCollection('users/jonaspimentel97/vegetation')
water = ee.FeatureCollection('users/jonaspimentel97/water')

# Carregar as imagens Landsat
image_ids = [
    "LANDSAT/LC08/C02/T1_TOA/LC08_226073_20200313",
    "LANDSAT/LC08/C02/T1_TOA/LC08_227074_20200116",
    "LANDSAT/LC08/C02/T1_TOA/LC08_226074_20200313",
    "LANDSAT/LC08/C02/T1_TOA/LC08_226072_20200313",
    "LANDSAT/LC08/C02/T1_TOA/LC08_225073_20200423",
    "LANDSAT/LC08/C02/T1_TOA/LC08_227071_20200421",
    "LANDSAT/LC08/C02/T1_TOA/LC08_227073_20200304",
    "LANDSAT/LC08/C02/T1_TOA/LC08_227072_20200116",
    "LANDSAT/LC08/C02/T1_TOA/LC08_226071_20200313",
    "LANDSAT/LC08/C02/T1_TOA/LC08_225072_20200423",
    "LANDSAT/LC08/C02/T1_TOA/LC08_225074_20200423",
    "LANDSAT/LC08/C02/T1_TOA/LC08_226075_20200125",
    "LANDSAT/LC08/C02/T1_TOA/LC08_228071_20200428",
    "LANDSAT/LC08/C02/T1_TOA/LC08_227075_20200421",
    "LANDSAT/LC08/C02/T1_TOA/LC08_228072_20200428",
]

bands = ['B2', 'B3', 'B4', 'B5', 'B6', 'B7']
combined_img = ee.ImageCollection(image_ids).mosaic().select(bands).clip(pantanal)

# Obter a média de cada banda para solo, vegetação e água
bareMean = combined_img.reduceRegion(ee.Reducer.mean(), bare, 30).values()
vegMean = combined_img.reduceRegion(ee.Reducer.mean(), vegetation, 30).values()
waterMean = combined_img.reduceRegion(ee.Reducer.mean(), water, 30).values()

# Criar a lista de endmembers
endmembers = ee.List([bareMean, vegMean, waterMean])

# Aplicar a técnica de mistura espectral
unmixed = combined_img.unmix(endmembers, sumToOne=True, nonNegative=True).rename(['bare', 'vegetation', 'water'])

# Calcular NDWI e MNDWI
ndwi = combined_img.normalizedDifference(['B3', 'B5']).rename('NDWI')
mndwi = combined_img.normalizedDifference(['B3', 'B6']).rename('MNDWI')

# Calcular a variação entre as frações
fraction_difference = (
    unmixed.select('water')
    .subtract(unmixed.select('vegetation')).abs()
    .add(unmixed.select('water').subtract(unmixed.select('bare')).abs())
    .add(unmixed.select('vegetation').subtract(unmixed.select('bare')).abs())
)
normalized_difference = fraction_difference.divide(3)

# Configurar o mapa
Map = geemap.Map()
Map.centerObject(pantanal, 7)

# Adicionar camadas ao mapa
Map.addLayer(water, {}, 'Water', False)
Map.addLayer(bare, {}, 'Bare', False)
Map.addLayer(vegetation, {}, 'Vegetation', False)
Map.addLayer(unmixed.select('bare'), {'min': 0, 'max': 1, 'palette': ['white', 'brown']}, 'Bare Soil', False)
Map.addLayer(unmixed.select('vegetation'), {'min': 0, 'max': 1, 'palette': ['white', 'green']}, 'Vegetation', False)
Map.addLayer(unmixed.select('water'), {'min': 0, 'max': 1, 'palette': ['white', 'blue']}, 'Water', False)
Map.addLayer(unmixed, {}, 'Unmix Result')
Map.addLayer(ndwi, {'min': 0, 'max': 1, 'palette': ['white', 'blue']}, 'NDWI')
Map.addLayer(mndwi, {'min': 0, 'max': 1, 'palette': ['white', 'blue']}, 'MNDWI')
Map.addLayer(normalized_difference, {'min': 0, 'max': 1, 'palette': ['white', 'red']}, 'Mixing Index')
Map.addLayer(
    combined_img, 
    {'bands': ['B4', 'B3', 'B2'], 'min': 0.0, 'max': 0.4, 'gamma': 1.4}, 
    'RGB Image', False
)

# Exibir o mapa no Streamlit
st.write("### Mapa Interativo")
Map.to_streamlit(height=600)
