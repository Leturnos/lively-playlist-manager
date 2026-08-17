# Lively Wallpaper Playlist Manager

Um sistema modular em Python para automatizar a troca de papéis de parede no [Lively Wallpaper](https://rocksdanister.github.io/lively/), com interface visual na bandeja do sistema.

---

## 🚀 Instalação

### Requisitos
- [Python 3.10+](https://www.python.org/)
- [uv](https://github.com/astral-sh/uv)
- [Lively Wallpaper](https://rocksdanister.github.io/lively/)

### Configurando a biblioteca do Lively (passo crítico)

Por padrão, o Lively salva os arquivos temporários de wallpaper em uma pasta interna dele. Este projeto redireciona isso para dentro da própria pasta do projeto, o que permite que o script limpe os arquivos duplicados que o Lively gera a cada troca.

1. Abra o **Lively Wallpaper**
2. Vá em **Configurações → Geral → Arquivo**
3. Aponte o **Local dos planos de fundo** para a pasta `Library` dentro deste projeto:
   ```
   C:\Caminho\Para\Seu\Projeto\Library
   ```

> **Por que isso é necessário?** O comando `setwp` do Lively adiciona cada vídeo à sua biblioteca interna a cada chamada, gerando duplicatas indefinidamente. Com a biblioteca dentro do projeto, o script consegue localizar e apagar essas entradas antes de cada troca. Sem isso, a pasta do Lively acumula gigabytes ao longo do tempo.

### Instalação das dependências

```bash
uv sync
```

### Adicionando wallpapers

Mova seus vídeos (`.mp4`, `.webm`, `.mkv`) para a pasta `wallpapers/` na raiz do projeto.

---

## ▶️ Como rodar

**Uso diário (sem janela de terminal):**
Dê duplo clique em `lively_playlist.vbs`. O programa sobe em segundo plano e aparece como ícone na bandeja do sistema, perto do relógio.

**Com logs visíveis (desenvolvimento):**
```bash
uv run python src/main.pyw
```

**Na inicialização do Windows:**
Pressione `Win+R`, digite `shell:startup` e coloque um atalho para o `lively_playlist.vbs` nessa pasta.

---

## ⚙️ Configuração (`config.json`)

Criado automaticamente na primeira execução. Pode ser editado manualmente ou via interface.

| Chave | Valores | Descrição |
|---|---|---|
| `mode` | `"video"`, `"30s"`, `"1min"`, `"5min"`, `"10min"`, `"30min"`, `"1h"` | Quando trocar o wallpaper |
| `active_wallpapers` | lista de nomes de arquivo | Wallpapers ativos para a lista principal |
| `lively_path` | caminho absoluto | Onde está o `Lively.exe` |
| `rotation_order` | `"shuffle"`, `"sequential"` | Modo de rotação (Aleatório ou Sequencial) |
| `current_playlist` | `"All Wallpapers"` ou nome da sublista | Sublista ativa atualmente selecionada |
| `playlists` | dicionário de `{ nome: [arquivos] }` | Armazena as sublistas de wallpapers criadas |
| `duration_cache` | dicionário de `{ arquivo: segundos }` | Cache com a duração de cada vídeo (melhora performance) |
| `target_monitor` | `null` (padrão) ou número inteiro (`0`, `1`, etc.) | Define um monitor específico para aplicar os wallpapers (omitido por padrão) |

> **Nota:** `mode: null` significa que nenhum modo foi configurado ainda. O programa aguarda você selecionar um pelo menu da bandeja antes de começar a trocar.

---

## 🖱️ Interface

O programa vive na bandeja do sistema. Clique no ícone para abrir o menu:

- **Sublista Ativa (Submenu)** — escolhe qual sublista de papéis de parede usar (gerenciadas pela interface)
- **Tempo de Troca (Submenu)** — define o tempo de permanência de cada vídeo (Duração do vídeo, 30 segundos, 1 min, 5 min, 10 min, 30 min ou 1 hora)
- **Modo de Rotação (Submenu)** — alterna entre rotação **Aleatória (Shuffle)** ou **Sequencial** (ordem alfabética)
- **⏸ Pausar troca / ▶ Retomar troca** — congela na faixa atual, o Lively continua rodando normalmente
- **⏮ Voltar Anterior** — retorna para o wallpaper reproduzido anteriormente usando a pilha de histórico
- **⏭ Próximo agora** — pula para o próximo imediatamente
- **📋 Gerenciar playlist** — abre a interface visual (também abre com clique simples no ícone)

### Gerenciador visual

Interface totalmente em português para controle da biblioteca:
- **Painel de Sublistas:** crie novas playlists zeradas (➕ Nova), renomeie (✏ Renomear) ou apague com confirmação (➖ Excluir)
- Grid de miniaturas responsivo: o número de colunas se **ajusta de forma dinâmica** ao redimensionar ou maximizar a janela (com debounce para evitar lentidão)
- Ativar/desativar wallpapers na sublista selecionada clicando no card ou checkbox
- Filtro inteligente por **Todos / Ativos / Inativos** (se ajusta ao selecionar uma sublista personalizada)
- Busca por nome e atalhos rápidos (**✓ Selecionar Todos / ✗ Desmarcar Todos**) com feedback de hover no cursor
- **▶ Tocar** em qualquer card para ir direto àquele wallpaper
- Badge **"▶ tocando agora"** no card atual, com scroll automático até ele ao abrir

As miniaturas são geradas em background ao iniciar o programa e salvas em `thumbs/`. Na primeira execução com muitos vídeos, os cards aparecem com placeholder e vão sendo preenchidos conforme ficam prontos.

---

## 🛠️ Funcionalidades técnicas

### Detecção de fullscreen & Múltiplos Monitores
O script detecta geometricamente se há um app ou jogo ocupando a tela toda (em qualquer um dos monitores conectados via `MonitorFromWindow` e `GetMonitorInfoW` da Win32 API) e pausa o temporizador enquanto isso acontece — o Lively já pausa o wallpaper nessa situação, e o temporizador acompanha para não pular vídeos enquanto o jogo ou app estiver aberto.
Além disso, quando a tela do Windows é bloqueada (`Win+L`) ou entra em repouso, o temporizador congela automaticamente para economizar ciclos e preservar a playlist.

**Janelas ignoradas na detecção** (não tratadas como fullscreen):
- `WorkerW`, `Progman`, `Shell_TrayWnd`, `Shell_SecondaryTrayWnd` — componentes da área de trabalho e barras de tarefas do Windows
- `TMainBox` — janela overlay do **iTop Easy Desktop**, que cobre a tela toda mesmo sem nada em foco

Se você usar outro app com comportamento parecido e o temporizador travar, rode o script `debug_window.py` para identificar a classe da janela problemática e adicione ao filtro em `src/utils/window_state.py`.

### Limpeza da biblioteca
A cada troca, o script apaga todos os vídeos (`Type: 7`) registrados na biblioteca do Lively em:
- `Library/SaveData/wallpapers/`
- `Library/SaveData/wptmp/`

Wallpapers HTML nativos do Lively (`Type: 1`, como Fluids, Rain, etc.) não são tocados.

### Temporizador com tempo real
O temporizador usa `time.time()` como âncora em vez de contador de ticks. Isso evita drift acumulado e garante que o tempo pausado durante fullscreen não seja contado — o relógio só avança quando o wallpaper está realmente visível.

### Quirks e Controle do Lively CLI
- **Controle por monitor:** O script suporta o envio do argumento `--monitor <id>` caso configurado em `target_monitor` no `config.json` ou passado programmaticamente em `set_wallpaper()`.
- **Controle de playback:** A função `set_lively_playback()` permite pausar/retomar globalmente o reprodutor do Lively usando `Lively.exe app --play <true|false>`.
- O `setwp` só funciona com o Lively já rodando. O script detecta isso via `psutil` e abre o Lively automaticamente se necessário.
- O Lively precisa ter sua janela "acordada" para processar o comando em algumas versões. Se o wallpaper não trocar, verifique se o Lively está minimizado vs. rodando em background.

---

## 📁 Estrutura do projeto

```
.
├── src/
│   ├── main.pyw          # Entry point, gerencia threads
│   ├── config.py         # Carrega/salva config.json, migra chaves legadas
│   ├── lively.py         # Integração com Lively.exe (setwp, limpeza)
│   ├── playlist.py       # Loop principal, temporizador, pausa
│   ├── state.py          # Estado global (eventos de thread e variáveis)
│   ├── ui/
│   │   ├── tray.py       # Ícone e menu da bandeja (pystray)
│   │   ├── manager.py    # Interface visual tkinter (grid de wallpapers)
│   │   └── theme.py      # Paleta de cores (Catppuccin Mocha)
│   └── utils/
│       ├── thumbnails.py # Geração de frames em background
│       ├── window_state.py # Detecção de fullscreen via ctypes
│       └── logger.py     # Log centralizado
├── wallpapers/           # Seus vídeos ficam aqui
├── thumbs/               # Miniaturas geradas automaticamente
├── Library/              # Biblioteca interna do Lively (apontada nas configurações)
├── config.json           # Configuração persistente
├── lively_playlist.vbs   # Launcher sem janela de terminal
└── pyproject.toml
```

---

## 🐛 Problemas conhecidos

**Troca abrupta entre wallpapers** — o Lively não expõe API de transição via CLI. A troca é sempre um corte direto. Tentativas de implementar fade via overlay (ctypes e tkinter) foram testadas e descartadas por causarem artefatos visuais piores que o corte.

**Duplicatas na biblioteca do Lively** — resolvido desde que a biblioteca esteja apontada para dentro do projeto (ver instalação). Se começar a acumular entradas duplicadas novamente, verifique se o caminho em Configurações do Lively ainda está correto.

---

## 📦 Dependências

| Pacote | Uso |
|---|---|
| `moviepy` | Leitura de duração e extração de frames para thumbnails |
| `psutil` | Verificar se o processo do Lively está rodando |
| `pystray` | Ícone e menu na bandeja do sistema |
| `Pillow` | Processamento de imagens para thumbnails e ícone da bandeja |