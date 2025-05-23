## Instalação de bibliotecas
%pip install gremlinpython requests networkx pandas

# 1. Extração de triplas SPO com LLM via API (ex: Ollama, SageMaker, etc.)
import os
import requests
import json

api_base = "http://<SEU_ENDPOINT>:11434/v1"  # Ajuste para seu endpoint LLM
api_key = os.getenv("AWS_LLM_API_KEY") or "qualquer_string"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

texto = """Arroz Tio João é um alimento da categoria grãos.
Feijão Carioca Camil também pertence à categoria grãos.
Ambos são utilizados em pratos do dia a dia e são vendidos em embalagens de 1kg.
Leite Integral Italac é um produto da categoria laticínios, geralmente consumido no café da manhã.
Arroz Tio João combina bem com Feijão Carioca Camil."""

prompt = f"""
Extraia triplas do tipo sujeito-predicado-objeto em formato JSON.
Use minúsculas. Cada item deve conter 'subject', 'predicate', 'object'.
Texto:
{texto}
"""

payload = {
    "model": "llama3",  # Ajuste conforme o modelo disponível
    "messages": [
        {"role": "system", "content": "Você é um extrator de conhecimento estruturado."},
        {"role": "user", "content": prompt}
    ],
    "temperature": 0.0
}

res = requests.post(f"{api_base}/chat/completions", headers=headers, json=payload)
triples = json.loads(res.json()['choices'][0]['message']['content'])

# 2. Conexão com Amazon Neptune
from gremlin_python.driver import client, serializer

neptune_endpoint = "wss://<ENDPOINT_NEPTUNE>:8182/gremlin"
gclient = client.Client(neptune_endpoint, 'g',
    username="",
    password="",
    message_serializer=serializer.GraphSONSerializersV2d0()
)

# 3. Função para adicionar vértices e arestas ao grafo
def add_edge(subject, predicate, obj):
    query = f"""
    g.V().has('name', '{subject}').fold().
      coalesce(unfold(), addV('produto').property('name', '{subject}')).
    V().has('name', '{obj}').fold().
      coalesce(unfold(), addV('produto').property('name', '{obj}')).
    addE('{predicate}').
      from(V().has('name', '{subject}')).
      to(V().has('name', '{obj}'))
    """
    gclient.submit(query)

# 4. Inserção das triplas no Neptune
for t in triples:
    try:
        add_edge(t["subject"], t["predicate"], t["object"])
    except Exception as e:
        print(f"Erro ao inserir {t}: {e}")

# 5. Visualização das triplas extraídas
import pandas as pd
edges = [(t["subject"], t["predicate"], t["object"]) for t in triples]
df = pd.DataFrame(edges, columns=["De", "Relação", "Para"])
display(df)

# 6. Visualização com NetworkX (opcional)
import networkx as nx
import matplotlib.pyplot as plt

G = nx.DiGraph()
for t in triples:
    G.add_edge(t["subject"], t["object"], label=t["predicate"])

plt.figure(figsize=(12, 8))
pos = nx.spring_layout(G, seed=42)
nx.draw(G, pos, with_labels=True, node_color="lightblue", edge_color="gray", node_size=2000, font_size=10)
nx.draw_networkx_edge_labels(G, pos, edge_labels={(u, v): d["label"] for u, v, d in G.edges(data=True)})

plt.title("Grafo de Produtos do Supermercado")
plt.show()
