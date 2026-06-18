# 🍅 Pomodoro Terminal

Timer Pomodoro no terminal com interface rica, histórico de sessões e notificações nativas no macOS.

## Funcionalidades

- Ciclos configuráveis: 25 min foco → 5 min pausa curta → pausa longa a cada 4 pomodoros
- Barra de progresso e contador de ciclos em tempo real
- Histórico salvo em `~/.pomodoro_history.json`
- Notificações via macOS (osascript)
- Controles por teclado: pausar, pular fase e sair

## Instalação

```bash
pip install -r requirements.txt
```

## Como usar

```bash
python pomodoro.py
```

### Controles

| Tecla | Ação |
|-------|------|
| `espaço` | Pausar / retomar |
| `s` | Pular fase atual |
| `q` | Sair |

## Configuração

Edite as constantes no topo de `pomodoro.py` para ajustar os tempos:

```python
WORK_MINS = 25        # duração do foco
SHORT_BREAK_MINS = 5  # pausa curta
LONG_BREAK_MINS = 15  # pausa longa
LONG_BREAK_EVERY = 4  # pomodoros antes da pausa longa
```

## Requisitos

- Python 3.10+
- macOS (para as notificações)
- [rich](https://github.com/Textualize/rich) >= 13.0
