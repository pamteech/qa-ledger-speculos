"""Identificacao do app e chaves publicas sem interacao do usuario."""
import pytest

from qa_ledger import oraculo



@pytest.mark.caso("CT-01", "Nome e versão do app pela biblioteca cliente", "Identificação")
def test_nome_e_versao(cliente, aparelho):
    nome, versao, flags = cliente.get_version()
    assert nome == "Bitcoin Test"
    assert versao == "2.6.0"
    assert isinstance(flags, bytes)
    aparelho.capturar("tela-inicial")


@pytest.mark.caso("CT-02", "Nome e versão pelo APDU padrão do sistema (B0 01)", "Identificação")
def test_apdu_app_e_versao(aparelho):
    dados, sw = aparelho.apdu("b0010000")
    assert sw == 0x9000
    assert dados[0] == 0x01, "byte de formato esperado"
    n = dados[1]
    nome = dados[2:2 + n].decode()
    m = dados[2 + n]
    versao = dados[3 + n:3 + n + m].decode()
    assert (nome, versao) == ("Bitcoin Test", "2.6.0")


@pytest.mark.caso("CT-03", "Impressão digital da semente igual ao oráculo independente", "Identificação")
def test_impressao_digital(cliente):
    assert cliente.get_master_fingerprint().hex() == oraculo.impressao_digital() == "f5acc2fd"


@pytest.mark.caso("CT-04", "Chave pública estendida por caminho padrão igual ao oráculo", "Identificação")
@pytest.mark.parametrize("caminho", ["m/44h/1h/0h", "m/49h/1h/0h", "m/84h/1h/0h", "m/86h/1h/0h"])
def test_xpub_caminhos_padrao(cliente, caminho):
    assert cliente.get_extended_pubkey(caminho.replace("h", "'"), False) == oraculo.xpub(caminho)
