# Origem do binário do app

| Campo | Valor |
|---|---|
| Arquivo | `bitcoin-testnet-2.6.0.elf` |
| App | Bitcoin Test (app Bitcoin da Ledger compilado para testnet, `COIN=bitcoin_testnet`) |
| Versão | 2.6.0 |
| Modelo | Nano S Plus (`nanos2` no SDK, `nanosp` no Speculos) |
| SDK | ledger-secure-sdk v27.1.7, API level 27 |
| Código-fonte | https://github.com/LedgerHQ/app-bitcoin-new, commit `f010982d3050e02813cd7129bebd68cf2d1f2099` (branch `develop`, PR #582 "bump_v2.6.0") |
| Como foi obtido | artefato `compiled_app_binaries` da execução oficial de CI https://github.com/LedgerHQ/app-bitcoin-new/actions/runs/42803384224 (10/11/2026) |
| SHA-256 do ELF | `b32a7263e5cb506ed931f05668ac12ca8bba5d5e56d1b8708693d98e835f6676` |
| Licença | Apache-2.0, conforme o repositório de origem |

O binário é usado apenas no emulador. Ele não foi modificado.

Para recompilar a partir do código-fonte, use a imagem oficial de build da Ledger:

```bash
git clone https://github.com/LedgerHQ/app-bitcoin-new && cd app-bitcoin-new
git checkout f010982d3050e02813cd7129bebd68cf2d1f2099
docker run --rm -v "$PWD:/app" -w /app ghcr.io/ledgerhq/ledger-app-builder/ledger-app-builder-lite:latest \
  bash -c 'make BOLOS_SDK=$NANOSP_SDK COIN=bitcoin_testnet'
# resultado em build/nanos2/bin/app.elf
```

Um binário recompilado pode ter SHA-256 diferente, por causa de caminhos e da versão do compilador.
