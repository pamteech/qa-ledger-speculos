"""Exibicao de endereco no aparelho: o que a tela mostra tem que ser o que o app devolve."""
import pytest
from ledger_bitcoin.exception.errors import DenyError

from qa_ledger import oraculo
from qa_ledger.dispositivo import EmSegundoPlano, texto_quebrado
from tests.apoio import politica_wpkh


@pytest.mark.caso("CT-05", "Endereço exibido na tela, aprovado e igual ao devolvido e ao oráculo", "Endereço")
@pytest.mark.parametrize("indice", [0, 7])
def test_endereco_aprovado(cliente, aparelho, indice):
    tarefa = EmSegundoPlano(lambda: cliente.get_wallet_address(politica_wpkh(), None, 0, indice, True))
    telas = aparelho.revisar_e_decidir("Confirm", primeira="Verify bitcoin")
    tarefa.aguardar()
    assert tarefa.erro is None, tarefa.erro
    na_tela = texto_quebrado(telas, "Address")
    esperado = oraculo.endereco_wpkh(f"m/84h/1h/0h/0/{indice}")
    assert tarefa.resultado == esperado
    assert na_tela == esperado, f"tela mostrou {na_tela}"
    assert na_tela.startswith("tb1q"), "endereço segwit nativo de testnet"


@pytest.mark.caso("CT-06", "Endereço rejeitado pelo usuário devolve 0x6985", "Endereço")
def test_endereco_rejeitado(cliente, aparelho):
    tarefa = EmSegundoPlano(lambda: cliente.get_wallet_address(politica_wpkh(), None, 0, 0, True))
    aparelho.revisar_e_decidir("Cancel", primeira="Verify bitcoin")
    tarefa.aguardar()
    assert isinstance(tarefa.erro, DenyError)
    assert tarefa.erro.args[0] == "0x6985"
    assert tarefa.resultado is None, "nenhum endereço pode vazar após rejeição"


@pytest.mark.caso("CT-07", "Chave pública em caminho incomum exige confirmação na tela", "Endereço")
def test_xpub_caminho_incomum_com_tela(cliente, aparelho):
    caminho = "m/84h/1h/1000h"
    tarefa = EmSegundoPlano(lambda: cliente.get_extended_pubkey(caminho.replace("h", "'"), True))
    telas = aparelho.revisar_e_decidir("Approve public key", primeira="Confirm public key")
    tarefa.aguardar()
    assert tarefa.erro is None, tarefa.erro
    caminho_tela = next(t.textos[1] for t in telas if t.textos[0] == "Path")
    assert caminho_tela == "84'/1'/1000'"
    assert texto_quebrado(telas, "Public key") == tarefa.resultado == oraculo.xpub(caminho)
