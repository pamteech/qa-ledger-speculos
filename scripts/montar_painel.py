"""Monta reports/index.html a partir de reports/resultados.json (gerado pelo pytest).

Uso: python scripts/montar_painel.py
"""
from __future__ import annotations

import html
import json
import os
import shutil
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

RAIZ = Path(__file__).resolve().parent.parent
REL = RAIZ / "reports"
esc = html.escape

dados = json.loads((REL / "resultados.json").read_text(encoding="utf-8"))
meta, casos = dados["meta"], dados["casos"]
shutil.copy(RAIZ / "scripts" / "estilo.css", REL / "estilo.css")

repo = os.environ.get("GITHUB_REPOSITORY", "pamteech/qa-ledger-speculos")
run_id = os.environ.get("GITHUB_RUN_ID")
run_url = f"https://github.com/{repo}/actions/runs/{run_id}" if run_id else None
quando = datetime.strptime(meta["fim"], "%Y-%m-%dT%H:%M:%S%z").astimezone(ZoneInfo("America/Sao_Paulo"))

total = len(casos)
aprov = sum(c["resultado"] == "aprovado" for c in casos)
reprov = sum(c["resultado"] == "reprovado" for c in casos)
n_telas = sum(len(c["telas"]) for c in casos)
ids = len({c["id"] for c in casos})

TAG = {"aprovado": '<span class="tag ok">Aprovado</span>', "reprovado": '<span class="tag fail">Reprovado</span>',
       "pulado": '<span class="tag warn">Pulado</span>'}

# Agrupa por categoria e por caso (casos parametrizados viram uma linha so).
por_cat: "OrderedDict[str, OrderedDict[str, list]]" = OrderedDict()
for c in casos:
    por_cat.setdefault(c["categoria"], OrderedDict()).setdefault(c["id"], []).append(c)

linhas = []
for cat, grupo in por_cat.items():
    for cid, execs in grupo.items():
        ok = all(e["resultado"] == "aprovado" for e in execs)
        variacoes = ", ".join(f"<code>{esc(e['parametro'])}</code>" for e in execs if e["parametro"]) or "-"
        linhas.append(f"<tr><td>{esc(cid)}</td><td>{esc(execs[0]['titulo'])}</td><td>{esc(cat)}</td>"
                      f"<td>{variacoes}</td><td>{TAG['aprovado' if ok else 'reprovado']}</td></tr>")

blocos = []
vistos: set[str] = set()
for c in casos:
    if not c["telas"] and c["resultado"] == "aprovado":
        continue
    figuras = "".join(
        f'<figure class="tela"><img src="{esc(t["imagem"])}" alt="{esc(t["texto"])}" loading="lazy">'
        f'<figcaption>{esc(t["texto"])}</figcaption></figure>' for t in c["telas"])
    param = f" [{esc(c['parametro'])}]" if c["parametro"] else ""
    erro = f'<p class="erro">{esc(c["erro"])}</p>' if c["erro"] else ""
    ancora = "" if c["id"] in vistos else f' id="{c["id"].lower()}"'
    vistos.add(c["id"])
    blocos.append(f'<details class="caso"{ancora} open><summary><span class="id">{esc(c["id"])}</span>{esc(c["titulo"])}{param} '
                  f'{TAG[c["resultado"]]}</summary>{erro}<div class="tela-lista">{figuras}</div></details>')

pagina = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>QA Ledger Speculos - Painel de qualidade</title>
<meta name="description" content="Testes automatizados de carteira de hardware Ledger no emulador Speculos">
<link rel="stylesheet" href="estilo.css"></head><body>
<header class="topo"><div class="wrap"><span class="marca">QA Ledger Speculos</span><span class="sub">Painel de qualidade</span></div></header>
<main class="wrap">
<h1>Carteira de hardware no emulador</h1>
<p class="meta">App {esc(meta['app'])} {esc(meta['app_versao'])} em Ledger Nano S Plus emulada (modelo <code>{esc(meta['modelo'])}</code>).
Última execução: {quando.strftime('%d/%m/%Y %H:%M')} (horário de Brasília){f' · <a href="{run_url}">execução no GitHub Actions</a>' if run_url else ''}</p>
<section class="kpis">
<div class="kpi"><span>Casos de teste</span><strong>{ids}</strong></div>
<div class="kpi"><span>Execuções</span><strong>{total}</strong></div>
<div class="kpi"><span>Aprovadas</span><strong>{aprov}</strong></div>
<div class="kpi"><span>Reprovadas</span><strong>{reprov}</strong></div>
<div class="kpi"><span>Telas capturadas</span><strong>{n_telas}</strong></div>
</section>
<section class="card"><h2>Casos de teste</h2>
<table><thead><tr><th>ID</th><th>Caso</th><th>Categoria</th><th>Variações</th><th>Status</th></tr></thead><tbody>
{''.join(linhas)}
</tbody></table>
<a class="btn" href="pytest/index.html">Abrir relatório detalhado do pytest</a></section>
<section class="card" id="evidencias"><h2>Evidências: telas do aparelho</h2>
<p class="nota">Cada imagem é a tela do aparelho emulado capturada pela API do Speculos durante o teste, na ordem em que a pessoa usuária veria. O texto abaixo de cada tela é o que o teste leu e comparou com o oráculo.</p>
{''.join(blocos)}
</section>
<section class="card"><h2>Como ler este painel</h2>
<p class="nota">Toda chave, endereço e assinatura vem da semente pública de testes do Speculos. Os valores devolvidos pelo app são conferidos com um oráculo independente (biblioteca embit), e as assinaturas são verificadas criptograficamente. Nada aqui usa semente real nem toca a rede Bitcoin.</p></section>
<footer class="rodape">Projeto de portfólio de QA de Pamella Soares · <a href="https://github.com/{repo}">código no GitHub</a></footer>
</main></body></html>"""

(REL / "index.html").write_text(pagina, encoding="utf-8")
print(f"Painel gerado: {aprov} aprovadas, {reprov} reprovadas, {n_telas} telas.")
