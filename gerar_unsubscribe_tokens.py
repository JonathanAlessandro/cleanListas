import os
import hmac
import hashlib
from db import obter_conexao

TABELA = "clientes_lista_aleatoria"
COLUNA_TOKEN = "unsubscribe_token"
TAMANHO_TOKEN = 64
LOTE_COMMIT = 100


def obter_secret():
    secret = os.getenv("UNSUBSCRIBE_SECRET", "").strip()
    if not secret:
        raise ValueError(
            "UNSUBSCRIBE_SECRET não definido no .env. "
            "Adicione a variável antes de executar o script."
        )
    return secret.encode("utf-8")


def gerar_token(registro_id, email, secret):
    """Gera token determinístico de 64 chars (SHA-256 em hex)."""
    mensagem = f"{registro_id}:{email}".encode("utf-8")
    return hmac.new(secret, mensagem, hashlib.sha256).hexdigest()


def token_vazio(valor):
    return valor is None or str(valor).strip() == ""


def executar():
    print("Conectando ao banco de dados...")
    try:
        conexao, placeholder, _ = obter_conexao()
        cursor = conexao.cursor()
        secret = obter_secret()
    except Exception as e:
        print(f"Erro na inicialização: {e}")
        return

    db_tipo = os.getenv("DB_TIPO", "sqlite").lower()
    print(f"Banco detectado: {db_tipo.upper()}")

    # Busca só registros sem token
    sql_select = f"""
        SELECT id, email, {COLUNA_TOKEN}
        FROM {TABELA}
        WHERE {COLUNA_TOKEN} IS NULL OR TRIM({COLUNA_TOKEN}) = ''
    """
    cursor.execute(sql_select)
    registros = cursor.fetchall()

    total_encontrados = len(registros)
    total_atualizados = 0
    total_ignorados = 0
    total_erros = 0

    print(f"\nRegistros sem token: {total_encontrados}")

    sql_update = f"""
        UPDATE {TABELA}
        SET {COLUNA_TOKEN} = {placeholder}
        WHERE id = {placeholder}
          AND ({COLUNA_TOKEN} IS NULL OR TRIM({COLUNA_TOKEN}) = '')
    """

    for i, (registro_id, email, token_atual) in enumerate(registros, start=1):
        # Validação extra: se já tem token, não altera
        if not token_vazio(token_atual):
            total_ignorados += 1
            continue

        if not email or not str(email).strip():
            print(f"  ID {registro_id}: ignorado (sem e-mail)")
            total_ignorados += 1
            continue

        try:
            token = gerar_token(registro_id, str(email).strip().lower(), secret)
            cursor.execute(sql_update, (token, registro_id))

            if cursor.rowcount > 0:
                total_atualizados += 1
            else:
                # Outro processo pode ter preenchido entre o SELECT e o UPDATE
                total_ignorados += 1

            if i % LOTE_COMMIT == 0:
                conexao.commit()
                print(f"  Progresso: {i}/{total_encontrados} processados...")

        except Exception as e:
            conexao.rollback()
            print(f"  Erro no ID {registro_id}: {e}")
            total_erros += 1

    conexao.commit()
    conexao.close()

    print("\n==========================================")
    print("Geração de tokens concluída!")
    print(f"  Sem token (encontrados): {total_encontrados}")
    print(f"  Atualizados:             {total_atualizados}")
    print(f"  Ignorados:               {total_ignorados}")
    print(f"  Erros:                   {total_erros}")
    print("==========================================")


if __name__ == "__main__":
    executar()