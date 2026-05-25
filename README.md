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
| `mode` | `"video"`, `"1min"`, `"5min"` | Quando trocar o wallpaper |
| `active_wallpapers` | lista de nomes de arquivo | Quais vídeos entram na rotação. Lista vazia = todos ativos |
| `lively_path` | caminho absoluto | Onde está o `Lively.exe` |

> **Nota:** `mode: null` significa que nenhum modo foi configurado ainda. O programa aguarda você selecionar um pelo menu da bandeja antes de começar a trocar.

---

## 🖱️ Interface

O programa vive na bandeja do sistema. Clique no ícone para abrir o menu:

- **Duração do vídeo** — troca quando o vídeo termina (com antecipação de 1s para evitar o flash do loop)
- **Trocar a cada 1 min / 5 min** — troca por tempo, repetindo o vídeo se necessário
- **⏸ Pausar troca** — congela na faixa atual, o Lively continua rodando normalmente
- **⏭ Próximo agora** — pula para o próximo imediatamente
- **📋 Gerenciar playlist** — abre a interface visual (também abre com clique simples no ícone)

### Gerenciador visual

Grid com miniaturas de todos os wallpapers. Permite:
- Ativar/desativar wallpapers individualmente com clique na imagem ou checkbox
- Filtrar por **Todos / Ativos / Inativos**
- Busca por nome
- **▶ Tocar** em qualquer card para ir direto àquele wallpaper
- Badge **"▶ tocando agora"** no card atual, com scroll automático até ele ao abrir

As miniaturas são geradas em background ao iniciar o programa e salvas em `thumbs/`. Na primeira execução com muitos vídeos, os cards aparecem com placeholder e vão sendo preenchidos conforme ficam prontos.

---

## 🛠️ Funcionalidades técnicas

### Detecção de fullscreen
O script detecta geometricamente se há um app ou jogo ocupando a tela toda e pausa o temporizador enquanto isso acontece — o Lively já pausa o wallpaper nessa situação, e o temporizador acompanha para não trocar assim que o jogo fechar.

**Janelas ignoradas na detecção** (não tratadas como fullscreen):
- `WorkerW`, `Progman`, `Shell_TrayWnd` — componentes da área de trabalho do Windows
- `TMainBox` — janela overlay do **iTop Easy Desktop**, que cobre a tela toda mesmo sem nada em foco

Se você usar outro app com comportamento parecido e o temporizador travar, rode o script `debug_window.py` para identificar a classe da janela problemática e adicione ao filtro em `src/utils/window_state.py`.

### Limpeza da biblioteca
A cada troca, o script apaga todos os vídeos (`Type: 7`) registrados na biblioteca do Lively em:
- `Library/SaveData/wallpapers/`
- `Library/SaveData/wptmp/`

Wallpapers HTML nativos do Lively (`Type: 1`, como Fluids, Rain, etc.) não são tocados.

### Temporizador com tempo real
O temporizador usa `time.time()` como âncora em vez de contador de ticks. Isso evita drift acumulado e garante que o tempo pausado durante fullscreen não seja contado — o relógio só avança quando o wallpaper está realmente visível.

### Quirks do Lively CLI
O comando `setwp` do Lively tem alguns comportamentos não documentados descobertos durante o desenvolvimento:

- `--monitor 0` causa falha silenciosa — o Lively retorna código 0 mas não troca nada. O parâmetro deve ser omitido. Isso está relacionado à configuração de Output de Áudio do Lively: quando definido como "Todas as telas", o script funciona corretamente sem o parâmetro --monitor. Se você usar o modo "Por tela", o comportamento pode ser imprevisível — o script não foi testado nessa configuração.
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