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
| `sync_lockscreen` | `true`, `false` (padrão) | Sincroniza a tela de bloqueio do Windows com o wallpaper estático ativo |
| `last_played_wallpaper` | nome do arquivo ou `null` | Último wallpaper ativo reproduzido (usado para continuar de onde parou ao reiniciar) |
| `solid_background_color` | string hex (ex: `"#18181b"`) | Cor sólida para papel de parede nativo e tela de bloqueio base |

> **Nota:** `mode: null` significa que nenhum modo foi configurado ainda. O programa aguarda você selecionar um pelo menu da bandeja antes de começar a trocar.

---

## 🖱️ Interface

O programa vive na bandeja do sistema. Clique no ícone para abrir o menu:

- **📋 Gerenciar playlist** — abre a interface visual (no topo do menu; também abre com clique simples/duplo no ícone)
- **Sublista Ativa (Submenu)** — escolhe qual sublista de papéis de parede usar (gerenciadas pela interface)
- **Tempo de Troca (Submenu)** — define o tempo de permanência de cada vídeo (Duração do vídeo, 30 segundos, 1 min, 5 min, 10 min, 30 min ou 1 hora)
- **Modo de Rotação (Submenu)** — alterna entre rotação **Aleatória (Shuffle)** ou **Sequencial** (ordem alfabética)
- **Monitor (Submenu)** — define o monitor de destino: **Seguir Lively (Auto)** (padrão) ou fixa em um monitor específico detectado no sistema
- **🎨 Cor de Fundo Sólida (Submenu)** — escolhe uma cor sólida aplicada ao papel de parede nativo do Windows e à tela de bloqueio (Preto Puro, Cinza Chumbo, Azul Noturno, Cinza Ardósia ou Personalizada via seletor visual nativo)
- **🔒 Sincronizar Tela de Bloqueio** — ativa/desativa a sincronização automática da tela de bloqueio do Windows com o wallpaper atual (logo abaixo de Cor de Fundo Sólida)
- **⏸ Pausar troca / ▶ Retomar troca** — congela na faixa atual, o Lively continua rodando normalmente
- **⏮ Voltar Anterior** — retorna para o wallpaper reproduzido anteriormente usando a pilha de histórico
- **⏭ Próximo agora** — pula para o próximo imediatamente

### Gerenciador visual

Interface totalmente em português para controle da biblioteca:
- **Ações Rápidas no Cabeçalho:**
  - **📂 Abrir Pasta:** abre a pasta `wallpapers/` diretamente no Windows Explorer para adicionar novos vídeos
  - **🎨 Abrir Lively:** traz a central do Lively Wallpaper para o primeiro plano via CLI
  - **🧹 Limpar Cache:** varre e remove com total segurança miniaturas e dados de duração de vídeos já excluídos do disco (com confirmação prévia)
  - **🔄 Recarregar:** atualiza a lista de wallpapers imediatamente
- **Painel de Sublistas:** crie novas playlists zeradas (➕ Nova), renomeie (✏ Renomear) ou apague com confirmação (➖ Excluir) utilizando **diálogos temáticos integrados ao Catppuccin Mocha**
- Grid de miniaturas responsivo: o número de colunas se **ajusta de forma dinâmica** ao redimensionar ou maximizar a janela (com debounce para evitar lentidão)
- Carregamento dinâmico de miniaturas em tempo real: placeholders na tela são substituídos automaticamente assim que as imagens são geradas pela thread de fundo
- Ativar/desativar wallpapers na sublista selecionada clicando no card ou checkbox
- Filtro inteligente por **Todos / Ativos / Inativos** (se ajusta ao selecionar uma sublista personalizada)
- Busca por nome e atalhos rápidos (**✓ Selecionar Todos / ✗ Desmarcar Todos**) com feedback de hover no cursor
- **▶ Tocar** em qualquer card para ir direto àquele wallpaper
- Badge **"▶ tocando agora"** no card atual, com scroll automático até ele ao abrir

---

## 🛠️ Funcionalidades técnicas

### Detecção de fullscreen & Múltiplos Monitores
O script detecta geometricamente se há um app ou jogo ocupando a tela toda (em qualquer um dos monitores conectados via `MonitorFromWindow` e `GetMonitorInfoW` da Win32 API) e pausa o temporizador enquanto isso acontece — o Lively já pausa o wallpaper nessa situação, e o temporizador acompanha para não pular vídeos enquanto o jogo ou app estiver aberto.
Além disso, quando a tela do Windows é bloqueada (`Win+L`) ou entra em repouso, o temporizador congela automaticamente para economizar ciclos e preservar a playlist.

**Janelas ignoradas na detecção** (não tratadas como fullscreen):
- `WorkerW`, `Progman`, `Shell_TrayWnd`, `Shell_SecondaryTrayWnd` — componentes da área de trabalho e barras de tarefas do Windows
- `TMainBox` — janela overlay do **iTop Easy Desktop**, que cobre a tela toda mesmo sem nada em foco

Se você usar outro app com comportamento parecido e o temporizador travar, rode o script `debug_window.py` para identificar a classe da janela problemática e adicione ao filtro em `src/utils/window_state.py`.

### Limpeza da biblioteca e cache órfão
- **Biblioteca Lively:** A cada troca, o script apaga todos os vídeos (`Type: 7`) registrados na biblioteca temporária do Lively (`Library/SaveData/wallpapers/` e `Library/SaveData/wptmp/`). Wallpapers HTML nativos do Lively não são tocados.
- **Cache Órfão:** A ferramenta de limpeza no Gerenciador garante que miniaturas antigas em `thumbs/` e tempos de duração no `duration_cache` de vídeos que não existem mais em `wallpapers/` possam ser limpos sem nunca alterar vídeos reais.

### 🔒 Sincronização da Tela de Bloqueio (Opcional)
Permite que o mesmo wallpaper ativo em reprodução no Lively Wallpaper seja automaticamente refletido como a imagem estática de bloqueio do Windows (em alta resolução nativa).

- **Ativação:** No menu da bandeja (perto do relógio), clique em **🔒 Sincronizar Tela de Bloqueio** (logo abaixo de **Monitor**). Uma marcação `✓` confirmará a ativação.
- **Permissão única no Windows:** As políticas de tela de bloqueio do Windows exigem escrita na chave `HKLM`. Para permitir que o aplicativo atualize a imagem transparentemente em segundo plano sem pedir confirmações de Administrador a cada troca, clique com o botão direito em `setup_lockscreen_permission.bat` na raiz do projeto e selecione **Executar como Administrador** apenas uma vez.
- **Proteções do Sistema:**
  - **Thread em segundo plano:** A extração do frame é 100% assíncrona; a transição de vídeo no Lively ocorre instantaneamente sem qualquer engasgo.
  - **Gravação atômica:** O frame é gravado temporariamente e movido de forma atômica para evitar leituras corrompidas pelo Windows.
  - **Restauração limpa:** Ao desmarcar a opção na bandeja, a tela de bloqueio retorna automaticamente à cor sólida configurada.

### 🎨 Cor de Fundo Sólida & Suavização de Transições
Durante o recarregamento de vídeos do Lively Wallpaper, o Windows expõe por milissegundos a sua área de trabalho nativa. Além disso, antes do carregamento dos utilitários na inicialização do computador, a tela de bloqueio pode exibir o fundo padrão do Windows.
- **Geração Dinâmica em Resolução Nativa:** Utiliza o Pillow para gerar a imagem `Static Wallpaper/solid_background.png` na resolução exata do monitor principal (ex: 1920x1080), evitando borrões de interpolação do Explorer.
- **Atualização Imediata do Buffer DWM:** Aplica o papel de parede nativo via Win32 API (`SystemParametersInfoW`) com flags `SPIF_UPDATEINIFILE | SPIF_SENDCHANGE`, forçando a atualização instantânea do Desktop.
- **Integração com a Tela de Bloqueio:** Aplica a mesma imagem na tela de bloqueio (`PersonalizationCSP`) para que no boot o sistema já inicie no tom escuro escolhido. Caso a sincronização de vídeo esteja ativa, o vídeo assume a tela de bloqueio após o início da reprodução.
- **Presets e Personalização:**
  - **Preto Puro (`#000000`):** Fallback clássico.
  - **Cinza Chumbo (`#18181b`):** Neutro moderno dark mode (Tailwind zinc-900).
  - **Azul Noturno (`#0f172a`):** Elegante e profundo, combina com estilo acrílico/mica.
  - **Cinza Ardósia (`#111827`):** Meio-termo técnico equilibrado.
  - **Personalizada...:** Abre o seletor visual nativo (`tkinter.colorchooser.askcolor`) para livre escolha.

---

## 📁 Estrutura do projeto

```
.
├── src/
│   ├── main.pyw          # Entry point, gerencia threads
│   ├── config.py         # Carrega/salva config.json, migra chaves legadas
│   ├── lively.py         # Integração com Lively.exe (setwp, monitores, limpeza)
│   ├── playlist.py       # Loop principal, temporizador, pausa
│   ├── state.py          # Estado global (eventos de thread e variáveis)
│   ├── ui/
│   │   ├── tray.py       # Ícone e menu da bandeja (pystray)
│   │   ├── manager.py    # Interface visual tkinter (grid de wallpapers)
│   │   ├── dialogs.py    # Diálogos modais temáticos (Catppuccin Mocha)
│   │   └── theme.py      # Paleta de cores (Catppuccin Mocha)
│   └── utils/
│       ├── cache.py      # Limpeza segura de miniaturas e cache órfãos
│       ├── lockscreen.py # Extração em alta resolução e personalização do Windows
│       ├── solid_color.py # Geração nativa e aplicação de cor sólida de fundo
│       ├── thumbnails.py # Geração de frames em background
│       ├── window_state.py # Detecção de fullscreen via ctypes
│       └── logger.py     # Log centralizado
├── wallpapers/           # Seus vídeos ficam aqui
├── thumbs/               # Miniaturas geradas automaticamente
├── Static Wallpaper/     # Frames estáticos para a tela de bloqueio
├── Library/              # Biblioteca interna do Lively (apontada nas configurações)
├── config.json           # Configuração persistente
├── lively_playlist.vbs   # Launcher sem janela de terminal
├── setup_lockscreen_permission.bat # Script de permissão única (UAC)
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