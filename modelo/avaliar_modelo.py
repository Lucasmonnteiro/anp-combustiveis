"""Avaliacao do modelo de previsao do preco de venda (R$/litro).

Compara a arvore de decisao com uma regua simples (media por UF e produto)
em tres cenarios:
  1. divisao aleatoria (80/20), como e comum em exemplos de aula;
  2. divisao temporal (treino jan-mar, teste abr) usando o mes como entrada;
  3. divisao temporal sem o mes como entrada.

O cenario temporal e o mais honesto: o modelo e testado em um mes que ele
nunca viu, como aconteceria se fosse usado para estimar precos futuros.

Uso:
    python modelo/avaliar_modelo.py dados/Tabela_Master_Final.csv
"""
import sys

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OrdinalEncoder
from sklearn.tree import DecisionTreeRegressor

COM_MES = ["produto", "uf", "municipio", "mes", "bandeira"]
SEM_MES = ["produto", "uf", "municipio", "bandeira"]
ALVO = "valor_venda"


def carregar(caminho):
    df = pd.read_csv(caminho, sep=";", dtype=str)
    df[ALVO] = pd.to_numeric(df[ALVO].str.replace(",", "."), errors="coerce")
    df["data"] = pd.to_datetime(df["data_coleta"], format="%d/%m/%Y")
    df["mes"] = df["data"].dt.month.astype(str)
    return df.dropna(subset=[ALVO])


def metricas(y, p):
    return {
        "MAE": mean_absolute_error(y, p),
        "RMSE": float(np.sqrt(mean_squared_error(y, p))),
        "R2": r2_score(y, p),
    }


def regua_media(treino, teste):
    """Preve a media de UF + produto vista no treino (ou a media de produto)."""
    m_uf = treino.groupby(["uf", "produto"])[ALVO].mean()
    m_prod = treino.groupby("produto")[ALVO].mean()
    chave = list(zip(teste["uf"], teste["produto"]))
    p = pd.Series(chave, index=teste.index).map(m_uf)
    return p.fillna(teste["produto"].map(m_prod)).to_numpy()


def arvore(treino, teste, features):
    enc = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    xtr = enc.fit_transform(treino[features])
    xte = enc.transform(teste[features])
    modelo = DecisionTreeRegressor(random_state=42)
    modelo.fit(xtr, treino[ALVO])
    return modelo.predict(xtr), modelo.predict(xte)


def avaliar(nome, treino, teste, features):
    p_tr, p_te = arvore(treino, teste, features)
    linhas = [
        ("Arvore - dados de treino", metricas(treino[ALVO], p_tr)),
        ("Arvore - dados de teste", metricas(teste[ALVO], p_te)),
        ("Regua (media UF+produto) - teste", metricas(teste[ALVO], regua_media(treino, teste))),
    ]
    print(f"\n== {nome} (treino: {len(treino):,} | teste: {len(teste):,}) ==")
    for rotulo, m in linhas:
        print(f"{rotulo:<36} MAE R$ {m['MAE']:.3f} | RMSE R$ {m['RMSE']:.3f} | R2 {m['R2']:.3f}")


def main():
    df = carregar(sys.argv[1] if len(sys.argv) > 1 else "dados/Tabela_Master_Final.csv")
    treino, teste = train_test_split(df, test_size=0.2, random_state=42)
    avaliar("1. Divisao aleatoria 80/20", treino, teste, COM_MES)
    jan_mar, abril = df[df["data"].dt.month <= 3], df[df["data"].dt.month == 4]
    avaliar("2. Temporal jan-mar -> abr, com mes", jan_mar, abril, COM_MES)
    avaliar("3. Temporal jan-mar -> abr, sem mes", jan_mar, abril, SEM_MES)


if __name__ == "__main__":
    main()
