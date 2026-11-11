"""Controle do Speculos pela API REST (telas, botoes, capturas e APDU)."""
from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import requests

API = os.environ.get("SPECULOS_API", "http://127.0.0.1:5000")
TELA_INICIAL = ["Bitcoin Testnet", "app is ready"]


@dataclass
class Tela:
    textos: list[str]
    imagem: str | None = None  # caminho relativo a reports/

    @property
    def texto(self) -> str:
        return " | ".join(self.textos)


@dataclass
class Speculos:
    api: str = API
    pasta_evidencias: Path | None = None
    telas: list[Tela] = field(default_factory=list)
    canal: object | None = None  # ledgercomm.Transport
    _seq: int = 0

    # Leitura da tela -----------------------------------------------------
    def textos(self) -> list[str]:
        r = requests.get(f"{self.api}/events", params={"currentscreenonly": "true"}, timeout=10)
        r.raise_for_status()
        return [e["text"] for e in r.json()["events"]]

    def capturar(self, nome: str | None = None) -> Tela:
        """Registra a tela atual: texto (via /events) e imagem PNG (via /screenshot)."""
        tela = Tela(self.textos())
        if self.pasta_evidencias is not None:
            self._seq += 1
            self.pasta_evidencias.mkdir(parents=True, exist_ok=True)
            arquivo = self.pasta_evidencias / f"{self._seq:02d}-{nome or 'tela'}.png"
            png = requests.get(f"{self.api}/screenshot", timeout=10)
            png.raise_for_status()
            arquivo.write_bytes(png.content)
            tela.imagem = str(arquivo)
        self.telas.append(tela)
        return tela

    def aguardar(self, condicao, limite_s: float = 10.0, intervalo: float = 0.2) -> list[str]:
        fim = time.monotonic() + limite_s
        ultimo: list[str] = []
        while time.monotonic() < fim:
            ultimo = self.textos()
            if condicao(ultimo):
                return ultimo
            time.sleep(intervalo)
        raise TimeoutError(f"Tela esperada nao apareceu. Ultima tela: {ultimo}")

    def aguardar_texto(self, texto: str, limite_s: float = 10.0) -> list[str]:
        return self.aguardar(lambda t: texto in t, limite_s)

    def aguardar_mudanca(self, anterior: list[str], limite_s: float = 5.0) -> list[str]:
        return self.aguardar(lambda t: t and t != anterior, limite_s)

    def aguardar_tela_inicial(self, limite_s: float = 15.0) -> list[str]:
        return self.aguardar(lambda t: t == TELA_INICIAL, limite_s)

    # Botoes --------------------------------------------------------------
    def apertar(self, botao: str) -> None:
        r = requests.post(f"{self.api}/button/{botao}", json={"action": "press-and-release"}, timeout=10)
        r.raise_for_status()

    def revisar_e_decidir(self, alvo: str, primeira: str, max_telas: int = 30) -> list[Tela]:
        """Percorre as telas de revisao com o botao direito, capturando cada uma,
        ate encontrar `alvo` (por exemplo "Sign message" ou "Reject message"),
        e confirma com os dois botoes, como uma pessoa faria no aparelho."""
        atual = self.aguardar_texto(primeira)
        revisadas: list[Tela] = []
        for _ in range(max_telas):
            revisadas.append(self.capturar())
            if alvo in atual:
                self.apertar("both")
                return revisadas
            self.apertar("right")
            atual = self.aguardar_mudanca(atual)
        raise AssertionError(f"Opcao '{alvo}' nao encontrada em {max_telas} telas")

    # APDU cru ------------------------------------------------------------
    def apdu(self, hexa: str) -> tuple[bytes, int]:
        """Envia um APDU cru. Usa o mesmo canal TCP da biblioteca cliente quando
        ele existe: o Speculos repassa toda resposta ao cliente TCP conectado,
        entao misturar /apdu (REST) e TCP na mesma sessao embaralha respostas."""
        if self.canal is not None:
            sw, dados = self.canal.exchange_raw(hexa)
            return dados, sw
        r = requests.post(f"{self.api}/apdu", json={"data": hexa}, timeout=30)
        r.raise_for_status()
        bruto = bytes.fromhex(r.json()["data"])
        return bruto[:-2], int.from_bytes(bruto[-2:], "big")


class EmSegundoPlano:
    """Executa uma chamada bloqueante ao app (que espera o usuario) em outra thread."""

    def __init__(self, funcao):
        self.resultado = None
        self.erro: BaseException | None = None
        self._t = threading.Thread(target=self._rodar, args=(funcao,), daemon=True)
        self._t.start()

    def _rodar(self, funcao):
        try:
            self.resultado = funcao()
        except BaseException as e:  # noqa: BLE001 - o teste decide o que fazer
            self.erro = e

    def aguardar(self, limite_s: float = 30.0):
        self._t.join(limite_s)
        if self._t.is_alive():
            raise TimeoutError("O app nao respondeu a tempo")
        return self


def texto_quebrado(telas: list[Tela], titulo: str) -> str:
    """Junta um valor longo que o aparelho quebra em varias linhas ou paginas
    (por exemplo endereco ou chave publica) a partir do titulo da tela."""
    partes: list[str] = []
    for tela in telas:
        if tela.textos and tela.textos[0].startswith(titulo):
            partes.extend(tela.textos[1:])
    return "".join(partes)
