import lightgbm as lgb
import pandas as pd
from datetime import datetime

print("Iniciando retreino do modelo LightGBM...")

# Carregue os dados (ajustar para o caminho real dos seus dados!)
df = pd.read_csv('data/dados_atualizados.csv')

# Separe features e alvo (exemplo, ajuste para o seu conjunto)
X = df.drop(columns=["target"])
y = df["target"]

# Re-treina o modelo
model = lgb.LGBMClassifier()
model.fit(X, y)

# Salva o modelo com timestamp
model_name = f"models/lightgbm_model_{datetime.today().strftime('%Y%m%d')}.txt"
model.booster_.save_model(model_name)
print(f"Modelo atualizado salvo em {model_name}")
