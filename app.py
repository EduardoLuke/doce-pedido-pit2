"""PIT II - Sistema simples de pedidos de cupcakes.
Execute: python app.py
Usa apenas Python (biblioteca padrão) e SQLite.
"""
import json
import os
import sqlite3
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

PASTA = Path(__file__).resolve().parent
BANCO = Path(os.environ.get("DB_PATH", str(PASTA / "pedidos.db")))
PORTA = int(os.environ.get("PORT", "8000"))
SABORES = {
    "Chocolate": 850,
    "Baunilha": 750,
    "Morango": 900,
}
STATUS = ("Recebido", "Em preparo", "Pronto", "Entregue", "Cancelado")


def conectar():
    conexao = sqlite3.connect(str(BANCO), timeout=10)
    conexao.row_factory = sqlite3.Row
    return conexao


def preparar_banco():
    BANCO.parent.mkdir(parents=True, exist_ok=True)
    with conectar() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT NOT NULL,
            sabor TEXT NOT NULL,
            quantidade INTEGER NOT NULL CHECK (quantidade BETWEEN 1 AND 30),
            total_centavos INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Recebido',
            criado_em TEXT NOT NULL
        )""")


def listar_pedidos():
    with conectar() as db:
        rows = db.execute("SELECT * FROM pedidos ORDER BY id DESC").fetchall()
        return [dict(row) for row in rows]


def cadastrar_pedido(dados):
    if not isinstance(dados, dict):
        raise ValueError("Envie os dados do pedido corretamente.")
    cliente = dados.get("cliente", "")
    sabor = dados.get("sabor", "")
    quantidade = dados.get("quantidade")
    if not isinstance(cliente, str) or not (2 <= len(cliente.strip()) <= 80):
        raise ValueError("Informe um nome entre 2 e 80 caracteres.")
    if sabor not in SABORES:
        raise ValueError("Escolha um sabor disponível.")
    if type(quantidade) is not int or not (1 <= quantidade <= 30):
        raise ValueError("A quantidade deve ser de 1 a 30.")
    with conectar() as db:
        cursor = db.execute(
            "INSERT INTO pedidos (cliente, sabor, quantidade, total_centavos, status, criado_em) VALUES (?, ?, ?, ?, ?, ?)",
            (cliente.strip(), sabor, quantidade, SABORES[sabor] * quantidade,
             "Recebido", datetime.now().strftime("%d/%m/%Y %H:%M")),
        )
        pedido_id = cursor.lastrowid
        row = db.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
        return dict(row)


def alterar_status(pedido_id, status):
    if status not in STATUS:
        raise ValueError("Status inválido.")
    with conectar() as db:
        row = db.execute("SELECT status FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
        if not row:
            raise LookupError("Pedido não encontrado.")
        if row["status"] in ("Entregue", "Cancelado") and row["status"] != status:
            raise ValueError("Pedidos finalizados não podem ser alterados.")
        db.execute("UPDATE pedidos SET status = ? WHERE id = ?", (status, pedido_id))
        return dict(db.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone())


class Aplicacao(BaseHTTPRequestHandler):
    def responder(self, codigo, dados):
        conteudo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(conteudo)))
        self.end_headers()
        self.wfile.write(conteudo)

    def ler_json(self):
        try:
            tamanho = int(self.headers.get("Content-Length", "0"))
            if tamanho < 1 or tamanho > 10000:
                raise ValueError("Dados inválidos ou muito extensos.")
            return json.loads(self.rfile.read(tamanho).decode("utf-8"))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("Não foi possível ler os dados enviados.")

    def do_GET(self):
        rota = urlparse(self.path).path
        if rota == "/api/pedidos":
            self.responder(200, listar_pedidos())
        elif rota in ("/", "/index.html"):
            conteudo = (PASTA / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(conteudo)))
            self.end_headers()
            self.wfile.write(conteudo)
        elif rota == "/health":
            self.responder(200, {"status": "ok"})
        else:
            self.responder(404, {"erro": "Página não encontrada."})

    def do_POST(self):
        if urlparse(self.path).path != "/api/pedidos":
            return self.responder(404, {"erro": "Rota não encontrada."})
        try:
            self.responder(201, cadastrar_pedido(self.ler_json()))
        except ValueError as erro:
            self.responder(400, {"erro": str(erro)})

    def do_PATCH(self):
        partes = urlparse(self.path).path.strip("/").split("/")
        if len(partes) != 3 or partes[:2] != ["api", "pedidos"] or not partes[2].isdigit():
            return self.responder(404, {"erro": "Rota não encontrada."})
        try:
            dados = self.ler_json()
            if not isinstance(dados, dict):
                raise ValueError("Dados inválidos.")
            self.responder(200, alterar_status(int(partes[2]), dados.get("status")))
        except LookupError as erro:
            self.responder(404, {"erro": str(erro)})
        except ValueError as erro:
            self.responder(400, {"erro": str(erro)})


if __name__ == "__main__":
    preparar_banco()
    servidor = ThreadingHTTPServer(("0.0.0.0", PORTA), Aplicacao)
    print(f"Sistema pronto em http://localhost:{PORTA}", flush=True)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
    finally:
        servidor.server_close()
