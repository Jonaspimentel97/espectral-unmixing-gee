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
        return " "
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

Map.addLayer(unmixed, {}, 'Modelo Linear de Mistura Espectral')
Map.addLayer(ndwi, {'min': 0, 'max': 1, 'palette': ['white', 'blue']}, 'NDWI')
Map.addLayer(mndwi, {'min': 0, 'max': 1, 'palette': ['white', 'blue']}, 'MNDWI')
#Map.addLayer(normalized_difference, {'min': 0, 'max': 1, 'palette': ['white', 'red']}, 'Mixing Index')
#Map.addLayer(
    combined_img, 
    {'bands': ['B4', 'B3', 'B2'], 'min': 0.0, 'max': 0.4, 'gamma': 1.4}, 
    'Mosaico RGB', 
)
# Criar uma sidebar para o título e contextualização
with st.sidebar:
    # Título estilizado na barra lateral
    st.markdown(
        """
        <div style="
            text-align: center; 
            font-family: 'Arial', sans-serif; 
            font-size: 15px; 
            font-weight: bold; 
            color: white; 
            background: linear-gradient(to right, #4CAF50, #2E8B57); 
            padding: 10px; 
            border-radius: 8px;
            box-shadow: 2px 2px 8px rgba(0,0,0,0.2);">
            USO DA MISTURA ESPECTRAL COMO FORMA DE AVALIAÇÃO DOS ÍNDICES NDWI E MNDWI PARA O PANTANAL BRASILEIRO
        </div>
        """,
        unsafe_allow_html=True
    )

    # Contextualização
    st.markdown(
        """
        ## 🌎 Contextualização

        - **📡 Satélite:** Landsat 8 (Surface Reflectance)  m e
        - **📅 Período:** Úmido de 2020 

        ### 📊 Índices Espectrais
        - **NDWI:** Destaca corpos d'água abertos  
          - 🧮 Fórmula: *(NIR - SWIR) / (NIR + SWIR)*  
        - **MNDWI:** Melhora a identificação de corpos d'água  
          - 🧮 Fórmula: *(GREEN - SWIR) / (GREEN + SWIR)*  

        ### 🔎 Processamento no Google Earth Engine (GEE)
        - **15 cenas do Pantanal** (Bandas: 2, 3, 4, 5, 6 e 7)  
        - **Função:** `reduceRegion`  

        ### 🔬 Modelo de Mistura Espectral (MLME)
        - **Função:** `unmix`  
        - **Baseado em endmembers (assinaturas puras):**  
          - 🌱 Vegetação  
          - 🏜 Solo  
          - 💧 Água  

        """
    )

# Exibir o mapa ao lado direito
Map.to_streamlit(height=1000)

# Sidebar para contextualização e imagens 📊
with st.sidebar:
    # Título estilizado
    st.markdown(
        """
        <div style="
            text-align: center; 
            font-family: 'Arial', sans-serif; 
            font-size: 18px; 
            font-weight: bold; 
            color: white; 
            background: linear-gradient(to right, #1E90FF, #4682B4); 
            padding: 8px; 
            border-radius: 6px;
            box-shadow: 2px 2px 8px rgba(0,0,0,0.2);">
            🛰️ Comparação NDWI x MNDWI
        </div>
        """,
        unsafe_allow_html=True
    )

    # Contextualização 📊
    st.markdown(
        """
        - **Áreas analisadas**: MNDWI detectou mais água que o NDWI.    
        """
    )

    # Exibir imagem da comparação entre NDWI e MNDWI
    st.image(r"D:\mistrua\1.png", caption="NDWI e MNDWI do Pantanal", use_container_width=True)

    # Separador visual
    st.divider()

    # Título da próxima seção
    st.markdown(
        """
        <div style="
            text-align: center; 
            font-family: 'Arial', sans-serif; 
            font-size: 18px; 
            font-weight: bold; 
            color: white; 
            background: linear-gradient(to right, #1E90FF, #4682B4); 
            padding: 8px; 
            border-radius: 6px;
            box-shadow: 2px 2px 8px rgba(0,0,0,0.2);">
            🌊 Eficiência do MNDWI
        </div>
        """,
        unsafe_allow_html=True
    )

    # Explicação sobre o MNDWI
    st.markdown(
        """
        ### **🔬 Análise de Mistura Espectral**
        - Corpos d’água com até **35% de vegetação** → Melhor detectados pelo **MNDWI**.  
        - **Limiar de 75%** foi definido para classificar corpos d’água.  
        - **MNDWI se destaca** na identificação de água em regiões com alta mistura espectral.  
        """
    )

    # Exibir imagens adicionais
    st.image(r"D:\mistrua\2.png", caption="Percentual de Cada Componente com Base no Modelo de Fração.", use_container_width=True)
    st.image(r"D:\mistrua\3.png", caption="Comparação entre MNDWI (A), NDWI (B) e Imagem de Frações (C)", use_container_width=True)

