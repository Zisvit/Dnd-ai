#!/usr/bin/env python3
"""Graceful shutdown для бота.

Обработчики сигналов регистрируются ТОЛЬКО явным вызовом
register_signals() из точки входа — импорт модуля не трогает сигналы.
"""

import signal
from typing import Callable
from .logger import info, error


class ShutdownHandler:
    """Обработчик корректного завершения"""

    def __init__(self):
        self._callbacks: list = []
        self._shutdown_flag = False

    def register_signals(self) -> None:
        """Регистрирует обработчики сигналов (вызывать из main())."""
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum: int, frame) -> None:
        """Обработчик сигналов"""
        info(f"Получен сигнал {signum}, завершаем работу...")
        self.shutdown()

    def register(self, callback: Callable) -> None:
        """Регистрирует функцию для вызова при завершении"""
        self._callbacks.append(callback)

    def shutdown(self) -> None:
        """Выполняет корректное завершение"""
        if self._shutdown_flag:
            return

        self._shutdown_flag = True
        info("Начинаю корректное завершение...")

        # Вызываем все зарегистрированные функции
        for callback in self._callbacks:
            try:
                callback()
            except Exception as e:
                error(f"Ошибка при выполнении callback: {e}")

        info("Завершено")
        # Прерываем работу через KeyboardInterrupt (BaseException, но он
        # пойман в основном цикле, который успеет сохранить сессию),
        # а не через sys.exit: SystemExit пролетал бы мимо всех
        # except-блоков и терял последний ход.
        raise KeyboardInterrupt

    @property
    def is_shutting_down(self) -> bool:
        return self._shutdown_flag


# Глобальный экземпляр (сигналы НЕ регистрирует — см. register_signals)
shutdown_handler = ShutdownHandler()
