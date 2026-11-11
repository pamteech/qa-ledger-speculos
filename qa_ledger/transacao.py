"""Monta uma PSBT de teste (rede testnet) com entrada e troco da carteira padrao do Speculos."""
from __future__ import annotations

from dataclasses import dataclass

from embit import bip32, script
from embit.psbt import PSBT, DerivationPath
from embit.transaction import Transaction, TransactionInput, TransactionOutput

from qa_ledger import oraculo

ORIGEM = "m/84h/1h/0h/0/0"
TROCO = "m/84h/1h/0h/1/0"
DESTINO = "m/84h/1h/0h/0/5"


@dataclass
class TransacaoTeste:
    psbt_b64: str
    tx: Transaction
    valor_entrada: int
    valor_envio: int
    valor_troco: int
    endereco_destino: str

    @property
    def taxa(self) -> int:
        return self.valor_entrada - self.valor_envio - self.valor_troco


def montar(valor_entrada=100_000, valor_envio=60_000, valor_troco=39_000) -> TransacaoTeste:
    fp = bytes.fromhex(oraculo.impressao_digital())
    pub_origem = oraculo.chave(ORIGEM).get_public_key()
    pub_troco = oraculo.chave(TROCO).get_public_key()
    spk_origem = script.p2wpkh(pub_origem)
    destino = script.p2wpkh(oraculo.chave(DESTINO).get_public_key())

    # Transacao anterior ficticia que "pagou" o endereco de origem. Nao existe na rede.
    anterior = Transaction(vin=[TransactionInput(bytes(32), 0)], vout=[TransactionOutput(valor_entrada, spk_origem)])
    tx = Transaction(
        vin=[TransactionInput(anterior.txid(), 0)],
        vout=[TransactionOutput(valor_envio, destino), TransactionOutput(valor_troco, script.p2wpkh(pub_troco))],
    )
    psbt = PSBT(tx)
    psbt.inputs[0].non_witness_utxo = anterior
    psbt.inputs[0].witness_utxo = anterior.vout[0]
    psbt.inputs[0].bip32_derivations[pub_origem] = DerivationPath(fp, bip32.parse_path(ORIGEM))
    psbt.outputs[1].bip32_derivations[pub_troco] = DerivationPath(fp, bip32.parse_path(TROCO))
    return TransacaoTeste(psbt.to_string(), tx, valor_entrada, valor_envio, valor_troco, destino.address(oraculo.REDE))


def sighash_entrada0(t: TransacaoTeste) -> bytes:
    pub = oraculo.chave(ORIGEM).get_public_key()
    return t.tx.sighash_segwit(0, script.p2pkh(pub), t.valor_entrada)
