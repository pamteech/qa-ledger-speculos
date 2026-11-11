"""Casos negativos: APDU invalido, caminho de derivacao recusado e recuperacao apos erro."""
import pytest
from ledger_bitcoin.exception.errors import NotSupportedError

from qa_ledger import oraculo


@pytest.mark.caso("CT-12", "APDU inválido devolve a palavra de status correta", "Negativo")
@pytest.mark.parametrize(
    "apdu,sw,motivo",
    [
        ("00010000", 0x6E00, "classe (CLA) não suportada"),
        ("e1ff0000", 0x6D00, "instrução (INS) inexistente"),
        ("e1010000", 0x6D00, "instrução 0x01 não usada pelo app"),
        ("e1000000", 0x6A87, "GET_EXTENDED_PUBKEY sem dados"),
        ("e100000002000101", 0x6A87, "caminho declarado maior que os dados enviados"),
    ],
    ids=["cla", "ins", "ins-01", "sem-dados", "tamanho-errado"],
)
def test_apdu_invalido(aparelho, apdu, sw, motivo):
    dados, status = aparelho.apdu(apdu)
    assert status == sw, f"{motivo}: esperado {sw:#06x}, recebido {status:#06x}"
    assert dados == b""


@pytest.mark.caso("CT-13", "Caminho de derivação fora do padrão é recusado sem confirmação", "Negativo")
@pytest.mark.parametrize("caminho", ["m/84'/1'/1000'", "m/1/2", "m"])
def test_caminho_incomum_sem_tela(cliente, caminho):
    with pytest.raises(NotSupportedError) as erro:
        cliente.get_extended_pubkey(caminho, False)
    assert erro.value.args[0] == "0x6a82"


@pytest.mark.caso("CT-14", "Caminho de rede principal (coin type 0) recusado no app de testnet", "Negativo")
@pytest.mark.parametrize("exibir", [False, True], ids=["sem-tela", "com-tela"])
def test_caminho_mainnet_recusado(cliente, aparelho, exibir):
    with pytest.raises(NotSupportedError) as erro:
        cliente.get_extended_pubkey("m/44'/0'/0'", exibir)
    assert erro.value.args[0] == "0x6a82"
    assert aparelho.textos() == ["Bitcoin Testnet", "app is ready"], "nada deve aparecer para o usuário"


@pytest.mark.caso("CT-15", "App continua respondendo após erros e rejeições", "Negativo")
def test_recupera_apos_erros(cliente, aparelho):
    for apdu in ("00010000", "e1ff0000", "e1000000"):
        aparelho.apdu(apdu)
    assert cliente.get_master_fingerprint().hex() == oraculo.impressao_digital()
    assert cliente.get_extended_pubkey("m/84'/1'/0'", False) == oraculo.xpub("m/84h/1h/0h")
