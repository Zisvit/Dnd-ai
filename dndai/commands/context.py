"""Контекст выполнения команд.

Содержит все состояния и колбэки, нужные обработчикам команд.
Обработчики не печатают сами — они возвращают CommandResult,
а оркестратор (main.py) печатает текст и применяет побочные эффекты.
"""


class GameContext:
    def __init__(self, *, character, world, spells, prog, status, quests,
                 npcs, timew, journal, macros, style, session_name,
                 persist, rollback, quiet_mode, history, summary,
                 player_name, compress, shutdown, party=None, enemies=None,
                 reputation=None):
        # состояние
        self.character = character
        self.world = world
        self.spells = spells
        self.prog = prog
        self.status = status
        self.quests = quests
        self.npcs = npcs
        self.timew = timew
        self.journal = journal
        self.macros = macros
        self.style = style
        # метаданные сессии
        self.session_name = session_name
        self.persist = persist          # callable() -> None
        self.rollback = rollback        # callable() -> bool
        self.quiet_mode = quiet_mode    # dict {"on": bool}
        self.history = history          # list (общий с main)
        self.summary = summary          # str
        self.player_name = player_name  # str
        self.compress = compress        # callable(history, session, char) -> (history, summary)
        self.shutdown = shutdown        # callable() -> None
        self.party = party              # Party | None — список игроков сессии
        self.enemies = enemies          # Enemies | None — враги в активном бою
        self.reputation = reputation    # Reputation | None — фракции
