"""Модуль диспетчеризации команд.

Выносит логику обработки пользовательских команд из main.py:
каждая команда — функция (act, ctx) -> CommandResult | None.
"""
from dndai.commands.registry import dispatch
from dndai.commands.context import GameContext
from dndai.commands.result import CommandResult

__all__ = ["dispatch", "GameContext", "CommandResult"]
