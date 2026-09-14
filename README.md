<div align="center">

# 🖨️ Klipper Gcode Sync

**A portable Windows app to sync 3D-printer gcode files across multiple Klipper/Moonraker printers, with a Mainsail-style file browser.**
**Una app portable para Windows que sincroniza gcodes entre varias impresoras Klipper/Moonraker, con un explorador de archivos al estilo Mainsail.**

</div>

---

## Screenshots

`docs/screenshot-sync.png` — Sync screen with live per-printer progress
`docs/screenshot-explorer.png` — Mainsail-style remote file browser with thumbnails
`docs/screenshot-printers.png` — Printer CRUD screen

---

# English

## What is this?

If you run **multiple 3D printers on Klipper/Moonraker** and manage your
gcode library from a Windows PC, this app replaces a manual `rsync`/SFTP
workflow with a single portable `.exe`:

- Your PC folder is the **single source of truth**. Push changes to as
  many printers as you want, in parallel.
- Before touching any file, it asks **Moonraker** whether that printer is
  currently printing or has the file queued — protected files are never
  touched, and the app tells you which ones to sync later by hand.
- A **Mainsail-style remote file browser**: navigate folders, see each
  model's real thumbnail, hover to preview it enlarged, and delete files
  (or whole folders) directly on a printer.
- Full **CRUD for printers** (add/edit/delete/reorder), a dark UI with a
  configurable accent color (red by default), and everything ships as a
  single portable `.exe` — no installer, no admin rights needed.

This started as a console Python script (`sync_gcodes.py`) used to
replace an unreliable printer-to-printer `rsync` chain; this repo is the
GUI evolution of that script, keeping the same sync logic (byte-size
comparison, retries, thumbnail cleanup, parallel sync) but wrapped in a
proper interface.

## Features

- 🔄 **Parallel sync** to all selected printers, with live per-printer
  progress, speed/ETA, and a colored log console.
- 🧪 **Dry-run mode** to preview what would change without touching
  anything.
- 🖨️ **Printer CRUD**: add, edit, delete, reorder — per-printer overrides
  for SSH port / Moonraker port / remote path.
- 📁 **Remote file explorer**: breadcrumb folder navigation, real gcode
  thumbnails (downloaded from `.thumbs/`), enlarge-on-hover preview,
  bulk delete (including whole folders), protected-file badges.
- 🛡️ **Print-safety first**: any file currently printing or queued in
  Moonraker is never uploaded over or deleted — it's skipped and listed
  for you to handle manually.
- 🎨 **Configurable theme**: dark background with a configurable accent
  color (defaults to red), applied consistently across a custom icon
  set (no emoji, no external assets).
- 💼 **Portable**: builds to a single `.exe` via PyInstaller. Config
  files live next to the executable — copy the folder to a USB stick
  and it still works.

## Requirements

- Windows 10/11 (the packaged `.exe` targets Windows; running from
  source works on Linux/macOS too, but the sync engine assumes SSH
  access to a Linux-based Klipper host either way).
- Python 3.10+ (only needed to run from source or to build the `.exe`
  yourself).
- SSH access to each printer's host (e.g. the `rpi` user on a
  Raspberry Pi running Klipper/Moonraker), and Moonraker reachable over
  HTTP on each printer.

## Setting up your Raspberry Pis

This section assumes the same environment I built and tested this on:
**one Raspberry Pi per printer**, each running its own Klipper +
Moonraker install, with the **same SSH username and password on every
Pi**. That's exactly why `ssh_user` / `ssh_password` are global fields
in `printers.json` instead of per-printer ones — you only type them
once and every printer uses them.

### 1. Give each Raspberry Pi a fixed IP

The app connects to each printer by IP address (stored in
`printers.json`), so if a Pi's IP changes — which happens by default,
since most routers assign IPs dynamically via DHCP — the app will stop
finding it and you'll have to update the config every time.

Two ways to fix this, pick one:

- **DHCP reservation on your router (recommended)**: in your router's
  admin panel, reserve an IP for each Pi's MAC address. The Pi still
  gets its IP via DHCP, but it's always the same one. This is the
  cleanest option because the Pi's own network config never changes.
- **Static IP on the Pi itself**: edit `/etc/dhcpcd.conf` (or use
  `nmcli`/`nmtui` on newer Raspberry Pi OS versions using
  NetworkManager) and set a fixed IP outside your router's DHCP range,
  to avoid conflicts with other devices.

Either way, once each printer has a fixed IP, that's the `host` value
you'll type into the app.

### 2. Make sure SSH is enabled and reachable

- Enable SSH if it isn't already (`sudo raspi-config` → *Interface
  Options* → *SSH*, or drop an empty file named `ssh` on the boot
  partition before first boot).
- Confirm you can log in manually first: `ssh fixer@192.168.1.5x` (or
  whatever user/IP you use) from the same Windows PC you'll run the app
  from. This also makes your PC accept the Pi's SSH host key the first
  time, which avoids a surprise on the first real sync.
- Confirm Moonraker is running and reachable on its default port
  (`7125`) — if you're using Mainsail/Fluidd, it already is.

### 3. Check your gcodes path matches `printer.cfg`

The `remote_gcodes_path` setting has to match the `path:` under
`[virtual_sdcard]` in each printer's `printer.cfg`. In a typical
KIAUH-based install this is `/home/<user>/printer_data/gcodes` — just
make sure it's the same across all your Pis (it should be, if you set
them up the same way), so you only need to set it once as the global
default.

### 4. Add each printer in the app

Once a Pi has a fixed IP, SSH working, and Moonraker reachable:

1. Open **Impresoras** → **Agregar impresora**.
2. Give it a name (e.g. `Mark4`) and its fixed IP as the host.
3. Leave SSH port / Moonraker port / remote path **empty** unless this
   specific printer is different from your global defaults — the app
   falls back to whatever you set in **Configuración**.

That's it — it'll show up as a checkbox in **Sincronizar** and in the
printer dropdown in **Explorador remoto**.

### A note on pre-built Klipper printers

This app was built and tested only against **self-assembled printers
running a plain Klipper/Moonraker install on a Raspberry Pi**, all
sharing the same SSH credentials. It *should* work with printers that
ship with Klipper pre-installed from the factory (Creality K1/K1C,
Sovol SV07, Elegoo Centauri Carbon, etc.) as long as you can SSH into
them and reach Moonraker — the per-printer `ssh_port` /
`moonraker_port` / `remote_gcodes_path` overrides exist specifically
for cases like these, where the defaults might not match. But since I
don't own one of these printers, **I haven't been able to test or
tune the app for them** — things like a different default user/SSH
setup, a locked-down shell, or a nonstandard gcodes path could trip it
up in ways I can't predict from here.

**If you have one of these printers and want to help figure out what
needs to change, please reach out or just open an issue / PR.** I'd rather get it right with
real hardware feedback than guess.

## Getting started (from source)

```bash
git clone https://github.com/JLVFixer/Klipper-Gcode-Sync.git
cd klipper-sync-gui
pip install -r requirements.txt
python main.py
```

The first run creates empty `printers.json` and `settings.json` next to
`main.py`. From there:

1. Go to **Configuración** and set your SSH user/password, default
   remote gcodes path, and default SSH/Moonraker ports.
2. Go to **Impresoras** and add each printer (name + host; per-printer
   port/path overrides are optional).
3. Go to **Sincronizar**, pick your local gcodes folder, select which
   printers to sync, and hit **Sincronizar ahora** (or check **dry-run**
   first to preview).
4. Go to **Explorador remoto** to browse and clean up what's already on
   a printer.

If you already have a `printers.json` from the console script version,
just drop it in this folder — the format is 100% compatible.

## Building the portable `.exe`

PyInstaller builds for the OS it runs on, so this step needs to run on
**Windows**:

```powershell
pip install -r requirements.txt
pip install pyinstaller
pyinstaller build.spec --clean
```

The result is `dist\KlipperSync.exe` — copy it anywhere, it's fully
portable. `printers.json` / `settings.json` are created next to it on
first run.

To use your own icon: drop an `icon.ico` in `assets/`, uncomment the
`icon=` line in `build.spec`, and rebuild.

## Configuration reference (`printers.json`)

| Key | Scope | Description |
|---|---|---|
| `local_gcodes_dir` | global | Local "master" folder synced to every printer |
| `ssh_user` | global | SSH username used for every printer |
| `ssh_password` | global | SSH password, stored in **plain text** (see below) |
| `remote_gcodes_path` | global* | Default remote gcodes folder |
| `ssh_port` | global* | Default SSH port |
| `moonraker_port` | global* | Default Moonraker HTTP port |
| `printers[].name` | printer | Display name (must be unique) |
| `printers[].host` | printer | IP address or hostname |
| `printers[].ssh_port` | printer | Overrides the global SSH port for this printer (optional) |
| `printers[].moonraker_port` | printer | Overrides the global Moonraker port (optional) |
| `printers[].remote_gcodes_path` | printer | Overrides the global remote path (optional) |

\* Global values are the default; any printer can override them
individually.

## Security notes

- The SSH password is stored **in plain text** in `printers.json`, by
  design (same as the original console script, for simplicity). Do not
  commit this file or share it — it's already covered by `.gitignore`
  in this repo, but double-check before pushing.
- The remote file explorer refuses to delete anything Moonraker reports
  as currently printing or queued, even if you select it.

## Project structure

```
main.py                  # entry point
core/
  sync_engine.py          # sync logic (size comparison, retries, thumbnails, explorer helpers)
  store.py                # printers.json / settings.json CRUD
  theme.py                # QSS stylesheet generator (dark + configurable accent)
  icons.py                # hand-drawn vector icon set (no external assets)
  resources.py            # resolves asset paths in dev vs. packaged (.exe) mode
gui/
  main_window.py          # sidebar + page navigation
  workers.py              # QThreads wrapping the sync engine for a non-blocking UI
  pages/
    sync_page.py           # sync screen
    printers_page.py        # printer CRUD
    explorer_page.py        # Mainsail-style remote file browser
    settings_page.py        # SSH credentials, defaults, theme
build.spec                # PyInstaller spec (--onefile)
```

## Known limitations / roadmap

- No live temperature/print-progress dashboard yet.
- No scheduled/automatic sync (Task Scheduler on Windows works fine as
  a workaround in the meantime).
- Password is plain text by design; a Windows Credential Manager /
  master-password option could be added later if there's interest.

Contributions and issues are welcome.

## Acknowledgments

The remote file browser's UX is deliberately inspired by
[Mainsail](https://github.com/mainsail-crew/mainsail)'s file manager.
This project is not affiliated with Mainsail, Moonraker, or Klipper —
just built to work well alongside them.

---

# Español

## ¿Qué es esto?

Si manejás **varias impresoras 3D con Klipper/Moonraker** y administrás
tu biblioteca de gcodes desde una PC con Windows, esta app reemplaza un
flujo manual de `rsync`/SFTP por un único `.exe` portable:

- Tu carpeta en la PC es la **única fuente de verdad**. Empujá los
  cambios a todas las impresoras que quieras, en paralelo.
- Antes de tocar un archivo, le pregunta a **Moonraker** si esa
  impresora está imprimiendo o tiene el archivo en cola — los archivos
  protegidos nunca se tocan, y la app te avisa cuáles sincronizar a mano
  más tarde.
- Un **explorador remoto al estilo Mainsail**: navegás por carpetas, ves
  el thumbnail real de cada modelo, lo agrandás con el mouse encima, y
  podés borrar archivos (o carpetas enteras) directo en la impresora.
- **CRUD completo de impresoras** (agregar/editar/eliminar/reordenar),
  interfaz oscura con color de acento configurable (rojo por defecto), y
  todo empaquetado en un único `.exe` portable — sin instalador, sin
  permisos de administrador.

Esto arrancó como un script de consola en Python (`sync_gcodes.py`) para
reemplazar una cadena de `rsync` entre impresoras poco confiable; este
repo es la evolución con interfaz gráfica de ese script, manteniendo la
misma lógica de sincronización (comparación por tamaño, reintentos,
limpieza de thumbnails, sync en paralelo) pero con una interfaz como
corresponde.

## Funciones

- 🔄 **Sincronización en paralelo** a todas las impresoras seleccionadas,
  con progreso en vivo por impresora, velocidad/ETA, y consola de log
  coloreada.
- 🧪 **Modo dry-run** para ver qué cambiaría sin tocar nada todavía.
- 🖨️ **CRUD de impresoras**: agregar, editar, eliminar, reordenar —
  con overrides por impresora de puerto SSH / puerto Moonraker / ruta
  remota.
- 📁 **Explorador remoto**: navegación por carpetas con breadcrumb,
  thumbnails reales de cada gcode (descargados de `.thumbs/`), preview
  agrandado al pasar el mouse, borrado masivo (incluyendo carpetas
  enteras), e indicador de archivos protegidos.
- 🛡️ **La impresión nunca se interrumpe**: ningún archivo que esté
  imprimiéndose o en cola en Moonraker se sube ni se borra — se saltea
  y se lista para que lo resuelvas a mano.
- 🎨 **Tema configurable**: fondo oscuro con color de acento configurable
  (rojo por defecto), aplicado de forma consistente en un set de íconos
  propio (sin emojis, sin assets externos).
- 💼 **Portable**: se compila a un único `.exe` con PyInstaller. Los
  archivos de configuración viven al lado del ejecutable — copiá la
  carpeta a un pendrive y sigue funcionando.

## Requisitos

- Windows 10/11 (el `.exe` empaquetado apunta a Windows; correr desde
  código fuente también funciona en Linux/macOS, aunque el motor de
  sync de todas formas asume acceso SSH a un host Linux con Klipper).
- Python 3.10+ (solo hace falta para correr desde código fuente o para
  compilar vos mismo el `.exe`).
- Acceso SSH a cada impresora (ej. el usuario `rpi` en una Raspberry
  Pi con Klipper/Moonraker), y Moonraker accesible por HTTP en cada una.

## Configurar las Raspberry Pi

Esta sección asume el mismo entorno en el que armé y probé todo esto:
**una Raspberry Pi por impresora**, cada una con su propio Klipper +
Moonraker instalado, y **el mismo usuario y contraseña SSH en todas**.
Por eso `ssh_user` / `ssh_password` son campos globales en
`printers.json` en vez de por-impresora: los cargás una sola vez y
sirven para todas.

### 1. Ponele una IP fija a cada Raspberry Pi

La app se conecta a cada impresora por dirección IP (guardada en
`printers.json`), así que si la IP de una Pi cambia —algo que pasa por
defecto, ya que la mayoría de los routers asignan IPs dinámicas por
DHCP— la app va a dejar de encontrarla y vas a tener que actualizar la
configuración cada vez.

Dos formas de solucionarlo, elegí una:

- **Reserva DHCP en el router (recomendado)**: en el panel de admin de
  tu router, reservá una IP para la MAC de cada Pi. La Pi sigue
  recibiendo su IP por DHCP, pero siempre es la misma. Es la opción más
  prolija porque la configuración de red de la Pi en sí no cambia nunca.
- **IP estática en la propia Pi**: editá `/etc/dhcpcd.conf` (o usá
  `nmcli`/`nmtui` en versiones más nuevas de Raspberry Pi OS que usan
  NetworkManager) y fijá una IP fuera del rango DHCP de tu router, para
  evitar conflictos con otros dispositivos.

Cualquiera de las dos, una vez que cada impresora tiene IP fija, ese es
el valor de `host` que vas a cargar en la app.

### 2. Asegurate de que SSH esté habilitado y accesible

- Habilitá SSH si todavía no lo está (`sudo raspi-config` → *Interface
  Options* → *SSH*, o dejá un archivo vacío llamado `ssh` en la
  partición de boot antes del primer arranque).
- Confirmá que podés entrar manualmente primero: `ssh fixer@192.168.1.5x`
  (o el usuario/IP que uses) desde la misma PC Windows donde vas a
  correr la app. Esto también hace que tu PC acepte la clave SSH de la
  Pi la primera vez, para que no te sorprenda en la primera sync real.
- Confirmá que Moonraker está corriendo y accesible en su puerto por
  defecto (`7125`) — si usás Mainsail/Fluidd, ya lo está.

### 3. Revisá que la ruta de gcodes coincida con el `printer.cfg`

El campo `remote_gcodes_path` tiene que coincidir con el `path:` de
`[virtual_sdcard]` en el `printer.cfg` de cada impresora. En una
instalación típica con KIAUH suele ser
`/home/<usuario>/printer_data/gcodes` — asegurate de que sea igual en
todas tus Pis (debería serlo, si las armaste todas de la misma forma),
así lo configurás una sola vez como default global.

### 4. Agregá cada impresora en la app

Una vez que una Pi tiene IP fija, SSH funcionando, y Moonraker
accesible:

1. Abrí **Impresoras** → **Agregar impresora**.
2. Ponele un nombre (ej. `Mark4`) y su IP fija como host.
3. Dejá el puerto SSH / puerto Moonraker / ruta remota **vacíos** salvo
   que esa impresora puntual sea distinta de tus defaults globales — la
   app usa lo que hayas cargado en **Configuración**.

Listo — va a aparecer como checkbox en **Sincronizar** y en el
desplegable de impresoras del **Explorador remoto**.

### Una aclaración sobre impresoras con Klipper de fábrica

Esta app la armé y probé solamente contra **impresoras autoensambladas
corriendo una instalación estándar de Klipper/Moonraker en una
Raspberry Pi**, todas con las mismas credenciales SSH. *Debería*
funcionar también con impresoras que ya vienen con Klipper instalado de
fábrica (Creality K1/K1C, Sovol SV07, Elegoo Centauri Carbon, etc.)
siempre que puedas entrar por SSH y llegar a Moonraker — los overrides
por impresora de `ssh_port` / `moonraker_port` / `remote_gcodes_path`
existen justamente para casos así, donde los valores por defecto
podrían no coincidir. Pero como no tengo ninguna de esas impresoras,
**no pude probarla ni ajustarla para ese caso**: cosas como un
usuario/SSH distinto por defecto, una shell restringida, o una ruta de
gcodes no estándar podrían romper algo de una forma que no puedo prever
desde acá.

**Si tenés una impresora de esas y querés ayudar a ver qué hay que
cambiar, escribime o directamente abrí un issue o un PR.** Prefiero resolverlo con feedback
de hardware real antes que adivinar.

## Empezar (desde código fuente)

```bash
git clone https://github.com/JLVFixer/Klipper-Gcode-Sync.git
cd klipper-sync-gui
pip install -r requirements.txt
python main.py
```

La primera corrida crea `printers.json` y `settings.json` vacíos al lado
de `main.py`. A partir de ahí:

1. Andá a **Configuración** y cargá tu usuario/contraseña SSH, la ruta
   remota de gcodes por defecto, y los puertos SSH/Moonraker por
   defecto.
2. Andá a **Impresoras** y agregá cada una (nombre + host; los overrides
   de puerto/ruta por impresora son opcionales).
3. Andá a **Sincronizar**, elegí tu carpeta local de gcodes, marcá qué
   impresoras sincronizar, y apretá **Sincronizar ahora** (o activá
   **dry-run** primero para ver qué haría).
4. Andá a **Explorador remoto** para navegar y limpiar lo que ya está en
   una impresora.

Si ya tenés un `printers.json` de la versión de consola, simplemente
copialo a esta carpeta — el formato es 100% compatible.

## Compilar el `.exe` portable

PyInstaller compila para el sistema operativo en el que corre, así que
este paso tiene que hacerse en **Windows**:

```powershell
pip install -r requirements.txt
pip install pyinstaller
pyinstaller build.spec --clean
```

El resultado es `dist\KlipperSync.exe` — copialo a donde quieras, es
totalmente portable. `printers.json` / `settings.json` se crean al lado
la primera vez que lo corrés.

Para usar tu propio ícono: poné un `icon.ico` en `assets/`, descomentá
la línea `icon=` en `build.spec`, y recompilá.

## Referencia de configuración (`printers.json`)

| Clave | Alcance | Descripción |
|---|---|---|
| `local_gcodes_dir` | global | Carpeta local "maestra" que se sincroniza a cada impresora |
| `ssh_user` | global | Usuario SSH usado para todas las impresoras |
| `ssh_password` | global | Contraseña SSH, guardada en **texto plano** (ver abajo) |
| `remote_gcodes_path` | global* | Carpeta remota de gcodes por defecto |
| `ssh_port` | global* | Puerto SSH por defecto |
| `moonraker_port` | global* | Puerto HTTP de Moonraker por defecto |
| `printers[].name` | impresora | Nombre visible (debe ser único) |
| `printers[].host` | impresora | Dirección IP o hostname |
| `printers[].ssh_port` | impresora | Pisa el puerto SSH global para esta impresora (opcional) |
| `printers[].moonraker_port` | impresora | Pisa el puerto Moonraker global (opcional) |
| `printers[].remote_gcodes_path` | impresora | Pisa la ruta remota global (opcional) |

\* Los valores globales son el default; cualquier impresora puede
pisarlos individualmente.

## Notas de seguridad

- La contraseña SSH se guarda **en texto plano** en `printers.json`, a
  propósito (igual que el script de consola original, por simplicidad).
  No subas ni compartas ese archivo — este repo ya lo ignora en
  `.gitignore`, pero revisalo igual antes de hacer push.
- El explorador remoto se niega a borrar cualquier archivo que Moonraker
  reporte como imprimiéndose o en cola, aunque lo hayas seleccionado.

## Estructura del proyecto

```
main.py                  # punto de entrada
core/
  sync_engine.py          # lógica de sync (comparación por tamaño, reintentos, thumbnails, explorador)
  store.py                # CRUD de printers.json / settings.json
  theme.py                # generador de QSS (tema oscuro + acento configurable)
  icons.py                # set de íconos vectoriales dibujados a mano (sin assets externos)
  resources.py            # resuelve rutas de assets en modo dev vs empaquetado (.exe)
gui/
  main_window.py          # sidebar + navegación de páginas
  workers.py              # QThreads que envuelven el motor de sync sin trabar la UI
  pages/
    sync_page.py           # pantalla de sincronización
    printers_page.py        # CRUD de impresoras
    explorer_page.py        # explorador remoto estilo Mainsail
    settings_page.py        # credenciales SSH, defaults, tema
build.spec                # spec de PyInstaller (--onefile)
```

## Limitaciones conocidas / roadmap

- Todavía no hay dashboard de temperaturas/progreso de impresión en vivo.
- No hay sincronización automática programada (el Programador de tareas
  de Windows sirve como workaround mientras tanto).
- La contraseña es texto plano a propósito; se podría sumar más adelante
  una opción de Windows Credential Manager / contraseña maestra si hay
  interés.

Se aceptan contribuciones e issues.

## Agradecimientos

La UX del explorador remoto está deliberadamente inspirada en
[Mainsail](https://github.com/mainsail-crew/mainsail). Este proyecto no
está afiliado a Mainsail, Moonraker ni Klipper — solo está pensado para
funcionar bien junto a ellos.