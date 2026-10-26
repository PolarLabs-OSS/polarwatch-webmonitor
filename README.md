<div align="center">

<img src="assets/polarwatch_neon_logo.png" alt="PolarWatch Web Monitor - logo ufficiale" width="320">

# PolarWatch Web Monitor

**Il tuo monitor dei siti web. Essenziale, locale, gratuito.**

[![Build desktop](https://github.com/PolarLabs-OSS/polarwatch-webmonitor/actions/workflows/release.yml/badge.svg)](https://github.com/PolarLabs-OSS/polarwatch-webmonitor/actions/workflows/release.yml)
![MIT](https://img.shields.io/badge/License-MIT-62dcdc)
![Windows and Linux](https://img.shields.io/badge/Windows%20%7C%20Linux-x64%20%7C%20ARM64-143449)

**[Scarica per Windows e Linux](https://github.com/PolarLabs-OSS/polarwatch-webmonitor/releases/latest)** · **[Codice sorgente](https://github.com/PolarLabs-OSS/polarwatch-webmonitor)**

</div>

## Cos'è

PolarWatch è un'app desktop **open source** realizzata da **PolarLabs** per controllare rapidamente lo stato dei siti web, senza creare account e senza servizi cloud. Il monitor funziona localmente; le verifiche HTTP(S) vengono effettuate dalla tua connessione Internet.

L'interfaccia moderna mostra immediatamente **siti monitorati, online/offline, tempo di risposta e scadenza del certificato TLS**. Per chi vuole approfondire c'è la **Modalità Esperto**, completamente gratuita.

## Download

| Sistema operativo | CPU | Pacchetto |
|---|---|---|
| Windows 10/11 | x64 (Intel / AMD) | [Windows x64](https://github.com/PolarLabs-OSS/polarwatch-webmonitor/releases/latest) |
| Windows 11 | ARM64 (Surface / Snapdragon) | [Windows ARM64](https://github.com/PolarLabs-OSS/polarwatch-webmonitor/releases/latest) |
| Linux desktop | x64 | [Linux x64](https://github.com/PolarLabs-OSS/polarwatch-webmonitor/releases/latest) |
| Linux desktop | ARM64 | [Linux ARM64](https://github.com/PolarLabs-OSS/polarwatch-webmonitor/releases/latest) |

Scarica l'archivio associato al tuo sistema operativo, estrailo e avvia il programma. Su Windows l'archivio include il file `PolarWatch-WebMonitor.exe`. Su Linux, dopo aver estratto il file TAR.GZ:

```bash
chmod +x PolarWatch-WebMonitor
./PolarWatch-WebMonitor
```

Su Linux serve un desktop grafico con X11 o Wayland/XWayland. La compatibilità dipende dalla distribuzione e dalle librerie disponibili. **I binari non sono firmati digitalmente**: non disattivare le protezioni del sistema operativo per avviarli.

## Funzionalità

- **Stato immediato:** online / offline e codice HTTP.
- **Prestazioni:** latenza, TTFB e grafico delle ultime verifiche della sessione.
- **Certificati:** versione TLS, suite crittografica, scadenza e giorni residui.
- **Rete:** risoluzione DNS e indirizzi IP.
- **Redirect:** URL finale e presenza di reindirizzamenti.
- **Header di sicurezza:** HSTS, CSP, X-Content-Type-Options, Referrer-Policy e Permissions-Policy (solo controllo della presenza).
- **Report:** copia i risultati tecnici negli appunti.
- **Intervalli:** controlli manuali oppure automatici ogni 1, 5, 15, 30 o 60 minuti.

Il monitoraggio è attivo **solo quando l'app rimane aperta**. Non garantisce una disponibilità del 100% e non sostituisce un servizio di monitoraggio esterno continuo.

## Nessun database

PolarWatch **non richiede SQLite, Supabase o un server**. Salva soltanto un piccolo file JSON con l'elenco dei nomi e degli URL dei siti aggiunti. Lo storico dei tempi di risposta resta esclusivamente nella RAM e viene cancellato alla chiusura.

| Sistema | File configurazione |
|---|---|
| Windows | `%LOCALAPPDATA%\PolarLabs\PolarWatch\sites.json` |
| Linux | `~/.config/polarlabs/polarwatch/sites.json` (o `$XDG_CONFIG_HOME`) |

Nessun wallet, miner, credenziale, sistema di licensing o backend è incluso in questo progetto. Le verifiche HTTP, DNS e TLS sono richieste di rete verso i siti che scegli di monitorare.

## Avvio da sorgente

Richiede **Python 3.13**.

```bash
git clone https://github.com/PolarLabs-OSS/polarwatch-webmonitor.git
cd polarwatch-webmonitor
python -m pip install -r requirements.txt
python polarwatch_sites.py
```

Per eseguire i test:

```bash
python -m unittest discover -s tests_monitor -p "test_*.py" -v
```

Su Linux, se necessario, esegui prima `sudo apt install python3-tk`. Per l'avvio senza desktop grafico dei test GUI, utilizza `xvfb-run -a`.

## Struttura

```text
polarwatch_sites.py           Avvio applicazione
polarwatch_modern_ui.py       Interfaccia CustomTkinter
polarwatch_monitor_core.py    HTTP, DNS, TLS e JSON locale
assets/                       Logo neon e icone PNG/ICO
tests_monitor/                Test funzionali e GUI
scripts/                      Build, packaging e test delle release
.github/workflows/release.yml CI per Windows/Linux x64/ARM64
```

## Licenza e sicurezza

**MIT License** — copyright 2026 Space Services SRLS / PolarLabs.

Leggi [SECURITY.md](SECURITY.md) per note di sicurezza e segnalazioni. La presenza degli header di sicurezza non equivale a un audit di sicurezza completo.

---

<div align="center"><b>PolarLabs</b> — Non serve fare di più. Serve farlo meglio.</div>
