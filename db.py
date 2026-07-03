import os
import sqlite3

# Tenta carregar variáveis usando python-dotenv se estiver disponível
try:
    # pyrefly: ignore [missing-import]
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Fallback robusto caso python-dotenv não esteja instalado
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()

def obter_conexao():
    """
    Estabelece e retorna a conexão com o banco de dados baseando-se no arquivo .env.
    
    Retorna:
        tuple: (conexao, placeholder, duplicado_excecao)
    """
    db_tipo = os.getenv("DB_TIPO", "sqlite").lower()

    if db_tipo == "mysql":
        import mysql.connector
        
        host = os.getenv("DB_HOST", "localhost")
        user = os.getenv("DB_USER", "root")
        password = os.getenv("DB_PASSWORD", "")
        database = os.getenv("DB_NAME", "")
        
        conexao = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        placeholder = "%s"
        duplicado_excecao = mysql.connector.errors.IntegrityError
    else:
        # SQLite por padrão
        sqlite_db_nome = os.getenv("DB_SQLITE_PATH", "liberty_db.db")
        conexao = sqlite3.connect(sqlite_db_nome)
        placeholder = "?"
        duplicado_excecao = sqlite3.IntegrityError
        
    return conexao, placeholder, duplicado_excecao
