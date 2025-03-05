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
        credentials = service_account.Credentials.from_service_account_info(service_account_keys, scopes=oauth.SCOPES)
        
        # Inicializa o Google Earth Engine com as credenciais
        ee.Initialize(credentials)
        
          # Retorna sucesso após autenticação
        return ' '
    except Exception as e:
        # Exibe o erro se algo falhar
        st.error(f"Erro ao autenticar: {e}")
        return None
        
# Inicialize o GEE antes de qualquer outra operação
auth_status = get_auth()
st.write(auth_status)

# Configuração do Streamlit
st.title('Mistura Espectral')

# Inicializar o Earth Engine
ee.Authenticate()
ee.Initialize(project='gee1-444402')

# Carregar a geometria do Pantanal
pantanal = ee.FeatureCollection("users/jonaspimentel97/pantanal")

# Definir as regiões para solo, vegetação e água (substitua pelos seus próprios assets ou coleções)
bare = ee.FeatureCollection('users/jonaspimentel97/bare')
vegetation = ee.FeatureCollection('users/jonaspimentel97/vegetation')
water = ee.FeatureCollection('users/jonaspimentel97/water')

# Carregar as imagens Landsat
image1 = ee.Image('LANDSAT/LC08/C02/T1_TOA/LC08_226073_20200313')
image2 = ee.Image('LANDSAT/LC08/C02/T1_TOA/LC08_227074_20200116')
image3 = ee.Image('LANDSAT/LC08/C02/T1_TOA/LC08_226074_20200313')
image4 = ee.Image('LANDSAT/LC08/C02/T1_TOA/LC08_226072_20200313')
image5 = ee.Image('LANDSAT/LC08/C02/T1_TOA/LC08_225073_20200423')
image6 = ee.Image('LANDSAT/LC08/C02/T1_TOA/LC08_227071_20200421')
image7 = ee.Image('LANDSAT/LC08/C02/T1_TOA/LC08_227073_20200304')
image8 = ee.Image('LANDSAT/LC08/C02/T1_TOA/LC08_227072_20200116')
image9 = ee.Image('LANDSAT/LC08/C02/T1_TOA/LC08_226071_20200313')
image10 = ee.Image('LANDSAT/LC08/C02/T1_TOA/LC08_225072_20200423')
image11 = ee.Image('LANDSAT/LC08/C02/T1_TOA/LC08_225074_20200423')
image12 = ee.Image('LANDSAT/LC08/C02/T1_TOA/LC08_226075_20200125')
image13 = ee.Image('LANDSAT/LC08/C02/T1_TOA/LC08_228071_20200428')
image14 = ee.Image('LANDSAT/LC08/C02/T1_TOA/LC08_227075_20200421')
image15 = ee.Image('LANDSAT/LC08/C02/T1_TOA/LC08_228072_20200428')

# Criar a coleção de imagens e combinar
bands = ['B2', 'B3', 'B4', 'B5', 'B6', 'B7'];
combined_img = ee.ImageCollection([
    image1, image2, image3, image4, image5, image6, image7, image8, image9, image10, image11, image12, image13, image14, image15
]).mosaic().select(bands).clip(pantanal)

# Obter a média de cada banda para solo, vegetação e água
bareMean = combined_img.reduceRegion(
    reducer=ee.Reducer.mean(),
    geometry=bare,
    scale=30
).values()

vegMean = combined_img.reduceRegion(
    reducer=ee.Reducer.mean(),
    geometry=vegetation,
    scale=30
).values()

waterMean = combined_img.reduceRegion(
    reducer=ee.Reducer.mean(),
    geometry=water,
    scale=30
).values()


# Criar a lista de endmembers
endmembers = ee.List([bareMean, vegMean, waterMean])

# Aplicar a técnica de mistura espectral (unmix)
unmixed = combined_img.unmix(endmembers, sumToOne=True, nonNegative=True).rename(['bare', 'vegetation', 'water'])

# Selecionar as bandas de acordo com as bandas disponíveis
# NDWI: (B3 - B5) / (B3 + B5)
ndwi = combined_img.normalizedDifference(['B3', 'B5']).rename('NDWI')

# MNDWI: (B3 - B6) / (B3 + B6)
mndwi = combined_img.normalizedDifference(['B3', 'B6']).rename('MNDWI')


# Selecionar as bandas de acordo com as bandas disponíveis
# NDWI: (B3 - B5) / (B3 + B5)
ndwi = combined_img.normalizedDifference(['B3', 'B5']).rename('NDWI')

# MNDWI: (B3 - B6) / (B3 + B6)
mndwi = combined_img.normalizedDifference(['B3', 'B6']).rename('MNDWI')

# Calcular a variação entre as frações (quanto mais baixa a diferença, maior a mistura)
fraction_difference = (
    unmixed.select('water')
    .subtract(unmixed.select('vegetation')).abs()
    .add(unmixed.select('water').subtract(unmixed.select('bare')).abs())
    .add(unmixed.select('vegetation').subtract(unmixed.select('bare')).abs())
)

# Normalizar a variação (opcional para facilitar a visualização)
normalized_difference = fraction_difference.divide(3)


# Configurar o mapa com geemap
Map = geemap.Map()
Map.centerObject(pantanal, 7)

# Adicionar as camadas de endmembers (resultados da mistura)

Map.addLayer(unmixed, {}, 'Unmix Result')

# adiconar indice de mistura 

Map.addLayer(normalized_difference,{'min': 0, 'max': 1, 'palette': ['white', 'red']}, 'Mixing Index')

# Exibir o mapa no Streamlit
st.write("### Mapa Interativo")
Map.to_streamlit(height=600)


