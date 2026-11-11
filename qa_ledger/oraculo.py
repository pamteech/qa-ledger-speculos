"""Oraculo independente do dispositivo.

Deriva chaves, enderecos e verifica assinaturas a partir da mnemonica padrao
do Speculos usando a biblioteca embit, sem consultar o app da Ledger. Se o app
e o oraculo concordam, o resultado do dispositivo esta correto.

ATENCAO: a mnemonica abaixo e publica, vem do proprio Speculos e serve apenas
para testes. Nunca use em carteira real nem envie fundos para esses enderecos.
"""
from embit import bip32, bip39, ec, script
from embit.hashes import double_sha256
from embit.networks import NETWORKS
from embit.compact import to_bytes as compact

MNEMONICA_TESTE = (
    "glory promote mansion idle axis finger extra february uncover one trip resource "
    "lawn turtle enact monster seven myth punch hobby comfort wild raise skin"
)
REDE = NETWORKS["test"]

_raiz = bip32.HDKey.from_seed(bip39.mnemonic_to_seed(MNEMONICA_TESTE), version=REDE["xprv"])


def impressao_digital() -> str:
    return _raiz.my_fingerprint.hex()


def chave(caminho: str) -> bip32.HDKey:
    return _raiz.derive(caminho)


def xpub(caminho: str) -> str:
    return chave(caminho).to_public().to_base58(version=REDE["xpub"])


def endereco_wpkh(caminho: str) -> str:
    return script.p2wpkh(chave(caminho).get_public_key()).address(REDE)


def hash_mensagem(mensagem: bytes) -> bytes:
    prefixo = b"\x18Bitcoin Signed Message:\n"
    return double_sha256(prefixo + compact(len(mensagem)) + mensagem)


def verificar_assinatura_mensagem(mensagem: bytes, assinatura65: bytes, caminho: str) -> bool:
    """Verifica uma assinatura compacta (65 bytes, formato BIP-137) com a chave publica esperada."""
    if len(assinatura65) != 65:
        return False
    r = int.from_bytes(assinatura65[1:33], "big")
    s = int.from_bytes(assinatura65[33:65], "big")
    return verificar_rs(hash_mensagem(mensagem), r, s, chave(caminho).get_public_key())


def _der_int(n: int) -> bytes:
    b = n.to_bytes(32, "big").lstrip(b"\x00") or b"\x00"
    if b[0] & 0x80:
        b = b"\x00" + b
    return b"\x02" + bytes([len(b)]) + b


def verificar_rs(digest: bytes, r: int, s: int, pub: ec.PublicKey) -> bool:
    corpo = _der_int(r) + _der_int(s)
    der = b"\x30" + bytes([len(corpo)]) + corpo
    return pub.verify(ec.Signature.parse(der), digest)
