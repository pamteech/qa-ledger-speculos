"""Fixtures e coleta de evidencias da suite."""
from __future__ import annotations

import base64
import json
import os
import re
import time
from pathlib import Path

import pytest
import requests
from ledger_bitcoin import Chain, TransportClient, createClient

from qa_ledger.dispositivo import API, Speculos

RAIZ = Path(__file__).parent
RELATORIOS = RAIZ / "reports"
TELAS = RELATORIOS / "telas"
APDU_PORTA = int(os.environ.get("SPECULOS_APDU_PORT", "9999"))
_resultados: dict[str, dict] = {}


def pytest_configure(config):
    config.addinivalue_line("markers", "caso(id, titulo, categoria): identifica o caso de teste no relatorio")


def _id_seguro(nodeid: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", nodeid.split("::", 1)[-1]).strip("_")


@pytest.fixture(scope="session", autouse=True)
def speculos_no_ar():
    fim = time.monotonic() + 60
    while time.monotonic() < fim:
        try:
            requests.get(f"{API}/events", timeout=2).raise_for_status()
            return
        except requests.RequestException:
            time.sleep(1)
    pytest.exit(f"Speculos nao respondeu em {API}. Suba o emulador antes (veja o README).", returncode=3)


@pytest.fixture(scope="session")
def transporte():
    t = TransportClient(interface="tcp", server="127.0.0.1", port=APDU_PORTA)
    yield t
    t.stop()


@pytest.fixture(scope="session")
def cliente(transporte):
    return createClient(transporte, chain=Chain.TEST)


@pytest.fixture
def aparelho(request, transporte):
    """Speculos com evidencias gravadas em reports/telas/<teste>/."""
    pasta = TELAS / _id_seguro(request.node.nodeid)
    disp = Speculos(pasta_evidencias=pasta, canal=transporte.transport)
    disp.aguardar_tela_inicial()
    request.node._aparelho = disp
    yield disp
    # Garante que o proximo teste comeca da tela inicial. Se um teste falhou no
    # meio de uma revisao, rejeita a operacao pendente para nao contaminar os demais.
    try:
        disp.aguardar_tela_inicial(limite_s=5)
    except TimeoutError:
        for _ in range(30):
            textos = disp.textos()
            if any(t.startswith(("Reject", "Cancel")) for t in textos):
                disp.apertar("both")
                break
            disp.apertar("right")
            time.sleep(0.3)
        disp.aguardar_tela_inicial()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    saida = yield
    rel = saida.get_result()
    marca = item.get_closest_marker("caso")
    if marca is None:
        return
    cid, titulo, categoria = marca.args
    reg = _resultados.setdefault(item.nodeid, {
        "id": cid, "titulo": titulo, "categoria": categoria, "nodeid": item.nodeid,
        "parametro": item.callspec.id if hasattr(item, "callspec") else "",
        "resultado": "aprovado", "duracao_s": 0.0, "telas": [], "erro": "",
    })
    reg["duracao_s"] += rel.duration
    if rel.failed:
        reg["resultado"] = "reprovado"
        reg["erro"] = str(rel.longreprtext).splitlines()[-1][:400] if rel.longreprtext else ""
    elif rel.skipped and rel.when == "setup":
        reg["resultado"] = "pulado"
    if rel.when == "call":
        disp = getattr(item, "_aparelho", None)
        extras = getattr(rel, "extras", [])
        if disp is not None:
            html = pytest.importorskip("pytest_html")
            for tela in disp.telas:
                if not tela.imagem:
                    continue
                reg["telas"].append({"texto": tela.texto, "imagem": str(Path(tela.imagem).relative_to(RELATORIOS))})
                dados = base64.b64encode(Path(tela.imagem).read_bytes()).decode()
                extras.append(html.extras.png(dados, name=tela.texto))
        rel.extras = extras


def pytest_sessionfinish(session, exitstatus):
    RELATORIOS.mkdir(exist_ok=True)
    meta = {
        "app": os.environ.get("APP_NOME", "Bitcoin Test"),
        "app_versao": os.environ.get("APP_VERSAO", "2.6.0"),
        "modelo": os.environ.get("SPECULOS_MODELO", "nanosp"),
        "fim": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    (RELATORIOS / "resultados.json").write_text(
        json.dumps({"meta": meta, "casos": list(_resultados.values())}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def pytest_html_report_title(report):
    report.title = "QA Ledger Speculos · relatório detalhado do pytest"
