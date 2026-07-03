import os
import pandas as pd
from db import obter_conexao

# ==========================================
# CONFIGURAÇÕES DO USUÁRIO
# ==========================================

# 1. Caminho para a planilha (pode ser .xlsx, .xls ou .csv)
CAMINHO_PLANILHA = "C:/Users/liber/Documents/LISTA_DE_CONTATOS_ALEATORIOS/SULAMERICA.xlsx"

# 2. MAPEAMENTO DE COLUNAS (Planilha -> Banco de Dados)
# Altere o valor (lado direito) com o nome exato da coluna na sua planilha.
MAPEAMENTO_CLIENTES = {
    "nome": "NomeRazao",             # Coluna do nome
    "email1": "Email1",              # Coluna do email 1
    "email2": "Email2",              # Coluna do email 2 (Opcional - deixe vazio "" ou None se não existir)
    "email3": "Email3"               # Coluna do email 3 (Opcional - deixe vazio "" ou None se não existir)
}

def obter_valor(row, mapeamento, campo_bd, default_val=None):
    """Auxiliar para extrair o valor da planilha com base no mapeamento."""
    coluna_planilha = mapeamento.get(campo_bd)
    if coluna_planilha and coluna_planilha in row:
        val = row[coluna_planilha]
        if pd.isna(val):
            return default_val
        return str(val).strip()
    return default_val

def extrair_e_salvar():
    if not os.path.exists(CAMINHO_PLANILHA):
        print(f"Erro: O arquivo '{CAMINHO_PLANILHA}' não foi encontrado.")
        return

    print(f"Lendo a planilha: {CAMINHO_PLANILHA}...")
    try:
        if CAMINHO_PLANILHA.endswith('.csv'):
            df = pd.read_csv(CAMINHO_PLANILHA)
        else:
            df = pd.read_excel(CAMINHO_PLANILHA)
    except Exception as e:
        print(f"Erro ao ler o arquivo: {e}")
        return

    # Valida se as colunas configuradas existem no arquivo
    colunas_mapeadas = [col for col in MAPEAMENTO_CLIENTES.values() if col]
    colunas_faltantes = [col for col in colunas_mapeadas if col not in df.columns]
    if colunas_faltantes:
        print(f"\nAviso: Algumas colunas mapeadas não existem na planilha: {colunas_faltantes}")
        print("O script tentará prosseguir usando valores padrão ou gerados para elas.")

    # Conectar ao Banco de Dados selecionado
    print("\nConectando ao banco de dados...")
    try:
        conexao, placeholder, duplicado_excecao = obter_conexao()
        cursor = conexao.cursor()
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        print("Dica: Verifique as configurações no arquivo .env e se o banco de dados está ativo.")
        return

    # Garante que a coluna 'fonte' existe na tabela
    db_tipo = os.getenv("DB_TIPO", "sqlite").lower()
    try:
        if db_tipo == "mysql":
            cursor.execute("SHOW COLUMNS FROM clientes_lista_aleatoria LIKE 'fonte'")
            col_exists = cursor.fetchone() is not None
        else:
            cursor.execute("PRAGMA table_info(clientes_lista_aleatoria)")
            col_exists = 'fonte' in [row[1] for row in cursor.fetchall()]
            
        if not col_exists:
            print("Adicionando coluna 'fonte' na tabela 'clientes_lista_aleatoria'...")
            cursor.execute("ALTER TABLE clientes_lista_aleatoria ADD COLUMN fonte VARCHAR(255) NULL")
            conexao.commit()
    except Exception as e:
        print(f"Aviso ao verificar/adicionar coluna 'fonte': {e}")

    nome_planilha = os.path.basename(CAMINHO_PLANILHA)

    total_processados = 0
    total_inseridos = 0
    total_erros = 0

    print("\nIniciando processamento dos dados...")

    for index, row in df.iterrows():
        total_processados += 1
        
        # 1. Extrai dados do Cliente (somente nome e email)
        nome = obter_valor(row, MAPEAMENTO_CLIENTES, "nome", "Sem Nome")
        
        # Extrai múltiplos e-mails
        emails = []
        for campo in ["email1", "email2", "email3"]:
            email_val = obter_valor(row, MAPEAMENTO_CLIENTES, campo)
            if email_val:
                email_val = email_val.strip()
                if email_val and email_val not in emails:
                    emails.append(email_val)
        
        # Se não houver nenhum e-mail para esse cliente, descartamos a linha
        if not emails:
            print(f"Linha {index + 1}: Ignorado por ausência de e-mails.")
            total_erros += 1
            continue

        # 2. Verifica duplicidade e insere no banco para cada e-mail encontrado
        for email in emails:
            try:
                # Consulta para verificar se o e-mail já existe na tabela clientes_lista_aleatoria
                sql_check = f"SELECT 1 FROM clientes_lista_aleatoria WHERE email = {placeholder} LIMIT 1"
                cursor.execute(sql_check, (email,))
                if cursor.fetchone():
                    print(f"Linha {index + 1}: E-mail já existente ignorado ({email}).")
                    continue

                # SQL para inserir na tabela clientes_lista_aleatoria com a coluna fonte
                sql_inserir = f"""
                    INSERT INTO clientes_lista_aleatoria (nome, email, fonte)
                    VALUES ({placeholder}, {placeholder}, {placeholder})
                """
                valores = (nome, email, nome_planilha)
                cursor.execute(sql_inserir, valores)
                
                # Confirma as alterações do e-mail atual
                conexao.commit()
                total_inseridos += 1
                
            except duplicado_excecao as err:
                conexao.rollback()
                print(f"Linha {index + 1}: Ignorado por duplicidade no banco ({email}).")
            except Exception as e:
                conexao.rollback()
                print(f"Linha {index + 1}: Erro ao inserir e-mail {email}: {e}")
                total_erros += 1

    # Fecha conexões
    conexao.close()
    
    print("\n==========================================")
    print("Processamento concluído!")
    print(f"Total de linhas lidas: {total_processados}")
    print(f"Total de registros inseridos com sucesso: {total_inseridos}")
    print(f"Total de registros pulados/erros: {total_erros}")
    print("==========================================")


if __name__ == "__main__":
    extrair_e_salvar()
