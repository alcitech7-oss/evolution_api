#!/usr/bin/env python3
"""
SISTEMA DE AGENDAMENTO - VERSAO CORRIGIDA
Cria agendamentos no banco de dados e gera comprovantes
"""

import os
import sqlite3
import shutil
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import re
import json

# ==================== CONFIGURACOES ====================
PASTA_ENTRADA = "mensagens_recebidas"
PASTA_SAIDA = "mensagens_enviadas"
PASTA_AGENDAMENTOS = "agendamentos"
DATABASE = "agendamentos.db"
ARQUIVO_ESTADOS = "estados_conversas.json"

print("="*60)
print("SISTEMA DE AGENDAMENTO - INICIANDO...")
print("="*60)

# Horario de funcionamento
HORARIOS_DISPONIVEIS = {
    "segunda": ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00", "17:30"],
    "terca": ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00", "17:30"],
    "quarta": ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00", "17:30"],
    "quinta": ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00", "17:30"],
    "sexta": ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00", "17:30"],
    "sabado": ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30"],
    "domingo": []
}

PROFISSIONAIS = [
    {"id": 1, "nome": "Dr. Carlos Silva", "especialidade": "Cardiologia"},
    {"id": 2, "nome": "Dra. Ana Santos", "especialidade": "Dermatologia"},
    {"id": 3, "nome": "Dr. Roberto Lima", "especialidade": "Ortopedia"},
    {"id": 4, "nome": "Dra. Fernanda Costa", "especialidade": "Pediatria"},
]

# Estados das conversas
estados_conversas = {}

def salvar_estados():
    with open(ARQUIVO_ESTADOS, 'w', encoding='utf-8') as f:
        json.dump(estados_conversas, f, ensure_ascii=False, indent=2, default=str)

def carregar_estados():
    global estados_conversas
    if os.path.exists(ARQUIVO_ESTADOS):
        with open(ARQUIVO_ESTADOS, 'r', encoding='utf-8') as f:
            estados_conversas = json.load(f)

def criar_pastas():
    for pasta in [PASTA_ENTRADA, PASTA_SAIDA, PASTA_AGENDAMENTOS]:
        if not os.path.exists(pasta):
            os.makedirs(pasta)
            print(f"Pasta criada: {pasta}")

def init_database():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            telefone TEXT UNIQUE NOT NULL,
            data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_consultas INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agendamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            profissional_id INTEGER,
            profissional_nome TEXT,
            data DATE,
            horario TEXT,
            status TEXT DEFAULT 'pendente',
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_confirmacao TIMESTAMP,
            FOREIGN KEY (cliente_id) REFERENCES clientes (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Banco de dados inicializado")

def get_or_create_cliente(telefone: str, nome: str = "Paciente") -> dict:
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM clientes WHERE telefone = ?", (telefone,))
    cliente = cursor.fetchone()
    
    if not cliente:
        cursor.execute("INSERT INTO clientes (nome, telefone) VALUES (?, ?)", (nome, telefone))
        conn.commit()
        cursor.execute("SELECT * FROM clientes WHERE telefone = ?", (telefone,))
        cliente = cursor.fetchone()
        print(f"  [DB] Novo cliente criado: {nome} - {telefone}")
    
    conn.close()
    return dict(cliente)

def salvar_agendamento(cliente_id: int, profissional: dict, data: str, horario: str) -> int:
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO agendamentos (cliente_id, profissional_id, profissional_nome, data, horario, status)
        VALUES (?, ?, ?, ?, ?, 'pendente')
    ''', (cliente_id, profissional['id'], profissional['nome'], data, horario))
    
    agendamento_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    print(f"  [DB] Agendamento SALVO! ID: {agendamento_id} - {profissional['nome']} - {data} {horario}")
    return agendamento_id

def confirmar_agendamento(agendamento_id: int):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE agendamentos SET status = 'confirmado', data_confirmacao = CURRENT_TIMESTAMP WHERE id = ?
    ''', (agendamento_id,))
    
    cursor.execute('''
        UPDATE clientes SET total_consultas = total_consultas + 1 
        WHERE id = (SELECT cliente_id FROM agendamentos WHERE id = ?)
    ''', (agendamento_id,))
    
    conn.commit()
    conn.close()
    print(f"  [DB] Agendamento CONFIRMADO! ID: {agendamento_id}")

def cancelar_agendamento(agendamento_id: int):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('UPDATE agendamentos SET status = "cancelado" WHERE id = ?', (agendamento_id,))
    conn.commit()
    conn.close()
    print(f"  [DB] Agendamento CANCELADO! ID: {agendamento_id}")

def get_agendamentos_cliente(telefone: str, status: str = None) -> List[dict]:
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cliente = get_or_create_cliente(telefone)
    
    if status:
        cursor.execute('''
            SELECT * FROM agendamentos WHERE cliente_id = ? AND status = ? ORDER BY data, horario
        ''', (cliente['id'], status))
    else:
        cursor.execute('''
            SELECT * FROM agendamentos WHERE cliente_id = ? ORDER BY data, horario
        ''', (cliente['id'],))
    
    agendamentos = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return agendamentos

def get_agendamento(agendamento_id: int) -> Optional[dict]:
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM agendamentos WHERE id = ?", (agendamento_id,))
    agendamento = cursor.fetchone()
    conn.close()
    return dict(agendamento) if agendamento else None

def detectar_intencao(mensagem: str) -> dict:
    msg_lower = mensagem.lower()
    
    if any(p in msg_lower for p in ['agendar', 'marcar', 'consulta', 'horario', 'reservar']):
        if any(p in msg_lower for p in ['remarcar', 'reagendar', 'mudar', 'trocar']):
            return {'intencao': 'remarcar'}
        return {'intencao': 'agendar'}
    elif any(p in msg_lower for p in ['cancelar', 'desmarcar', 'cancelamento']):
        return {'intencao': 'cancelar'}
    elif any(p in msg_lower for p in ['confirmar', 'confirmo', 'confirmacao', 'sim']):
        return {'intencao': 'confirmar'}
    elif any(p in msg_lower for p in ['listar', 'minhas consultas', 'meus agendamentos', 'ver consultas']):
        return {'intencao': 'listar'}
    elif any(p in msg_lower for p in ['ajuda', 'menu', 'opcoes', 'como funciona']):
        return {'intencao': 'ajuda'}
    elif mensagem.strip().isdigit() and 1 <= int(mensagem.strip()) <= 10:
        return {'intencao': 'selecao_numero', 'numero': int(mensagem.strip())}
    else:
        return {'intencao': 'nao_identificado'}

def extrair_profissional(mensagem: str) -> Optional[dict]:
    msg_lower = mensagem.lower()
    for p in PROFISSIONAIS:
        if p['nome'].lower() in msg_lower or p['especialidade'].lower() in msg_lower:
            return p
    return None

def extrair_data(mensagem: str) -> Optional[str]:
    hoje = datetime.now()
    msg_lower = mensagem.lower()
    
    if 'hoje' in msg_lower:
        return hoje.strftime('%Y-%m-%d')
    if 'amanha' in msg_lower or 'amanhã' in msg_lower:
        return (hoje + timedelta(days=1)).strftime('%Y-%m-%d')
    if 'proxima semana' in msg_lower or 'próxima semana' in msg_lower:
        days = (7 - hoje.weekday()) % 7
        return (hoje + timedelta(days=days if days > 0 else 7)).strftime('%Y-%m-%d')
    
    padrao = r'(\d{1,2})[/-](\d{1,2})'
    match = re.search(padrao, mensagem)
    if match:
        dia, mes = int(match.group(1)), int(match.group(2))
        try:
            data = datetime(hoje.year, mes, dia)
            if data < hoje:
                data = datetime(hoje.year + 1, mes, dia)
            return data.strftime('%Y-%m-%d')
        except:
            pass
    return None

def obter_horarios_disponiveis(data: str, profissional_id: int = None) -> List[str]:
    data_obj = datetime.strptime(data, '%Y-%m-%d')
    dias_map = {'monday': 'segunda', 'tuesday': 'terca', 'wednesday': 'quarta',
                'thursday': 'quinta', 'friday': 'sexta', 'saturday': 'sabado', 'sunday': 'domingo'}
    dia = dias_map.get(data_obj.strftime('%A').lower(), 'segunda')
    horarios = HORARIOS_DISPONIVEIS.get(dia, [])
    
    import random
    random.seed(f"{data}_{profissional_id}")
    ocupados = random.sample(horarios, min(3, len(horarios) // 3)) if horarios else []
    return [h for h in horarios if h not in ocupados]

def enviar_resposta(telefone: str, mensagem: str):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    nome_arquivo = f"{PASTA_SAIDA}/{telefone}_{timestamp}.txt"
    
    with open(nome_arquivo, 'w', encoding='utf-8') as f:
        f.write(f"PARA: {telefone}\n")
        f.write(f"DATA: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
        f.write("="*50 + "\n")
        f.write(mensagem)
    
    print(f"  -> Resposta salva: {nome_arquivo}")

def gerar_comprovante(agendamento_id: int, telefone: str):
    ag = get_agendamento(agendamento_id)
    if ag:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"{PASTA_AGENDAMENTOS}/agendamento_{ag['id']}_{timestamp}.txt"
        
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            f.write("="*60 + "\n")
            f.write("COMPROVANTE DE AGENDAMENTO\n")
            f.write("="*60 + "\n\n")
            f.write(f"Protocolo: {ag['id']}\n")
            f.write(f"Paciente: {telefone}\n")
            f.write(f"Profissional: {ag['profissional_nome']}\n")
            f.write(f"Data: {ag['data'].replace('-', '/')}\n")
            f.write(f"Horario: {ag['horario']}\n")
            f.write(f"Status: {ag['status'].upper()}\n")
            f.write(f"Data do agendamento: {ag['data_criacao']}\n")
            f.write("\n" + "="*60 + "\n")
        
        print(f"  -> COMPROVANTE gerado: {nome_arquivo}")
        return True
    return False

def processar_mensagem(telefone: str, mensagem: str, nome: str):
    global estados_conversas
    
    # Obter estado atual
    estado = estados_conversas.get(telefone, {'passo': 'inicio', 'dados': {}})
    cliente = get_or_create_cliente(telefone, nome)
    
    print(f"  Estado: {estado['passo']}")
    
    # Processar baseado no passo
    if estado['passo'] == 'aguardando_horario':
        try:
            escolha = int(mensagem.strip())
            horarios = estado['dados']['horarios']
            if 1 <= escolha <= len(horarios):
                horario_escolhido = horarios[escolha - 1]
                
                # SALVAR AGENDAMENTO
                agendamento_id = salvar_agendamento(
                    cliente['id'],
                    estado['dados']['profissional'],
                    estado['dados']['data'],
                    horario_escolhido
                )
                
                msg = f"""AGENDAMENTO PENDENTE DE CONFIRMACAO

Profissional: {estado['dados']['profissional']['nome']}
Data: {estado['dados']['data'].replace('-', '/')}
Horario: {horario_escolhido}
Codigo: {agendamento_id}

Para CONFIRMAR, digite: CONFIRMO
Para CANCELAR, digite: CANCELAR"""
                
                enviar_resposta(telefone, msg)
                estados_conversas[telefone] = {'passo': 'aguardando_confirmacao', 'dados': {'agendamento_id': agendamento_id}}
                salvar_estados()
                return
            else:
                enviar_resposta(telefone, f"Opcao invalida! Digite 1 a {len(horarios)}")
                return
        except ValueError:
            enviar_resposta(telefone, "Digite APENAS o numero do horario")
            return
    
    elif estado['passo'] == 'aguardando_confirmacao':
        if 'confirmo' in mensagem.lower() or 'sim' in mensagem.lower():
            confirmar_agendamento(estado['dados']['agendamento_id'])
            gerar_comprovante(estado['dados']['agendamento_id'], telefone)
            
            ag = get_agendamento(estado['dados']['agendamento_id'])
            msg = f"""CONSULTA CONFIRMADA!

Profissional: {ag['profissional_nome']}
Data: {ag['data'].replace('-', '/')}
Horario: {ag['horario']}
Protocolo: {ag['id']}

Voce recebera um lembrete 24 horas antes."""
            
            enviar_resposta(telefone, msg)
            estados_conversas[telefone] = {'passo': 'inicio', 'dados': {}}
            salvar_estados()
            return
            
        elif 'cancelar' in mensagem.lower() or 'nao' in mensagem.lower():
            cancelar_agendamento(estado['dados']['agendamento_id'])
            enviar_resposta(telefone, "CONSULTA CANCELADA! Horario liberado.")
            estados_conversas[telefone] = {'passo': 'inicio', 'dados': {}}
            salvar_estados()
            return
        else:
            enviar_resposta(telefone, "Digite CONFIRMO ou CANCELAR")
            return
    
    # Nova intencao
    intencao = detectar_intencao(mensagem)
    print(f"  Intencao: {intencao['intencao']}")
    
    if intencao['intencao'] == 'agendar':
        profissional = extrair_profissional(mensagem)
        
        if not profissional:
            msg = "ESCOLHA O PROFISSIONAL:\n\n"
            for i, p in enumerate(PROFISSIONAIS, 1):
                msg += f"{i} - {p['nome']} - {p['especialidade']}\n"
            msg += "\nDigite o numero do profissional:"
            enviar_resposta(telefone, msg)
            estados_conversas[telefone] = {'passo': 'aguardando_profissional', 'dados': {}}
            salvar_estados()
            return
        
        data = extrair_data(mensagem)
        if not data:
            msg = "QUAL DATA?\n\nExemplos:\n- hoje\n- amanha\n- proxima semana\n- 25/12\n\nDigite a data:"
            enviar_resposta(telefone, msg)
            estados_conversas[telefone] = {'passo': 'aguardando_data', 'dados': {'profissional': profissional}}
            salvar_estados()
            return
        
        horarios = obter_horarios_disponiveis(data, profissional['id'])
        if not horarios:
            msg = f"Sem horarios para {data.replace('-', '/')}. Escolha outra data:"
            enviar_resposta(telefone, msg)
            estados_conversas[telefone] = {'passo': 'aguardando_data', 'dados': {'profissional': profissional}}
            salvar_estados()
            return
        
        msg = f"HORARIOS DISPONIVEIS\n\nData: {data.replace('-', '/')}\nProfissional: {profissional['nome']}\n\n"
        for i, h in enumerate(horarios[:8], 1):
            msg += f"{i} - {h}\n"
        msg += "\nDigite o NUMERO do horario:"
        
        enviar_resposta(telefone, msg)
        estados_conversas[telefone] = {
            'passo': 'aguardando_horario',
            'dados': {
                'profissional': profissional,
                'data': data,
                'horarios': horarios
            }
        }
        salvar_estados()
        
    elif intencao['intencao'] == 'listar':
        agendamentos = get_agendamentos_cliente(telefone)
        if not agendamentos:
            enviar_resposta(telefone, "Voce nao tem consultas agendadas.")
        else:
            msg = "SUAS CONSULTAS:\n\n"
            for ag in agendamentos:
                status_icon = {'confirmado': '[OK]', 'pendente': '[ ]', 'cancelado': '[X]'}.get(ag['status'], '[?]')
                msg += f"{status_icon} {ag['profissional_nome']}\n"
                msg += f"   Data: {ag['data'].replace('-', '/')} as {ag['horario']}\n"
                msg += f"   Status: {ag['status']}\n\n"
            enviar_resposta(telefone, msg)
    
    elif intencao['intencao'] == 'cancelar':
        agendamentos = get_agendamentos_cliente(telefone, status='confirmado')
        if not agendamentos:
            enviar_resposta(telefone, "Nenhuma consulta confirmada para cancelar.")
        elif len(agendamentos) == 1:
            cancelar_agendamento(agendamentos[0]['id'])
            enviar_resposta(telefone, f"CONSULTA CANCELADA!\n\n{agendamentos[0]['profissional_nome']}\n{agendamentos[0]['data'].replace('-', '/')} as {agendamentos[0]['horario']}")
        else:
            msg = "QUAL CONSULTA CANCELAR?\n\n"
            for i, ag in enumerate(agendamentos, 1):
                msg += f"{i} - {ag['profissional_nome']} - {ag['data'].replace('-', '/')} as {ag['horario']}\n"
            enviar_resposta(telefone, msg)
    
    elif intencao['intencao'] == 'confirmar':
        pendentes = get_agendamentos_cliente(telefone, status='pendente')
        if pendentes:
            confirmar_agendamento(pendentes[0]['id'])
            gerar_comprovante(pendentes[0]['id'], telefone)
            enviar_resposta(telefone, f"CONSULTA CONFIRMADA! Protocolo: {pendentes[0]['id']}")
        else:
            enviar_resposta(telefone, "Nenhum agendamento pendente para confirmar.")
    
    else:
        msg = """ASSISTENTE DE AGENDAMENTO

COMANDOS:
1. Agendar: "Agendar com Dr. Carlos para amanha"
2. Listar: "Minhas consultas"
3. Cancelar: "Cancelar minha consulta"
4. Confirmar: "CONFIRMO" (apos agendar)"""
        enviar_resposta(telefone, msg)

def processar_mensagem_arquivo(caminho_arquivo: str):
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        conteudo = f.read()
    
    # Separar mensagens multiplas no mesmo arquivo
    blocos = conteudo.strip().split('\n\n')
    
    for bloco in blocos:
        linhas = bloco.split('\n')
        telefone = None
        nome = "Paciente"
        mensagem = []
        
        for linha in linhas:
            if linha.startswith("DE:"):
                telefone = linha.replace("DE:", "").strip()
            elif linha.startswith("NOME:"):
                nome = linha.replace("NOME:", "").strip()
            elif not linha.startswith("DATA:") and not linha.startswith("===") and linha.strip():
                mensagem.append(linha)
        
        if telefone and mensagem:
            mensagem_texto = ' '.join(mensagem).strip()
            print(f"\n[Processando] {telefone} - {nome}")
            print(f"Mensagem: {mensagem_texto[:80]}")
            processar_mensagem(telefone, mensagem_texto, nome)

def processar_todas_mensagens():
    carregar_estados()
    
    arquivos = [f for f in os.listdir(PASTA_ENTRADA) if f.endswith('.txt') and not f.endswith('.processed')]
    
    if not arquivos:
        print(f"\nNenhuma mensagem em: {PASTA_ENTRADA}/")
        return
    
    print(f"\nProcessando {len(arquivos)} arquivo(s)...")
    for arquivo in arquivos:
        caminho = os.path.join(PASTA_ENTRADA, arquivo)
        print(f"\n--- Lendo arquivo: {arquivo} ---")
        try:
            processar_mensagem_arquivo(caminho)
            os.rename(caminho, caminho + ".processed")
            print(f"[OK] {arquivo} processado")
        except Exception as e:
            print(f"[ERRO] {arquivo}: {e}")

def criar_arquivo_teste_unico():
    """Cria um unico arquivo com o fluxo completo"""
    conteudo = """DE: 5511999999999
NOME: Joao Silva
DATA: 15/12/2024 10:00:00
==================================================
Agendar com Dr. Carlos Silva para amanha

DE: 5511999999999
NOME: Joao Silva
DATA: 15/12/2024 10:02:00
==================================================
1

DE: 5511999999999
NOME: Joao Silva
DATA: 15/12/2024 10:05:00
==================================================
CONFIRMO

DE: 5511999999999
NOME: Joao Silva
DATA: 15/12/2024 10:10:00
==================================================
Minhas consultas"""
    
    with open(f"{PASTA_ENTRADA}/teste_completo.txt", 'w', encoding='utf-8') as f:
        f.write(conteudo)
    
    print(f"\nArquivo de teste criado: {PASTA_ENTRADA}/teste_completo.txt")

# ==================== MAIN ====================
criar_pastas()
init_database()
criar_arquivo_teste_unico()
processar_todas_mensagens()

print("\n" + "="*60)
print("PROCESSAMENTO CONCLUIDO!")
print(f"Respostas: {PASTA_SAIDA}/")
print(f"Comprovantes: {PASTA_AGENDAMENTOS}/")
print("="*60)

# Mostrar agendamentos criados
conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM agendamentos")
count = cursor.fetchone()[0]
print(f"\nTotal de agendamentos no banco: {count}")
conn.close()