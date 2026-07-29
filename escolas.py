import requests
from bs4 import BeautifulSoup
import re

urls = [
    "https://educacao.marilia.sp.gov.br/-unidadesemef/",
    "https://demarilia.educacao.sp.gov.br/escolas-estaduais-2-0/"
]

escolas = []

for url in urls:

    print("Lendo:", url)

    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")

    texto = soup.get_text("\n")

    linhas = texto.split("\n")

    nome = None
    endereco = None

    for linha in linhas:

        linha = linha.strip()

        if not linha:
            continue

        # detectar escola
        if linha.startswith("EMEF") or linha.startswith("E.E"):
            nome = linha

        # detectar endereço
        if "Rua" in linha or "Av." in linha or "Avenida" in linha:

            endereco = linha

            if nome:
                escolas.append((nome, endereco))
                nome = None
                endereco = None


print("Total encontrado:", len(escolas))


with open("escolas_marilia.sql", "w", encoding="utf-8") as f:

    f.write("BEGIN TRANSACTION;\n")

    for nome, endereco in escolas:

        nome = nome.replace("'", "''")
        endereco = endereco.replace("'", "''")

        f.write(
            f"INSERT INTO escola (nome, endereco) VALUES ('{nome}', '{endereco}');\n"
        )

    f.write("COMMIT;\n")

print("Arquivo escolas_marilia.sql criado.")