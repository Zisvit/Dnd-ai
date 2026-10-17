"""Результат выполнения команды.

text        — что напечатать пользователю (может быть многострочным)
stop        — True: команда полностью обработана, НЕ передавать ход DM
               False: команда лишь подготовила act (напр. спасбросок),
                      продолжить и отправить rewrite_act мастеру
rewrite_act — новая строка act для мастера (вместо исходной), либо None
exit_loop   — True: завершить игровой цикл (использует !откат)
"""


class CommandResult:
    def __init__(self, text="", *, stop=True, rewrite_act=None, exit_loop=False,
                 skip_persist=False):
        self.text = text
        self.stop = stop
        self.rewrite_act = rewrite_act
        self.exit_loop = exit_loop
        # True: при выходе НЕ перезаписывать сессию (используется !откатом,
        # который уже восстановил файл из бэкапа)
        self.skip_persist = skip_persist

    @classmethod
    def silent(cls):
        return cls("", stop=True)
