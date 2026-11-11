"""Assinatura de mensagem e de transacao com aprovacao e rejeicao pelos botoes."""
import base64

import pytest
from embit.ec import PublicKey, Signature
from ledger_bitcoin.exception.errors import DenyError

from qa_ledger import oraculo, transacao
from qa_ledger.dispositivo import EmSegundoPlano, texto_quebrado
from tests.apoio import politica_wpkh, valor_tela

MENSAGEM = b"Teste de QA - portfolio Pamella Soares"
CAMINHO = "m/84h/1h/0h/0/0"


@pytest.mark.caso("CT-08", "Mensagem revisada na tela, assinada e verificada criptograficamente", "Assinatura")
def test_assinar_mensagem(cliente, aparelho):
    tarefa = EmSegundoPlano(lambda: cliente.sign_message(MENSAGEM, CAMINHO.replace("h", "'")))
    telas = aparelho.revisar_e_decidir("Sign message", primeira="Review message")
    tarefa.aguardar()
    assert tarefa.erro is None, tarefa.erro
    textos = {t.textos[0]: t.textos[1:] for t in telas}
    assert textos["Path"] == ["84'/1'/0'/0/0"]
    assert "".join(textos["Message"]) == MENSAGEM.decode(), "mensagem quebrada em linhas tem que ser igual à original"

    assinatura = base64.b64decode(tarefa.resultado)
    assert len(assinatura) == 65
    assert 31 <= assinatura[0] <= 34, "cabeçalho BIP-137 de chave comprimida"
    assert oraculo.verificar_assinatura_mensagem(MENSAGEM, assinatura, CAMINHO)
    # Oráculo negativo: a mesma assinatura não pode valer para outra mensagem nem outra chave.
    assert not oraculo.verificar_assinatura_mensagem(MENSAGEM + b".", assinatura, CAMINHO)
    assert not oraculo.verificar_assinatura_mensagem(MENSAGEM, assinatura, "m/84h/1h/0h/0/1")


@pytest.mark.caso("CT-09", "Assinatura de mensagem rejeitada devolve 0x6985", "Assinatura")
def test_rejeitar_mensagem(cliente, aparelho):
    tarefa = EmSegundoPlano(lambda: cliente.sign_message(MENSAGEM, CAMINHO.replace("h", "'")))
    aparelho.revisar_e_decidir("Reject message", primeira="Review message")
    tarefa.aguardar()
    assert isinstance(tarefa.erro, DenyError)
    assert tarefa.erro.args[0] == "0x6985"


@pytest.mark.caso("CT-10", "Transação revisada (valor, destino, taxa), assinada e verificada", "Assinatura")
def test_assinar_transacao(cliente, aparelho):
    t = transacao.montar()
    tarefa = EmSegundoPlano(lambda: cliente.sign_psbt(t.psbt_b64, politica_wpkh(), None))
    telas = aparelho.revisar_e_decidir("Sign transaction", primeira="Review transaction")
    tarefa.aguardar()
    assert tarefa.erro is None, tarefa.erro

    textos = {t_.textos[0]: t_.textos[1:] for t_ in telas}
    assert textos["Amount"] == [valor_tela(t.valor_envio)]
    assert texto_quebrado(telas, "To") == t.endereco_destino
    assert textos["Fees"] == [valor_tela(t.taxa)]
    tela_toda = " ".join(x.texto for x in telas)
    assert valor_tela(t.valor_troco) not in tela_toda, "troco da própria carteira não deve ser exibido como envio"

    assert len(tarefa.resultado) == 1
    indice, parcial = tarefa.resultado[0]
    pub = oraculo.chave(transacao.ORIGEM).get_public_key()
    assert indice == 0
    assert parcial.pubkey == pub.sec()
    assert parcial.signature[-1] == 0x01, "SIGHASH_ALL"
    assinatura = Signature.parse(parcial.signature[:-1])
    assert pub.verify(assinatura, transacao.sighash_entrada0(t))
    outra = PublicKey.parse(oraculo.chave("m/84h/1h/0h/0/1").get_public_key().sec())
    assert not outra.verify(assinatura, transacao.sighash_entrada0(t))


@pytest.mark.caso("CT-11", "Transação rejeitada devolve 0x6985 e nenhuma assinatura", "Assinatura")
def test_rejeitar_transacao(cliente, aparelho):
    t = transacao.montar()
    tarefa = EmSegundoPlano(lambda: cliente.sign_psbt(t.psbt_b64, politica_wpkh(), None))
    aparelho.revisar_e_decidir("Reject transaction", primeira="Review transaction")
    tarefa.aguardar()
    assert isinstance(tarefa.erro, DenyError)
    assert tarefa.erro.args[0] == "0x6985"
    assert tarefa.resultado is None
