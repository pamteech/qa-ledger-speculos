from decimal import Decimal

from ledger_bitcoin import WalletPolicy

from qa_ledger import oraculo

CONTA = "m/84h/1h/0h"


def politica_wpkh() -> WalletPolicy:
    """Carteira padrao BIP-84 (segwit nativo) da conta 0 na testnet."""
    origem = f"[{oraculo.impressao_digital()}/84'/1'/0']{oraculo.xpub(CONTA)}"
    return WalletPolicy("", "wpkh(@0/**)", [origem])


def valor_tela(satoshis: int) -> str:
    """Formato que o app usa para valores: BTC sem zeros a direita e o ticker TEST."""
    texto = format(Decimal(satoshis) / Decimal(100_000_000), "f").rstrip("0").rstrip(".")
    return f"{texto} TEST"
