import os
import pandas as pd
from db import obter_conexao

# ==============================================================================
# CONFIGURAÇÃO DAS PLANILHAS
# Adicione os caminhos de todas as planilhas que você usou para importar contatos.
# O script lerá cada uma delas e marcará a fonte no banco de dados.
# ==============================================================================
PLANILHAS = [
    "C:/Users/liber/Documents/LISTA_DE_CONTATOS_ALEATORIOS/AMIL.xlsx",
    "C:/Users/liber/Documents/LISTA_DE_CONTATOS_ALEATORIOS/BRADESCO.xlsx",
    "C:/Users/liber/Documents/LISTA_DE_CONTATOS_ALEATORIOS/SULAMERICA.xlsx",
    "C:/Users/liber/Documents/LISTA_DE_CONTATOS_ALEATORIOS/CNU.xlsx",
    "C:/Users/liber/Documents/LISTA_DE_CONTATOS_ALEATORIOS/LISTA_BRADESCO.xlsx",
    "C:/Users/liber/Documents/LISTA_DE_CONTATOS_ALEATORIOS/LISTA_DATA_CENTER.xlsx",
    "C:/Users/liber/Documents/LISTA_DE_CONTATOS_ALEATORIOS/LISTA_DIEGO_MONTEIRO.xlsx",
    "C:/Users/liber/Documents/LISTA_DE_CONTATOS_ALEATORIOS/SOCIO_PROP_COTIA_1303.xlsx",
    # Adicione outras planilhas aqui se necessário...
]

# Tabelas do banco de dados que você deseja atualizar
TABELAS = ["clientes_lista_aleatoria"]

def obter_tipo_db():
    """Detecta o tipo de banco de dados baseado nas variáveis de ambiente."""
    return os.getenv("DB_TIPO", "sqlite").lower()

def tabela_existe(cursor, tabela, db_tipo):
    """Verifica se uma tabela existe no banco de dados (suporta MySQL e SQLite)."""
    if db_tipo == "mysql":
        cursor.execute(f"SHOW TABLES LIKE '{tabela}'")
        return cursor.fetchone() is not None
    else:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tabela}'")
        return cursor.fetchone() is not None

def coluna_existe(cursor, tabela, coluna, db_tipo):
    """Verifica se uma coluna existe em uma tabela (suporta MySQL e SQLite)."""
    if db_tipo == "mysql":
        cursor.execute(f"SHOW COLUMNS FROM {tabela} LIKE '{coluna}'")
        return cursor.fetchone() is not None
    else:
        cursor.execute(f"PRAGMA table_info({tabela})")
        colunas = [row[1] for row in cursor.fetchall()]
        return coluna in colunas

def garantir_coluna_fonte(cursor, conexao, db_tipo):
    """Garante que a coluna 'fonte' existe nas tabelas especificadas."""
    for tabela in TABELAS:
        try:
            if not tabela_existe(cursor, tabela, db_tipo):
                continue
                
            if not coluna_existe(cursor, tabela, "fonte", db_tipo):
                print(f"Adicionando coluna 'fonte' na tabela '{tabela}'...")
                cursor.execute(f"ALTER TABLE {tabela} ADD COLUMN fonte VARCHAR(255) NULL")
                conexao.commit()
            else:
                print(f"A coluna 'fonte' já existe na tabela '{tabela}'.")
        except Exception as e:
            print(f"Erro ao verificar/adicionar coluna 'fonte' na tabela '{tabela}': {e}")

def obter_emails_banco(cursor, db_tipo):
    """Busca no banco de dados todos os e-mails e IDs onde a fonte ainda não está preenchida."""
    dados_banco = {} # Estrutura: {tabela: {email: [id1, id2, ...]}}
    for tabela in TABELAS:
        dados_banco[tabela] = {}
        try:
            if not tabela_existe(cursor, tabela, db_tipo):
                continue
                
            cursor.execute(f"SELECT id, email FROM {tabela} WHERE fonte IS NULL")
            rows = cursor.fetchall()
            for row_id, email in rows:
                if email:
                    email_limpo = str(email).strip().lower()
                    if email_limpo not in dados_banco[tabela]:
                        dados_banco[tabela][email_limpo] = []
                    dados_banco[tabela][email_limpo].append(row_id)
        except Exception as e:
            print(f"Erro ao buscar e-mails da tabela '{tabela}': {e}")
    return dados_banco

def extrair_emails_planilha(caminho):
    """Lê a planilha e descobre dinamicamente todas as colunas que possuem e-mails."""
    if not os.path.exists(caminho):
        print(f"Aviso: Planilha não encontrada no caminho '{caminho}'")
        return set()

    print(f"Lendo planilha: {caminho}...")
    try:
        if caminho.endswith('.csv'):
            df = pd.read_csv(caminho)
        else:
            df = pd.read_excel(caminho)
    except Exception as e:
        print(f"Erro ao ler planilha '{caminho}': {e}")
        return set()

    emails_encontrados = set()
    colunas_com_email = []

    # Descobre dinamicamente quais colunas contêm e-mails analisando amostras de dados
    for col in df.columns:
        amostra = df[col].dropna().astype(str)
        if len(amostra) > 0:
            contagem_at = amostra.str.contains('@').sum()
            # Se mais de 10% das células da coluna contêm '@', consideramos coluna de e-mail
            if contagem_at / len(amostra) > 0.1 or contagem_at >= 1:
                colunas_com_email.append(col)

    if colunas_com_email:
        print(f"  Colunas detectadas como e-mail: {colunas_com_email}")
        for col in colunas_com_email:
            for val in df[col].dropna():
                val_str = str(val).strip().lower()
                if '@' in val_str:
                    emails_encontrados.add(val_str)
    else:
        print("  Aviso: Nenhuma coluna de e-mail identificada nesta planilha.")

    return emails_encontrados

def executar_atualizacao():
    print("Conectando ao banco de dados...")
    try:
        conexao, placeholder, _ = obter_conexao()
        cursor = conexao.cursor()
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        return

    db_tipo = obter_tipo_db()
    print(f"Banco de dados detectado: {db_tipo.upper()}")

    # 1. Garante que a coluna 'fonte' existe nas tabelas do banco
    garantir_coluna_fonte(cursor, conexao, db_tipo)

    # 2. Carrega os e-mails sem fonte do banco de dados
    print("\nBuscando registros sem 'fonte' preenchida...")
    dados_banco = obter_emails_banco(cursor, db_tipo)
    
    for t in dados_banco:
        print(f"  Tabela '{t}': {len(dados_banco[t])} e-mails únicos aguardando atualização.")

    # 3. Processa cada planilha e atualiza o banco
    for caminho in PLANILHAS:
        nome_arquivo = os.path.basename(caminho)
        print(f"\n------------------------------------------")
        print(f"Processando arquivo: {nome_arquivo}")
        
        emails_planilha = extrair_emails_planilha(caminho)
        if not emails_planilha:
            continue
            
        print(f"  Encontrados {len(emails_planilha)} e-mails únicos na planilha.")
        
        for tabela in TABELAS:
            if tabela not in dados_banco or not dados_banco[tabela]:
                continue
                
            # Identifica quais IDs do banco correspondem aos e-mails da planilha atual
            ids_para_atualizar = []
            emails_encontrados_db = []
            
            for email in emails_planilha:
                if email in dados_banco[tabela]:
                    ids_para_atualizar.extend(dados_banco[tabela][email])
                    emails_encontrados_db.append(email)
                    
            if ids_para_atualizar:
                print(f"  Atualizando {len(ids_para_atualizar)} registros na tabela '{tabela}' com a fonte '{nome_arquivo}'...")
                try:
                    for row_id in ids_para_atualizar:
                        sql = f"UPDATE {tabela} SET fonte = {placeholder} WHERE id = {placeholder}"
                        cursor.execute(sql, (nome_arquivo, row_id))
                    conexao.commit()
                    
                    # Remove os e-mails encontrados do cache na memória para evitar reprocessamento
                    for email in emails_encontrados_db:
                        del dados_banco[tabela][email]
                except Exception as e:
                    conexao.rollback()
                    print(f"  Erro ao atualizar registros no banco: {e}")
            else:
                print(f"  Nenhuma correspondência encontrada para a tabela '{tabela}'.")

    # Fecha conexões
    conexao.close()
    print("\n==========================================")
    print("Atualização concluída com sucesso!")
    print("==========================================")

if __name__ == "__main__":
    executar_atualizacao()
