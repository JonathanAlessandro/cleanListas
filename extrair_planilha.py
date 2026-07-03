import os
import pandas as pd
from db import obter_conexao

# ==========================================
# CONFIGURAÇÕES DO USUÁRIO
# ==========================================

# 1. Caminho para a planilha (pode ser .xlsx, .xls ou .csv)
CAMINHO_PLANILHA = "C:/Users/liber/Documents/LISTA_DE_CONTATOS_ALEATORIOS/AMIL.xlsx"


# 3. MAPEAMENTO DE COLUNAS (Planilha -> Banco de Dados)
# Altere o valor (lado direito) com o nome exato da coluna na sua planilha.
# Se a planilha não possuir o campo, você pode deixar None e ajustar o valor padrão abaixo.

MAPEAMENTO_CLIENTES = {
    "nome": "NomeRazao",             # Coluna do nome
    "email": "DSEMAIL",           # Coluna do email (NOT NULL / UNIQUE)
    "tipo_documento": "",         # Coluna do tipo de documento ('CPF' ou 'CNPJ')
    "documento": "CPFCNPJ",       # Coluna do número do documento (NOT NULL / UNIQUE)
    "contrato": "NOMEPLANO",      # Coluna do contrato
    "telefone": "FONE2",          # Coluna do telefone
    "data_nascimento": "DataNascAbertura",
    "status": "status"            # Coluna do status ('ATIVO', 'INATIVO', 'BLOQUEADO')
}

MAPEAMENTO_ENDERECO = {
    "rua": "EndCompleto",          # Coluna da rua (NOT NULL)
    "bairro": "EndBairro",        # Coluna do bairro (NOT NULL)
    "cidade": "EndCidade",        # Coluna da cidade (NOT NULL)
    "estado": "EndUF"             # Coluna do estado (NOT NULL, ex: SP, RJ)
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

def validar_cpf(cpf):
    """Valida se o CPF é matematicamente válido e possui 11 dígitos."""
    if not cpf:
        return False
    # Remove qualquer caractere que não seja dígito
    cpf = "".join(char for char in str(cpf) if char.isdigit())
    
    if len(cpf) != 11:
        return False
        
    # CPFs com todos os dígitos iguais são inválidos
    if cpf == cpf[0] * 11:
        return False
        
    # Validação do primeiro dígito verificador
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    if int(cpf[9]) != digito1:
        return False
        
    # Validação do segundo dígito verificador
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    if int(cpf[10]) != digito2:
        return False
        
    return True


def validar_cnpj(cnpj):
    """Valida se o CNPJ é matematicamente válido e possui 14 dígitos."""
    if not cnpj:
        return False
    # Remove qualquer caractere que não seja dígito
    cnpj = "".join(char for char in str(cnpj) if char.isdigit())
    
    if len(cnpj) != 14:
        return False
        
    # CNPJs com todos os dígitos iguais são inválidos
    if cnpj == cnpj[0] * 14:
        return False
        
    # Validação do primeiro dígito verificador
    multiplicadores1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * multiplicadores1[i] for i in range(12))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    if int(cnpj[12]) != digito1:
        return False
        
    # Validação do segundo dígito verificador
    multiplicadores2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * multiplicadores2[i] for i in range(13))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    if int(cnpj[13]) != digito2:
        return False
        
    return True


def formatar_data(data_val):
    """Formata a data de nascimento para YYYY-MM-DD, lidando com formatos variados (como YYYYMMDD numérico)."""
    if not data_val or pd.isna(data_val):
        return None
    s = str(data_val).strip()
    # Se terminar com .0, remove (comum em floats do excel)
    if s.endswith('.0'):
        s = s[:-2]
    s_digits = ''.join(c for c in s if c.isdigit())
    if len(s_digits) == 8:
        possivel_ano = int(s_digits[:4])
        if 1900 <= possivel_ano <= 2100:
            fmt = '%Y%m%d'
        else:
            fmt = '%d%m%Y'
        try:
            dt = pd.to_datetime(s_digits, format=fmt, errors='coerce')
            if not pd.isna(dt):
                return dt.strftime('%Y-%m-%d')
        except Exception:
            pass
    try:
        dt = pd.to_datetime(s, dayfirst=True, errors='coerce')
        if not pd.isna(dt):
            return dt.strftime('%Y-%m-%d')
    except Exception:
        pass
    return None


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

    # Coleta todas as colunas mapeadas que precisam existir na planilha
    colunas_mapeadas = []
    for col in list(MAPEAMENTO_CLIENTES.values()) + list(MAPEAMENTO_ENDERECO.values()):
        if col:
            colunas_mapeadas.append(col)

    # Valida se as colunas configuradas existem no arquivo
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

    total_processados = 0
    total_inseridos = 0
    total_erros = 0

    print("\nIniciando processamento dos dados...")

    for index, row in df.iterrows():
        total_processados += 1
        
        # 1. Extrai dados do Cliente
        nome = obter_valor(row, MAPEAMENTO_CLIENTES, "nome", "Sem Nome")
        
        # Se não houver email na planilha, descartamos a linha
        email = obter_valor(row, MAPEAMENTO_CLIENTES, "email")
        if not email:
            print(f"Linha {index + 1}: Ignorado por ausência de email.")
            total_erros += 1
            continue
            
        documento_bruto = obter_valor(row, MAPEAMENTO_CLIENTES, "documento")
        documento_limpo = "".join(char for char in str(documento_bruto) if char.isdigit()) if documento_bruto else ""
        
        tipo_documento = None
        documento = None
        
        if len(documento_limpo) == 11:
            if not validar_cpf(documento_limpo):
                print(f"Linha {index + 1}: Ignorado por CPF inválido ({documento_bruto}).")
                total_erros += 1
                continue
            tipo_documento = "CPF"
            documento = documento_limpo
        elif len(documento_limpo) == 14:
            if not validar_cnpj(documento_limpo):
                print(f"Linha {index + 1}: Ignorado por CNPJ inválido ({documento_bruto}).")
                total_erros += 1
                continue
            tipo_documento = "CNPJ"
            documento = documento_limpo
        else:
            # Se for insuficiente (qualquer outro tamanho ou vazio), deixa NULL (None)
            tipo_documento = None
            documento = None
            
        contrato = obter_valor(row, MAPEAMENTO_CLIENTES, "contrato")
        telefone = obter_valor(row, MAPEAMENTO_CLIENTES, "telefone")
        
        data_nascimento = obter_valor(row, MAPEAMENTO_CLIENTES, "data_nascimento")
        data_nascimento = formatar_data(data_nascimento)
            
        status = obter_valor(row, MAPEAMENTO_CLIENTES, "status", "ATIVO")
        if status not in ["ATIVO", "INATIVO", "BLOQUEADO"]:
            status = "ATIVO"  # Ajusta para respeitar o ENUM

        # 2. Extrai dados do Endereço
        rua = obter_valor(row, MAPEAMENTO_ENDERECO, "rua", "Rua Não Informada")
        bairro = obter_valor(row, MAPEAMENTO_ENDERECO, "bairro", "Bairro Não Informado")
        cidade = obter_valor(row, MAPEAMENTO_ENDERECO, "cidade", "Cidade Não Informada")
        estado = obter_valor(row, MAPEAMENTO_ENDERECO, "estado", "SP")
        if len(estado) > 2:
            estado = estado[:2] # Garante tamanho máximo de CHAR(2)

        # 3. Transação de Inserção nas duas tabelas
        try:
            # SQL para inserir na tabela clientes
            sql_cliente = f"""
                INSERT INTO clientes (nome, email, tipo_documento, documento, status, contrato, telefone, data_nascimento)
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
            """
            valores_cliente = (nome, email, tipo_documento, documento, status, contrato, telefone, data_nascimento)
            cursor.execute(sql_cliente, valores_cliente)
            
            # Recupera o ID gerado pelo AUTO_INCREMENT
            cliente_id = cursor.lastrowid
            
            # SQL para inserir na tabela endereco
            sql_endereco = f"""
                INSERT INTO endereco (cliente_id, rua, bairro, cidade, estado)
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
            """
            valores_endereco = (cliente_id, rua, bairro, cidade, estado)
            cursor.execute(sql_endereco, valores_endereco)
            
            # Confirma as alterações da linha atual
            conexao.commit()
            total_inseridos += 1
            
        except duplicado_excecao as err:
            conexao.rollback()
            # Trata casos de registro com email ou documento duplicado
            print(f"Linha {index + 1}: Ignorado por duplicidade de email/documento ({email} / {documento}).")
            total_erros += 1
        except Exception as e:
            conexao.rollback()
            print(f"Linha {index + 1}: Erro ao inserir dados: {e}")
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
    # Certifique-se de instalar as dependências antes de rodar:
    # Para Excel: pip install pandas openpyxl
    # Para MySQL: pip install mysql-connector-python
    extrair_e_salvar()
