#!/usr/bin/env python3
"""Internationalization: RU ↔ EN language switching.

Usage:
    from dndai.core.i18n import t, set_lang, get_lang
    print(t("main.no_keys"))
"""

import os

_lang = (os.getenv("LANG") or os.getenv("LC_ALL") or "ru").lower()
if _lang[:2] not in ("ru", "en"):
    _lang = "ru"
else:
    _lang = _lang[:2]

# ─── All user-facing strings ───────────────────────────────────────────────
_T: dict[str, dict[str, str]] = {
    # ── main.py ──────────────────────────────────────────────────────────
    "main.no_keys": {
        "ru": "Нет API ключей!",
        "en": "No API keys!",
    },
    "main.no_keys_hint": {
        "ru": "Добавьте ключ (GROQ_API_KEY, GEMINI_API_KEY, ...) в {home_env} или в .env рядом с проектом. Локальная Ollama: задайте OLLAMA_SERVER_URL",
        "en": "Add a key (GROQ_API_KEY, GEMINI_API_KEY, ...) to {home_env} or .env next to the project. Local Ollama: set OLLAMA_SERVER_URL",
    },
    "main.no_keys_url": {
        "ru": "Получить ключи: https://console.groq.com/keys",
        "en": "Get keys: https://console.groq.com/keys",
    },
    "main.startup_hint": {
        "ru": "💡 Введите 'помощь' или '/help' для списка команд",
        "en": "💡 Type 'help' or '/help' for command list",
    },
    "main.session_loaded": {
        "ru": "📂 Сессия '{session}' загружена",
        "en": "📂 Session '{session}' loaded",
    },
    "main.memory_preview": {
        "ru": "🧠 Память сюжета: {text}",
        "en": "🧠 Story memory: {text}",
    },
    "main.recent_events": {
        "ru": "📜 Последние события:",
        "en": "📜 Recent events:",
    },
    "main.new_session": {
        "ru": "🆕 Новая сессия '{session}'",
        "en": "🆕 New session '{session}'",
    },
    "main.first_prompt_tavern": {
        "ru": "Начинай игру. Опиши таверну.",
        "en": "Start the game. Describe the tavern.",
    },
    "main.models_unavailable": {
        "ru": "❌ Модели недоступны",
        "en": "❌ Models unavailable",
    },
    "main.char_creation": {
        "ru": "🎭 Создание персонажа",
        "en": "🎭 Character creation",
    },
    "main.char_name_prompt": {
        "ru": "Введите имя персонажа (или 'готов' чтобы оставить 'player'):",
        "en": "Enter character name (or 'skip' to keep 'player'):",
    },
    "main.char_name_input": {
        "ru": "Имя >",
        "en": "Name >",
    },
    "main.char_class_input": {
        "ru": "Класс >",
        "en": "Class >",
    },
    "main.char_default_class": {
        "ru": "Искатель приключений",
        "en": "Adventurer",
    },
    "main.name_change_marker": {
        "ru": "Теперь тебя зовут",
        "en": "you will now be called",
    },
    "main.name_change_pattern": {
        "ru": r"Теперь тебя зовут ([^\s,.!?]+)",
        "en": r"you will now be called\s+([^\s,.!?]+)",
    },
    "main.fact_marker_pattern": {
        "ru": r"\[\[ФАКТ:\s*(.+?)\]\]",
        "en": r"\[\[(?:ФАКТ|FACT):\s*(.+?)\]\]",
    },
    "world.start_location": {
        "ru": "Таверна",
        "en": "Tavern",
    },
    "world.start_fact": {
        "ru": "Игра начинается в таверне",
        "en": "The adventure begins in a tavern",
    },
    "main.char_hp_input": {
        "ru": "HP (по умолч. 24) >",
        "en": "HP (default 24) >",
    },
    "main.char_ac_input": {
        "ru": "КД (по умолч. 15) >",
        "en": "AC (default 15) >",
    },
    "main.char_stats_rolled": {
        "ru": "🎲 Характеристики (4d6, худший вон): {stats} (CON учтён в HP)",
        "en": "🎲 Stats rolled (4d6 drop lowest): {stats} (CON applied to HP)",
    },
    "main.nothing_to_rewrite": {
        "ru": "Переписывать нечего — нет ответа мастера.",
        "en": "Nothing to rewrite — no DM response yet.",
    },
    "main.char_created": {
        "ru": "✅ Персонаж '{name}' ({cls}) готов. Позже можно добавить союзников: !новый Имя, Класс, HP, КД и переключаться: !играть Имя",
        "en": "✅ Character '{name}' ({cls}) ready. You can add allies: !new Name, Class, HP, AC and switch: !play Name",
    },
    "main.facts_recorded": {
        "ru": "📌 Записано фактов мира: {n}",
        "en": "📌 World facts recorded: {n}",
    },
    "main.effect_damage": {
        "ru": "🩸 Эффект нанёс {dmg} урона ({parts}) (ОЗ {hp}/{max_hp})",
        "en": "🩸 Effect dealt {dmg} damage ({parts}) (HP {hp}/{max_hp})",
    },
    "main.you_died": {
        "ru": "💀 Ты пал! Используй !откат",
        "en": "💀 You died! Use !rollback",
    },
    "main.effect_expired": {
        "ru": "Эффект истёк: {names}",
        "en": "Effect expired: {names}",
    },
    "main.session_saved": {
        "ru": "✅ Сессия сохранена. До встречи!",
        "en": "✅ Session saved. See you!",
    },
    "main.list_empty": {
        "ru": "Сессий пока нет.",
        "en": "No sessions yet.",
    },
    "main.list_title": {
        "ru": "Сессии ({n}):",
        "en": "Sessions ({n}):",
    },
    "main.list_row": {
        "ru": "  {name} — сообщений: {msgs}, {size}, {date}",
        "en": "  {name} — messages: {msgs}, {size}, {date}",
    },
    "main.list_more": {
        "ru": "… и ещё {n} (показаны первые 50)",
        "en": "… and {n} more (first 50 shown)",
    },
    "main.prompts_corrupt": {
        "ru": "⚠️ Промпты изменены относительно манифеста ({n} шт.) — проверьте целостность",
        "en": "⚠️ Prompts differ from the integrity manifest ({n}) — check installation",
    },
    # ── api/openrouter.py ────────────────────────────────────────────────
    "api.no_provider_key": {
        "ru": "❌ У провайдера нет API-ключа.",
        "en": "❌ Provider has no API key.",
    },
    "api.no_keys": {
        "ru": "❌ Нет API ключей! Добавьте ключи в .env (OPENROUTER_API_KEY, GROQ_API_KEY, ...).",
        "en": "❌ No API keys! Add keys to .env (OPENROUTER_API_KEY, GROQ_API_KEY, ...).",
    },
    "api.error_401": {
        "ru": "❌ Неверный или просроченный API-ключ. Проверьте ключи в .env.",
        "en": "❌ Invalid or expired API key. Check your .env keys.",
    },
    "api.auth_skipped": {
        "ru": "⏭️ Недавняя ошибка 401 — провайдер временно пропускается.",
        "en": "⏭️ Recent 401 error — provider temporarily skipped.",
    },
    "api.error_403": {
        "ru": "❌ Доступ запрещён. У аккаунта нет прав на эту модель или ключ заблокирован.",
        "en": "❌ Access denied. Account lacks permission for this model or key is blocked.",
    },
    "api.error_404": {
        "ru": "❌ Модель не найдена или больше не доступна бесплатно.",
        "en": "❌ Model not found or no longer available for free.",
    },
    "api.error_400_tokens": {
        "ru": "❌ Слишком большой лимит токенов для этой модели. Попробуйте уменьшить детализацию.",
        "en": "❌ Token limit too high for this model. Try reducing detail level.",
    },
    "api.error_400": {
        "ru": "❌ Некорректный запрос к API (ошибка 400).",
        "en": "❌ Bad API request (error 400).",
    },
    "api.error_429_reset": {
        "ru": "❌ Исчерпан дневной лимит бесплатных запросов этого провайдера. Лимит обновится: {time}. Бот переключится на другого провайдера.",
        "en": "❌ Daily free request limit exhausted. Limit resets: {time}. Bot will switch provider.",
    },
    "api.error_429": {
        "ru": "❌ Исчерпан дневной лимит бесплатных запросов. Бот попробует другого провайдера.",
        "en": "❌ Daily free request limit exhausted. Bot will try another provider.",
    },
    "api.error_credits": {
        "ru": "❌ Недостаточно кредитов на балансе провайдера.",
        "en": "❌ Insufficient provider balance.",
    },
    "api.error_rate": {
        "ru": "❌ Слишком частые запросы (лимит скорости). Бот переключится на другого провайдера.",
        "en": "❌ Too many requests (rate limit). Bot will switch provider.",
    },
    "api.error_timeout": {
        "ru": "❌ Превышено время ожидания ответа от модели. Попробуем другую.",
        "en": "❌ Model response timed out. Trying another.",
    },
    "api.error_server": {
        "ru": "❌ Ошибка сервера провайдера ({status}).",
        "en": "❌ Provider server error ({status}).",
    },
    "api.error_network": {
        "ru": "❌ Нет соединения с интернетом или сервер недоступен. Проверьте подключение.",
        "en": "❌ No internet connection or server unreachable. Check your connection.",
    },
    "api.error_unknown": {
        "ru": "❌ Неизвестная ошибка API (код {status}).",
        "en": "❌ Unknown API error (code {status}).",
    },
    "api.refusal": {
        "ru": "❌ Модель отказалась отвечать (сработал фильтр отказа).",
        "en": "❌ Model refused to answer (refusal filter triggered).",
    },
    "api.empty_response": {
        "ru": "❌ Пустой ответ от модели.",
        "en": "❌ Empty response from model.",
    },
    "api.stream_broken": {
        "ru": "❌ Обрыв потока ответа от модели.",
        "en": "❌ Stream broken from model.",
    },
    "api.all_failed_limits": {
        "ru": "❌ У всех провайдеров исчерпаны лимиты бесплатных запросов. Подождите сброса лимита или добавьте ещё ключи/пополните баланс.",
        "en": "❌ All providers' free request limits exhausted. Wait for reset or add more keys/fund balance.",
    },
    "api.all_failed_auth": {
        "ru": "❌ Ошибка авторизации у провайдеров. Проверьте ключи в .env.",
        "en": "❌ Provider authorization error. Check your .env keys.",
    },
    "api.all_failed_network": {
        "ru": "❌ Проблема с сетью. Проверьте интернет-соединение.",
        "en": "❌ Network problem. Check your internet connection.",
    },
    "api.all_failed": {
        "ru": "❌ Не удалось получить ответ ни от одного провайдера.",
        "en": "❌ Failed to get response from any provider.",
    },
    # ── meta_cmds.py ─────────────────────────────────────────────────────
    "meta.memory_updated": {
        "ru": "🧠 Память сюжета обновлена.",
        "en": "🧠 Story memory updated.",
    },
    "meta.dm_order": {
        "ru": "📜 Приказ мастеру: {cmd}",
        "en": "📜 DM order: {cmd}",
    },
    "meta.emoji_on": {
        "ru": "✅ Режим эмодзи: включён",
        "en": "✅ Emoji mode: enabled",
    },
    "meta.emoji_off": {
        "ru": "✅ Режим эмодзи: выключен",
        "en": "✅ Emoji mode: disabled",
    },
    "meta.dice_roll": {
        "ru": "🎲 Бросок {expr}: {detail} = {total}",
        "en": "🎲 Roll {expr}: {detail} = {total}",
    },
    "meta.rollback_ok": {
        "ru": "↩️ Откат к предыдущему сохранению. Перезапустите сессию: dndd {session}",
        "en": "↩️ Rolled back to previous save. Restart session: dndd {session}",
    },
    "meta.no_backup": {
        "ru": "Бэкап не найден.",
        "en": "No backup found.",
    },
    "meta.model_auto": {
        "ru": "✅ Режим модели: автоматический выбор",
        "en": "✅ Model mode: automatic selection",
    },
    # ── character_cmds.py ────────────────────────────────────────────────
    "char.created": {
        "ru": "✅ Персонаж создан: {name} ({cls})",
        "en": "✅ Character created: {name} ({cls})",
    },
    "char.create_format": {
        "ru": "Формат: !персонаж Имя, Класс, HP, КД (пример: !персонаж Волк, Наёмник, 24, 15)",
        "en": "Format: !character Name, Class, HP, AC (example: !character Wolf, Mercenary, 24, 15)",
    },
    "char.damage": {
        "ru": "💥 Получен урон {dmg}. HP: {hp}/{max_hp}",
        "en": "💥 Took {dmg} damage. HP: {hp}/{max_hp}",
    },
    "char.heal": {
        "ru": "✚ Восстановлено {amt}. HP: {hp}/{max_hp}",
        "en": "✚ Healed {amt}. HP: {hp}/{max_hp}",
    },
    "char.sethp": {
        "ru": "HP установлен: {hp}/{max_hp}",
        "en": "HP set to: {hp}/{max_hp}",
    },
    "char.inv_add": {
        "ru": "🎒 Добавлено: {items}",
        "en": "🎒 Added: {items}",
    },
    "char.inv_del": {
        "ru": "🗑 Удалено: {items}",
        "en": "🗑 Removed: {items}",
    },
    "char.inv_show": {
        "ru": "🎒 Инвентарь:",
        "en": "🎒 Inventory:",
    },
    "char.inv_empty": {
        "ru": "Инвентарь пуст.",
        "en": "Inventory is empty.",
    },
    # ── combat_cmds.py ───────────────────────────────────────────────────
    "combat.save_success": {
        "ru": "УСПЕХ",
        "en": "SUCCESS",
    },
    "combat.save_fail": {
        "ru": "ПРОВАЛ",
        "en": "FAIL",
    },
    "combat.save_result": {
        "ru": "🎲 Спасбросок {stat} (мод {mod}{bonus}) против СЛ {dc}: выпало {roll} → {result}",
        "en": "🎲 Saving throw {stat} (mod {mod}{bonus}) vs DC {dc}: rolled {roll} → {result}",
    },
    "combat.save_bonus_note": {
        "ru": ", бонус эффекта {sb:+d}",
        "en": ", effect bonus {sb:+d}",
    },
    # ── боевая система с трекингом HP ─────────────────────────────────────
    "combat.enemy_joined": {
        "ru": "⚔️ {name} вступает в бой (HP {hp}, КД {ac})",
        "en": "⚔️ {name} joins the fight (HP {hp}, AC {ac})",
    },
    "combat.enemy_exists": {
        "ru": "⚔️ Продолжается бой против {name}",
        "en": "⚔️ Fight continues vs {name}",
    },
    "combat.player_hit": {
        "ru": "🎲 d20={roll} {mod} = {total} vs КД {ac} → ПОПАДАНИЕ! Урон: 💥{dmg} (у врага {left_hp}/{max_hp} HP)",
        "en": "🎲 d20={roll} {mod} = {total} vs AC {ac} → HIT! Damage: 💥{dmg} (enemy at {left_hp}/{max_hp} HP)",
    },
    "combat.player_miss": {
        "ru": "🎲 d20={roll} {mod} = {total} vs КД {ac} → МИМО",
        "en": "🎲 d20={roll} {mod} = {total} vs AC {ac} → MISS",
    },
    "combat.critical": {
        "ru": "КРИТИЧЕСКОЕ ПОПАДАНИЕ!",
        "en": "CRITICAL HIT!",
    },
    "combat.enemy_slain": {
        "ru": "{name} повержен! +{xp} опыта",
        "en": "{name} is slain! +{xp} XP",
    },
    "combat.battle_won": {
        "ru": "Все враги побеждены — бой окончен!",
        "en": "All enemies defeated — battle won!",
    },
    "combat.mob_hit_you": {
        "ru": "↩️ {name} контратакует: d20={roll}+5 vs твоя КД {ac} → попал, тебе -{dmg} HP ({hp}/{max_hp})",
        "en": "↩️ {name} strikes back: d20={roll}+5 vs your AC {ac} → hit, -{dmg} HP ({hp}/{max_hp})",
    },
    "combat.mob_miss_you": {
        "ru": "↩️ {name} атакует в ответ: d20={roll}+5 vs КД {ac} → мимо",
        "en": "↩️ {name} counters: d20={roll}+5 vs AC {ac} → miss",
    },
    "combat.no_such_enemy": {
        "ru": "Враг '{name}' не найден. Смотри !враги",
        "en": "Enemy '{name}' not found. See !enemies",
    },
    "combat.none_left": {
        "ru": "никого не осталось",
        "en": "none left",
    },
    "combat.no_enemies": {
        "ru": "Врагов в бою нет.",
        "en": "No enemies in combat.",
    },
    "combat.enemies_title": {
        "ru": "⚔️ ВРАГИ В БОЮ:",
        "en": "⚔️ ENEMIES IN COMBAT:",
    },
    "combat.initiative": {
        "ru": "иниц.",
        "en": "init",
    },
    "combat.dying_intro": {
        "ru": "Ты падаешь без сознания! Каждый ход — бросок смерти (d20: ≥10 успех, <10 провал; 3 провала = смерть). !стабилизироваться или !отдых может спасти",
        "en": "You fall unconscious! Death save each turn (d20: ≥10 success, <10 fail; 3 fails = death)",
    },
    "combat.not_dying": {
        "ru": "Ты в сознании — стабилизация не нужна.",
        "en": "You are conscious — no need to stabilize.",
    },
    "combat.already_stable": {
        "ru": "Ты уже стабилизирован. Нужен отдых или лечение, чтобы встать.",
        "en": "Already stabilized. You need rest or healing to stand up.",
    },
    "combat.stabilized_ok": {
        "ru": "✚ Проверка медицины {roll} → ты стабилизирован! Отдых вернёт тебя в строй",
        "en": "✚ Medicine check {roll} → stabilized! Rest will get you back",
    },
    "combat.stabilize_fail": {
        "ru": "Проверка не удалась ({roll}). Провалов: {fails}/3",
        "en": "Check failed ({roll}). Failures: {fails}/3",
    },
    "combat.death_save_result": {
        "ru": "☠ Бросок смерти: d20={roll}. Успехи: {ok}, провалы: {fail}/3",
        "en": "☠ Death save: d20={roll}. Successes: {ok}, failures: {fail}/3",
    },
    "combat.death_stabilized": {
        "ru": "Бросок смерти {roll}: 3 успеха — ты стабилизировался!",
        "en": "Death save {roll}: 3 successes — stabilized!",
    },
    "combat.death_nat20": {
        "ru": "Бросок смерти: НАТУРАЛЬНАЯ 20! Ты вскакиваешь на ноги с 1 HP!",
        "en": "Death save: NATURAL 20! You spring back to your feet with 1 HP!",
    },
    "combat.morale_flee": {
        "ru": "{name} бросает оружие и убегает! (+{xp} опыта за победу)",
        "en": "{name} drops their weapon and flees! (+{xp} XP for the win)",
    },
    "rpg.level_short": {
        "ru": "ур.{level}",
        "en": "lv.{level}",
    },
    "rpg.day_n": {
        "ru": "день {day}",
        "en": "day {day}",
    },
    # ── party_cmds.py ────────────────────────────────────────────────────
    "party.empty": {
        "ru": "Партия пуста.",
        "en": "Party is empty.",
    },
    "party.list_title": {
        "ru": "👥 ПАРТИЯ:",
        "en": "👥 PARTY:",
    },
    "party.member": {
        "ru": "  {n}. {name} ({cls}, ур. {level}, HP {hp}/{max_hp}){mark}",
        "en": "  {n}. {name} ({cls}, lv. {level}, HP {hp}/{max_hp}){mark}",
    },
    "party.switched": {
        "ru": "🔄 Теперь управляет: {name} ({cls})",
        "en": "🔄 Now controlling: {name} ({cls})",
    },
    "party.not_found": {
        "ru": "Игрок '{name}' не найден в партии.",
        "en": "Player '{name}' not found in party.",
    },
    "party.added": {
        "ru": "✨ Добавлен в партию: {name} ({cls}). Теперь им управляет (переключить: !играть {name})",
        "en": "✨ Added to party: {name} ({cls}). Now controlling (switch: !play {name})",
    },
    "party.add_fail": {
        "ru": "Не удалось создать персонажа. Формат: !новый Имя, Класс, HP, КД",
        "en": "Failed to create character. Format: !new Name, Class, HP, AC",
    },
    "party.renamed": {
        "ru": "🏷 Тебя зовут: {name}",
        "en": "🏷 Your name is now: {name}",
    },
    "party.rename_fail": {
        "ru": "Не удалось переименовать.",
        "en": "Failed to rename.",
    },
    # ── rpg_cmds.py ──────────────────────────────────────────────────────
    "rpg.spell_added": {
        "ru": "✨ Заклинание добавлено: {name}{extra}",
        "en": "✨ Spell added: {name}{extra}",
    },
    "rpg.spell_add_fail": {
        "ru": "Не удалось добавить заклинание.",
        "en": "Failed to add spell.",
    },
    "rpg.spell_dmg": {
        "ru": "урон {dmg}",
        "en": "damage {dmg}",
    },
    "rpg.spell_dc": {
        "ru": "СЛ {dc}",
        "en": "DC {dc}",
    },
    "rpg.spell_removed": {
        "ru": "✨ Заклинание удалено.",
        "en": "✨ Spell removed.",
    },
    "rpg.spell_not_found": {
        "ru": "Заклинание не найдено.",
        "en": "Spell not found.",
    },
    "rpg.xp_gained": {
        "ru": "⭐ Получено XP: {xp}",
        "en": "⭐ Gained XP: {xp}",
    },
    "rpg.level_up": {
        "ru": "🆙 УРОВЕНЬ ПОВЫШЕН! Теперь уровень {level} (+1 очко характеристики)",
        "en": "🆙 LEVEL UP! Now level {level} (+1 stat point)",
    },
    "rpg.statup_ok": {
        "ru": "🆙 {stat} +{amt}. Остаток очков: {left}",
        "en": "🆙 {stat} +{amt}. Points remaining: {left}",
    },
    "rpg.statup_fail": {
        "ru": "Недостаточно очков ({pts}) или нет характеристики {stat}.",
        "en": "Not enough points ({pts}) or stat {stat} not found.",
    },
    "rpg.effect_applied": {
        "ru": "🔮 Эффект наложен: {name} (ходов: {rounds}){desc}",
        "en": "🔮 Effect applied: {name} (rounds: {rounds}){desc}",
    },
    "rpg.effect_apply_fail": {
        "ru": "Не удалось наложить эффект.",
        "en": "Failed to apply effect.",
    },
    "rpg.effect_removed": {
        "ru": "Эффект снят.",
        "en": "Effect removed.",
    },
    "rpg.effect_not_found": {
        "ru": "Эффект не найден.",
        "en": "Effect not found.",
    },
    "rpg.quest_added": {
        "ru": "📜 Квест добавлен: {title}",
        "en": "📜 Quest added: {title}",
    },
    "rpg.quest_exists": {
        "ru": "Такой квест уже есть.",
        "en": "This quest already exists.",
    },
    "rpg.quest_done": {
        "ru": "✅ Квест завершён: {title}",
        "en": "✅ Quest completed: {title}",
    },
    "rpg.quest_not_found": {
        "ru": "Квест не найден.",
        "en": "Quest not found.",
    },
    "rpg.quest_removed": {
        "ru": "Квест удалён: {title}",
        "en": "Quest removed: {title}",
    },
    "rpg.time_advanced": {
        "ru": "⏰ Время сдвинуто.",
        "en": "⏰ Time advanced.",
    },
    "rpg.time_info": {
        "ru": "  Время: День {day}, {part} ({hour}:00), погода: {weather}",
        "en": "  Time: Day {day}, {part} ({hour}:00), weather: {weather}",
    },
    "rpg.weather_set": {
        "ru": "🌤 Погода: {weather}",
        "en": "🌤 Weather: {weather}",
    },
    "rpg.weather_unknown": {
        "ru": "Неизвестная погода. Доступно: {list}",
        "en": "Unknown weather. Available: {list}",
    },
    "rpg.journal_added": {
        "ru": "📓 Запись добавлена в дневник.",
        "en": "📓 Entry added to journal.",
    },
    "rpg.macro_added": {
        "ru": "⚡ Макрос {name} → {cmd}",
        "en": "⚡ Macro {name} → {cmd}",
    },
    "rpg.macro_add_fail": {
        "ru": "Не удалось добавить макрос.",
        "en": "Failed to add macro.",
    },
    "rpg.macro_removed": {
        "ru": "Макрос удалён.",
        "en": "Macro removed.",
    },
    "rpg.tone_set": {
        "ru": "🎭 Тон: {tone}",
        "en": "🎭 Tone: {tone}",
    },
    "rpg.tone_unknown": {
        "ru": "Тон '{tone}' не из списка. Доступно: {list}",
        "en": "Tone '{tone}' not in list. Available: {list}",
    },
    "rpg.genre_set": {
        "ru": "🎭 Жанр: {genre}",
        "en": "🎭 Genre: {genre}",
    },
    "rpg.genre_unknown": {
        "ru": "Жанр '{genre}' не из списка. Доступно: {list}",
        "en": "Genre '{genre}' not in list. Available: {list}",
    },
    "rpg.style_info": {
        "ru": "  Тон: {tone}, Жанр: {genre}",
        "en": "  Tone: {tone}, Genre: {genre}",
    },
    "rpg.quiet_on": {
        "ru": "🔇 Тихий режим: включён",
        "en": "🔇 Quiet mode: enabled",
    },
    "rpg.rest_done": {
        "ru": "🛏 Долгий отдых завершён (день {day}, {hour}:00). HP {hp}/{max_hp}.",
        "en": "🛏 Long rest complete (day {day}, {hour}:00). HP {hp}/{max_hp}.",
    },
    "rpg.rest_healed": {
        "ru": "Восстановлено HP: +{amt}",
        "en": "HP restored: +{amt}",
    },
    "rpg.rest_effects_cleared": {
        "ru": "Эффекты сняты: {names}",
        "en": "Effects cleared: {names}",
    },
    "rpg.rest_slots": {
        "ru": "Ячейки заклинаний восстановлены: +{n}",
        "en": "Spell slots restored: +{n}",
    },
    "rpg.cast_ok": {
        "ru": "Ты произносишь «{name}» (ячейки: {left})",
        "en": "You cast '{name}' (slots left: {left})",
    },
    "rpg.cast_damage": {
        "ru": "💥 {target} получает урон магией: -{dmg} HP (осталось {left_hp}/{max_hp})",
        "en": "💥 {target} takes magic damage: -{dmg} HP ({left_hp}/{max_hp} left)",
    },
    "rpg.cast_no_dmg": {
        "ru": "Магия окутывает {target}...",
        "en": "Magic envelops {target}...",
    },
    "rpg.cast_unknown": {
        "ru": "Заклинание «{name}» неизвестно. Добавь его: !закл имя | эффект",
        "en": "Unknown spell '{name}'. Add it: !spell name | effect",
    },
    "rpg.no_slots": {
        "ru": "Ячейки заклинаний исчерпаны! Нужен !отдых",
        "en": "No spell slots left! You need !rest",
    },
    "rpg.slots_none": {
        "ru": "Твой класс не использует ячейки заклинаний.",
        "en": "Your class doesn't use spell slots.",
    },
    "rpg.slots_left": {
        "ru": "✨ Ячейки заклинаний: {left} из {max}",
        "en": "✨ Spell slots: {left} of {max}",
    },
    "rpg.quiet_off": {
        "ru": "🔇 Тихий режим: выключен",
        "en": "🔇 Quiet mode: disabled",
    },
    "rpg.check_conflict": {
        "ru": "⚠️ Противоречие с установленными фактами:",
        "en": "⚠️ Conflict with established facts:",
    },
    "rpg.check_ok": {
        "ru": "✅ Противоречий не найдено.",
        "en": "✅ No conflicts found.",
    },
    # ── world_cmds.py ────────────────────────────────────────────────────
    "world.npc_added": {
        "ru": "👥 NPC добавлен: {name}",
        "en": "👥 NPC added: {name}",
    },
    "world.npc_add_fail": {
        "ru": "Не удалось добавить NPC.",
        "en": "Failed to add NPC.",
    },
    "world.npc_removed": {
        "ru": "NPC удалён.",
        "en": "NPC removed.",
    },
    "world.npc_not_found": {
        "ru": "NPC не найден.",
        "en": "NPC not found.",
    },
    "world.location_changed": {
        "ru": "📍 Локация изменена: <<{loc}>>",
        "en": "📍 Location changed: <<{loc}>>",
    },
    "world.fact_added": {
        "ru": "✓ Факт добавлен: {fact}",
        "en": "✓ Fact added: {fact}",
    },
    "world.fact_exists": {
        "ru": "Факт уже есть или пуст.",
        "en": "Fact already exists or empty.",
    },
    "world.voice_set": {
        "ru": "🎭 Голос {npc} → {tag}",
        "en": "🎭 Voice {npc} → {tag}",
    },
    "world.voice_unknown": {
        "ru": "Неизвестный тег голоса. Доступно: {list}",
        "en": "Unknown voice tag. Available: {list}",
    },
    "world.map_linked": {
        "ru": "🗺 Локации связаны: {a} ↔ {b}",
        "en": "🗺 Locations linked: {a} ↔ {b}",
    },
    # ── game/help.py ─────────────────────────────────────────────────────
    "help.title": {
        "ru": "🎲 Системные команды:",
        "en": "🎲 System commands:",
    },
    "help.quick_title": {
        "ru": "🎲 КОМАНДЫ (полный список: /help всё)",
        "en": "🎲 COMMANDS (full list: /help all)",
    },
    "help.clear": {
        "ru": "очистить историю и выйти",
        "en": "  clear / reset – clear history and exit",
    },
    "help.quit": {
        "ru": "сохранить сессию и выйти (quit)",
        "en": "save session and exit (quit)",
    },
    "help.model_switch": {
        "ru": "сменить модель/провайдера (auto — авто-выбор)",
        "en": "switch model/provider (auto for automatic)",
    },
    "help.classes": {
        "ru": "показать список архетипов классов",
        "en": "show available class archetypes",
    },
    "help.detail_up": {
        "ru": "повысить детализацию",
        "en": "  more detail – increase detail level",
    },
    "help.detail_down": {
        "ru": "сбросить детализацию",
        "en": "  shorter – reset detail level",
    },
    "help.rename": {
        "ru": "сменить имя",
        "en": "  my name is now X – change name",
    },
    "help.dm_order": {
        "ru": "прямой приказ мастеру",
        "en": "  dm: <order> – direct order to DM",
    },
    "help.info_title": {
        "ru": "📋 Информационные команды:",
        "en": "📋 Information commands:",
    },
    "help.models": {
        "ru": "показать ранкинги моделей",
        "en": "  /models or models – show model rankings",
    },
    "help.stats": {
        "ru": "статистика запросов по провайдерам",
        "en": "  /stats or stats – request statistics by provider",
    },
    "help.colors": {
        "ru": "проверить работу цветов",
        "en": "  /colors or test colors – test color display",
    },
    "help.model_show": {
        "ru": "показать текущую модель",
        "en": "  /model – show current model",
    },
    "help.history": {
        "ru": "показать историю",
        "en": "  history or /history – show history",
    },
    "help.memory": {
        "ru": "сжать историю и обновить память сюжета",
        "en": "  update memory – compress history and update story memory",
    },
    "help.char_title": {
        "ru": "🎲 Механика персонажа (D&D):",
        "en": "🎲 Character mechanics (D&D):",
    },
    "help.char_create": {
        "ru": "создать персонажа",
        "en": "  !character Name, Class, HP, AC – create character",
    },
    "help.char_status": {
        "ru": "показать состояние персонажа",
        "en": "  !status – show character status",
    },
    "help.inv": {
        "ru": "показать вещи",
        "en": "  !inventory – show items",
    },
    "help.heal": {
        "ru": "восстановить HP",
        "en": "  !heal 5 – restore HP",
    },
    "help.save": {
        "ru": "спасбросок (модификатор учитывается)",
        "en": "  !save STR 12 – saving throw (modifier applied)",
    },
    "help.fight": {
        "ru": "бой с HP врага, критом и инициативой",
        "en": "fight enemy with HP tracking, crits and initiative",
    },
    "help.dice": {
        "ru": "бросить кости (например 1d20, 3d6+2)",
        "en": "  !dice 2d6 – roll dice (e.g. 1d20, 3d6+2)",
    },
    "help.party_title": {
        "ru": "👥 Партия (co-op, несколько игроков):",
        "en": "👥 Party (co-op, multiple players):",
    },
    "help.party_new": {
        "ru": "добавить союзника в партию",
        "en": "  !new Name, Class, HP, AC – add ally to party",
    },
    "help.party_list": {
        "ru": "список персонажей партии",
        "en": "  !characters / !party – list party members",
    },
    "help.party_switch": {
        "ru": "переключить управляемого",
        "en": "  !play <Name> / !switch – switch controlled character",
    },
    "help.world_title": {
        "ru": "🌍 Мир и локации:",
        "en": "🌍 World and locations:",
    },
    "help.world_show": {
        "ru": "состояние мира (локация, факты, голоса NPC)",
        "en": "  !world – world state (location, facts, NPC voices)",
    },
    "help.goto": {
        "ru": "сменить локацию",
        "en": "  !goto <<Dark Alley>> – change location",
    },
    "help.fact": {
        "ru": "добавить факт мира",
        "en": "  !fact Magic is forbidden here – add world fact",
    },
    "help.voice": {
        "ru": "задать стиль NPC",
        "en": "  !voice Barman cynical – set NPC voice style",
    },
    "help.rollback": {
        "ru": "откатить сессию к сохранению на момент входа",
        "en": "  !rollback – rollback session to save on entry",
    },
    "help.rpg_title": {
        "ru": "✨ RPG-системы:",
        "en": "✨ RPG systems:",
    },
    "help.spell_add": {
        "ru": "добавить заклинание",
        "en": "    !spell Name: Description | damage 3d6 | DC 13 – add spell",
    },
    "help.xp": {
        "ru": "получить опыт (авто-повышение уровня)",
        "en": "    !xp 150 – gain XP (auto level-up)",
    },
    "help.effect_add": {
        "ru": "наложить эффект на 3 хода",
        "en": "    !status-effect poison 3 – apply effect for 3 rounds",
    },
    "help.quest_add": {
        "ru": "добавить квест",
        "en": "    !quest Name: Description – add quest",
    },
    "help.npc_add": {
        "ru": "добавить NPC",
        "en": "    !npc Name | voice | note | relation – add",
    },
    "help.time_advance": {
        "ru": "сдвинуть время на 3 часа",
        "en": "    !time +3 – advance time by 3 hours",
    },
    "help.map_show": {
        "ru": "показать карту",
        "en": "    !map – show map",
    },
    "help.journal_add": {
        "ru": "добавить запись в дневник",
        "en": "    !note Text – add journal entry",
    },
    "help.macro_add": {
        "ru": "создать макрос",
        "en": "    !macro Name: command – create macro",
    },
    "help.tone_set": {
        "ru": "задать тон повествования",
        "en": "    !tone dark – set narrative tone",
    },
    "help.quiet": {
        "ru": "скрыть системные сообщения",
        "en": "    !quiet on|off – hide system messages",
    },
    "help.check": {
        "ru": "сверить с фактами мира",
        "en": "    !check Statement – verify against world facts",
    },
    # ── game/help.py (color legend, etc.) ────────────────────────────────
    "help.legend_title": {
        "ru": "🎨 Сюжетная подсветка:",
        "en": "🎨 Story highlights:",
    },
    "help.legend_npc": {
        "ru": "  {NPC} — NPC, важные люди",
        "en": "  {NPC} — NPCs, important people",
    },
    "help.legend_loc": {
        "ru": "  <<Места>> — локации, города, таверны",
        "en": "  <<Places>> — locations, cities, taverns",
    },
    "help.legend_item": {
        "ru": "  [[Предметы]] — вещи, артефакты, гаджеты",
        "en": "  [[Items]] — things, artifacts, gadgets",
    },
    "help.legend_event": {
        "ru": "  __События__ — повороты сюжета, ключевые моменты",
        "en": "  __Events__ — plot twists, key moments",
    },
    "help.legend_emotion": {
        "ru": "  !!Эмоции!! — чувства, настроение",
        "en": "  !!Emotions!! — feelings, mood",
    },
    "help.test_green": {
        "ru": "Зелёный работает!",
        "en": "Green works!",
    },
    "help.test_blue": {
        "ru": "Синий работает!",
        "en": "Blue works!",
    },
    "help.test_red": {
        "ru": "Красный работает!",
        "en": "Red works!",
    },
    "help.test_yellow": {
        "ru": "Жёлтый работает!",
        "en": "Yellow works!",
    },
    "help.test_cyan": {
        "ru": "Голубой работает!",
        "en": "Cyan works!",
    },
    "help.test_orange": {
        "ru": "Оранжевый работает!",
        "en": "Orange works!",
    },
    "help.test_purple": {
        "ru": "Фиолетовый работает!",
        "en": "Purple works!",
    },
    # ── game/character.py ────────────────────────────────────────────────
    "char.status_title": {
        "ru": "🧙 СОСТОЯНИЕ ПЕРСОНАЖА:",
        "en": "🧙 CHARACTER STATUS:",
    },
    "char.not_created": {
        "ru": "Персонаж ещё не создан. Введите: !персонаж Имя, Класс, HP, КД",
        "en": "Character not yet created. Type: !character Name, Class, HP, AC",
    },
    "char.not_created_ex": {
        "ru": "Пример: !персонаж Волк, Наёмник, 24, 15",
        "en": "Example: !character Wolf, Mercenary, 24, 15",
    },
    "char.name": {
        "ru": "Имя:",
        "en": "Name:",
    },
    "char.class": {
        "ru": "Класс:",
        "en": "Class:",
    },
    "char.hp": {
        "ru": "HP:",
        "en": "HP:",
    },
    "char.ac": {
        "ru": "КД:",
        "en": "AC:",
    },
    "char.stats": {
        "ru": "Характеристики:",
        "en": "Stats:",
    },
    "char.inventory": {
        "ru": "Инвентарь:",
        "en": "Inventory:",
    },
    "char.gold": {
        "ru": "Золото:",
        "en": "Gold:",
    },
    "char.gold_show": {
        "ru": "💰 В кошельке: {gold} монет",
        "en": "💰 Purse: {gold} coins",
    },
    "char.gold_changed": {
        "ru": "💰 Золото {delta} → теперь {gold} монет",
        "en": "💰 Gold {delta} → now {gold} coins",
    },
    "char.equipment": {
        "ru": "Экипировка:",
        "en": "Equipped:",
    },
    "char.equipped": {
        "ru": "Надето: {item} [{slot}]",
        "en": "Equipped: {item} [{slot}]",
    },
    "char.unequipped": {
        "ru": "Снято: {items}",
        "en": "Removed: {items}",
    },
    "char.equip_nothing": {
        "ru": "Ничего не надето.",
        "en": "Nothing equipped.",
    },
    "char.equip_empty": {
        "ru": "Экипировка пуста. Надень предмет: !надеть меч",
        "en": "Nothing equipped. Try: !equip sword",
    },
    "char.equip_not_in_inventory": {
        "ru": "«{item}» нет в инвентаре. Добавь: !инвентарь добавить <предмет>",
        "en": "'{item}' is not in inventory. Add it: !inventory add <item>",
    },
    "meta.chronicle_saved": {
        "ru": "📖 Хроника сохранена: {path}",
        "en": "📖 Chronicle saved: {path}",
    },
    "main.char_race_input": {
        "ru": "Раса ({examples} или своя) >",
        "en": "Race ({examples} or custom) >",
    },
    "main.char_default_race": {
        "ru": "Человек",
        "en": "Human",
    },
    "main.char_race_bonus": {
        "ru": "{race}: бонусы {bonuses}",
        "en": "{race}: bonuses {bonuses}",
    },
    "char.kit_given": {
        "ru": "Стартовый набор: {items}",
        "en": "Starting kit: {items}",
    },
    "char.kit_spell": {
        "ru": "заклинание",
        "en": "spell",
    },
    "shop.bought": {
        "ru": "🛒 Куплено: «{item}» за {price} монет (осталось {gold})",
        "en": "🛒 Bought: '{item}' for {price} coins ({gold} left)",
    },
    "shop.sold": {
        "ru": "💰 Продано: «{item}» за {price} монет (теперь {gold})",
        "en": "💰 Sold: '{item}' for {price} coins (now {gold})",
    },
    "shop.cant_afford": {
        "ru": "«{item}» стоит {price}, у тебя только {gold} монет.",
        "en": "'{item}' costs {price}, you only have {gold} coins.",
    },
    "shop.not_owned": {
        "ru": "«{item}» нет в инвентаре — нечего продавать.",
        "en": "'{item}' is not in your inventory.",
    },
    "rep.title": {
        "ru": "🤝 РЕПУТАЦИЯ ФРАКЦИЙ:",
        "en": "🤝 FACTION REPUTATION:",
    },
    "rep.empty": {
        "ru": "О тебе пока никто не слышал.",
        "en": "Nobody has heard of you yet.",
    },
    "rep.changed": {
        "ru": "Репутация [{faction}]: {delta} → теперь {score}",
        "en": "Reputation [{faction}]: {delta} → now {score}",
    },
    "main.recap_title": {
        "ru": "📖 Ранее в кампании:",
        "en": "📖 Previously in this campaign:",
    },
    "char.notes": {
        "ru": "Заметки:",
        "en": "Notes:",
    },
    # ── game/rpg.py ──────────────────────────────────────────────────────
    "rpg.spells_title": {
        "ru": "✨ ЗАКЛИНАНИЯ И СПОСОБНОСТИ:",
        "en": "✨ SPELLS AND ABILITIES:",
    },
    "rpg.spells_empty": {
        "ru": "Заклинаний и способностей пока нет.",
        "en": "No spells or abilities yet.",
    },
    "rpg.progression_title": {
        "ru": "Уровень:",
        "en": "Level:",
    },
    "rpg.progression_max": {
        "ru": "МАКСИМУМ",
        "en": "MAX",
    },
    "rpg.progression_to_next": {
        "ru": "до след.",
        "en": "to next",
    },
    "rpg.progression_points": {
        "ru": "Очки:",
        "en": "Points:",
    },
    "rpg.effects_title": {
        "ru": "Эффекты:",
        "en": "Effects:",
    },
    "rpg.effects_empty": {
        "ru": "Активных эффектов нет.",
        "en": "No active effects.",
    },
    "rpg.quests_title": {
        "ru": "📜 КВЕСТЫ:",
        "en": "📜 QUESTS:",
    },
    "rpg.quests_active": {
        "ru": "Активные:",
        "en": "Active:",
    },
    "rpg.quests_active_empty": {
        "ru": "Активных квестов нет.",
        "en": "No active quests.",
    },
    "rpg.quests_done": {
        "ru": "Завершённые:",
        "en": "Completed:",
    },
    "rpg.npcs_title": {
        "ru": "👥 ПЕРСОНАЖИ (NPC):",
        "en": "👥 CHARACTERS (NPC):",
    },
    "rpg.npcs_empty": {
        "ru": "NPC пока не добавлены.",
        "en": "No NPC added yet.",
    },
    "rpg.npc_voice": {
        "ru": "голос:",
        "en": "voice:",
    },
    "rpg.npc_relation": {
        "ru": "отношение:",
        "en": "relation:",
    },
    "rpg.time_title": {
        "ru": "Время:",
        "en": "Time:",
    },
    "rpg.day": {
        "ru": "День",
        "en": "Day",
    },
    "rpg.weather": {
        "ru": "погода:",
        "en": "weather:",
    },
    "rpg.time_part_dawn": {
        "ru": "рассвет",
        "en": "dawn",
    },
    "rpg.time_part_morning": {
        "ru": "утро",
        "en": "morning",
    },
    "rpg.time_part_noon": {
        "ru": "полдень",
        "en": "noon",
    },
    "rpg.time_part_afternoon": {
        "ru": "день",
        "en": "afternoon",
    },
    "rpg.time_part_evening": {
        "ru": "вечер",
        "en": "evening",
    },
    "rpg.time_part_sunset": {
        "ru": "закат",
        "en": "sunset",
    },
    "rpg.time_part_night": {
        "ru": "ночь",
        "en": "night",
    },
    "rpg.time_part_late_night": {
        "ru": "глубокая ночь",
        "en": "late night",
    },
    "rpg.journal_title": {
        "ru": "📓 ДНЕВНИК СОБЫТИЙ:",
        "en": "📓 EVENT JOURNAL:",
    },
    "rpg.journal_empty": {
        "ru": "Событий пока нет.",
        "en": "No events yet.",
    },
    "rpg.macros_title": {
        "ru": "⚡ МАКРОСЫ:",
        "en": "⚡ MACROS:",
    },
    "rpg.macros_empty": {
        "ru": "Макросов нет.",
        "en": "No macros.",
    },
    # ── game/world.py ────────────────────────────────────────────────────
    "world.show_title": {
        "ru": "🌍 СОСТОЯНИЕ МИРА:",
        "en": "🌍 WORLD STATE:",
    },
    "world.location": {
        "ru": "Локация:",
        "en": "Location:",
    },
    "world.visited": {
        "ru": "Посещено:",
        "en": "Visited:",
    },
    "world.facts": {
        "ru": "Факты:",
        "en": "Facts:",
    },
    "world.facts_empty": {
        "ru": "Фактов пока нет.",
        "en": "No facts yet.",
    },
    "world.voices": {
        "ru": "Голоса NPC:",
        "en": "NPC Voices:",
    },
    "world.voices_empty": {
        "ru": "Голоса NPC не заданы.",
        "en": "No NPC voices set.",
    },
    "world.map_title": {
        "ru": "🗺 КАРТА ЛОКАЦИЙ:",
        "en": "🗺 LOCATION MAP:",
    },
    "world.map_empty": {
        "ru": "Карта пуста. Используйте !идти и !связь.",
        "en": "Map empty. Use !goto and !link.",
    },
    "world.map_visited": {
        "ru": "Посещено:",
        "en": "Visited:",
    },
    "world.map_links": {
        "ru": "Связи:",
        "en": "Links:",
    },
    # ── game/stats.py ────────────────────────────────────────────────────
    "stats.title": {
        "ru": "📊 СТАТИСТИКА ЗАПРОСОВ ПО ПРОВАЙДЕРАМ:",
        "en": "📊 REQUEST STATISTICS BY PROVIDER:",
    },
    "stats.row": {
        "ru": "  {status} {name:<12} запросов: {req:<4} ок: {ok:<4} ошибок: {err:<3} токенов: {tok}",
        "en": "  {status} {name:<12} requests: {req:<4} ok: {ok:<4} errors: {err:<3} tokens: {tok}",
    },
    "stats.total": {
        "ru": "Итого:",
        "en": "Total:",
    },
    "stats.limits": {
        "ru": "💡 Лимиты: OpenRouter ~50/день, Gemini ~1500/день, Groq ~14400/день (по токенам ~500k/день)",
        "en": "💡 Limits: OpenRouter ~50/day, Gemini ~1500/day, Groq ~14400/day (~500k tokens/day)",
    },
    # ── game/session.py ──────────────────────────────────────────────────
    "session.compressing": {
        "ru": "⏳ Сжимаю историю...",
        "en": "⏳ Compressing history...",
    },
    # ── game/commands.py ─────────────────────────────────────────────────
    "cmd.mode_auto": {
        "ru": "авто",
        "en": "auto",
    },
    "cmd.mode_smart": {
        "ru": "умные",
        "en": "smart",
    },
    "cmd.mode_medium": {
        "ru": "средние",
        "en": "medium",
    },
    "cmd.mode_fast": {
        "ru": "тупые",
        "en": "fast",
    },
    "cmd.mode_model": {
        "ru": "модель",
        "en": "model",
    },
    "cmd.detail_custom": {
        "ru": "обычный",
        "en": "normal",
    },
    "cmd.mode_label": {
        "ru": "Режим:",
        "en": "Mode:",
    },
    "cmd.model_label": {
        "ru": "модель",
        "en": "model",
    },
    "cmd.model_responding": {
        "ru": "отвечает",
        "en": "responding via",
    },
    "cmd.model_first_try": {
        "ru": "первым попробует (ещё не проверено)",
        "en": "will try first (untested)",
    },
    "cmd.models_blocked": {
        "ru": "заблокировано: {n}",
        "en": "blocked: {n}",
    },
    "world.map_you_are_here": {
        "ru": "ты здесь",
        "en": "you are here",
    },
    "help.fight_ex": {
        "ru": "бой с трекингом HP: крит 20 = двойной урон, победа даёт опыт",
        "en": "combat with HP tracking: nat 20 = double damage, kills grant XP",
    },
    "help.rest": {
        "ru": "долгий отдых: полное HP, снятие эффектов, +8 часов",
        "en": "long rest: full HP, clear effects, +8 hours",
    },
    "help.gold": {
        "ru": "кошелёк: показать или изменить золото",
        "en": "purse: show or adjust gold",
    },
    "help.cast": {
        "ru": "произнести заклинание (тратит ячейку) / остаток ячеек",
        "en": "cast a spell (spends a slot) / slots left",
    },
    "help.rewrite": {
        "ru": "перегенерировать последний ответ мастера",
        "en": "regenerate the last DM response",
    },
    "help.full_list": {
        "ru": "полный список команд",
        "en": "full command list",
    },
    "help.summary": {
        "ru": "вся ситуация одной панелью",
        "en": "whole situation in one panel",
    },
    "help.chronicle": {
        "ru": "экспорт истории партии в markdown",
        "en": "export party history to markdown",
    },
    "help.equip": {
        "ru": "экипировка: оружие задаёт урон, броня/щит дают КД",
        "en": "equipment: weapon sets damage dice, armor/shield add AC",
    },
    "help.shop": {
        "ru": "торговля (цена из прайса или своя)",
        "en": "trade (price from list or custom)",
    },
    "help.rep": {
        "ru": "отношение фракций к партии",
        "en": "faction reputation",
    },
    "cmd.detail_label": {
        "ru": "детализация",
        "en": "detail",
    },
    "cmd.history_cleared": {
        "ru": "♻️  История очищена.",
        "en": "♻️  History cleared.",
    },
    "cmd.exiting": {
        "ru": "✅ Выхожу. До встречи!",
        "en": "✅ Exiting. See you!",
    },
    # ── Language switching ───────────────────────────────────────────────
    "lang.switched": {
        "ru": "🌐 Язык переключён на русский",
        "en": "🌐 Language switched to English",
    },
    # ── v2.2: категории моделей, детализация, лечение, бой ──────────────
    "meta.category_set": {
        "ru": "Категория моделей: {label}",
        "en": "Model category: {label}",
    },
    "meta.category_switch_hint": {
        "ru": "переключение: {cats}",
        "en": "switch: {cats}",
    },
    "meta.blocked_mark": {
        "ru": "[блок]",
        "en": "[blocked]",
    },
    "meta.no_models_for_tier": {
        "ru": "(нет доступных провайдеров с моделями этой категории)",
        "en": "(no providers with models in this category)",
    },
    "meta.blacklist_size": {
        "ru": "⛔ Во временном блок-листе связок провайдер:модель: {n}",
        "en": "⛔ Temporarily blocked provider:model pairs: {n}",
    },
    "meta.detail_now": {
        "ru": "Детализация: {level}",
        "en": "Detail level: {level}",
    },
    "meta.current_model": {
        "ru": "Текущая модель",
        "en": "Current model",
    },
    "meta.model_none_auto": {
        "ru": "Модель не выбрана (авто)",
        "en": "No model forced (auto)",
    },
    "meta.provider_not_found": {
        "ru": "Провайдер не найден. Доступные: {list}",
        "en": "Provider not found. Available: {list}",
    },
    "meta.provider_unavailable": {
        "ru": "Провайдер {name} недоступен (нет ключа)",
        "en": "Provider {name} unavailable (no API key)",
    },
    "meta.model_unavailable_at": {
        "ru": "Модель {model} недоступна у {provider}. Доступные: {list}…",
        "en": "Model {model} unavailable at {provider}. Available: {list}…",
    },
    "meta.model_switch_failed": {
        "ru": "Не удалось определить модель для {provider}",
        "en": "Could not pick a model for {provider}",
    },
    "meta.model_switched": {
        "ru": "Модель переключена: {model}",
        "en": "Model switched: {model}",
    },
    "meta.classes_title": {
        "ru": "📋 Доступные архетипы классов:",
        "en": "📋 Available class archetypes:",
    },
    "meta.classes_any_note": {
        "ru": "Можете ввести любой класс — система примет любое название.",
        "en": "Any class name is accepted — the system takes anything.",
    },
    "meta.classes_hint_create": {
        "ru": "При создании: !персонаж Имя, Класс, HP, КД",
        "en": "To create: !character Name, Class, HP, AC",
    },
    "help.providers_title": {
        "ru": "Доступные провайдеры и модели:",
        "en": "Available providers and models:",
    },
    "help.categories": {
        "ru": "категория моделей (умные/средние/быстрые)",
        "en": "model category (smart/balanced/fast)",
    },
    "main.switch_model_hint": {
        "ru": "Подождите немного или попробуйте сменить модель командой /model",
        "en": "Wait a moment or switch models with /model",
    },
    "api.stream_truncated": {
        "ru": "⚠️ [ответ модели оборван — часть текста могла потеряться]",
        "en": "⚠️ [model response was cut off — part of the text may be missing]",
    },
    "rpg.hp_gain": {
        "ru": "+{amt} max HP (HP {hp}/{max_hp})",
        "en": "+{amt} max HP (HP {hp}/{max_hp})",
    },
    "rpg.rest_in_combat": {
        "ru": "Рядом враги — сейчас не до отдыха!",
        "en": "Enemies nearby — no time to rest!",
    },
    "rpg.cast_healed": {
        "ru": "💚 Исцелено {amt} HP. Теперь HP {hp}/{max_hp}",
        "en": "💚 Healed {amt} HP. Now HP {hp}/{max_hp}",
    },
    "combat.hit_while_down": {
        "ru": "☠ Удар по лежащему: провалов смерти {fails}/3",
        "en": "☠ Hit while down: {fails}/3 death save failures",
    },
    "stats.reset_ok": {
        "ru": "Статистика запросов сброшена",
        "en": "Request statistics reset",
    },
    "party.removed": {
        "ru": "🏴 Персонаж {name} покинул партию",
        "en": "🏴 Character {name} left the party",
    },
    "party.remove_last": {
        "ru": "Последнего персонажа удалить нельзя ({names}). Создайте второго через !новый",
        "en": "Can't remove the last character ({names}). Create another one with !new",
    },
    "party.now_playing": {
        "ru": "Остались: {list}",
        "en": "Remaining: {list}",
    },
    "party.not_found_named": {
        "ru": "Персонаж «{name}» не найден. В партии: {list}",
        "en": "Character '{name}' not found. Party: {list}",
    },
    "world.exits_from": {
        "ru": "· оттуда ведут пути: {list}",
        "en": "· paths lead to: {list}",
    },
    "main.fatal_error": {
        "ru": "💥 Непредвиденная ошибка: {hint}\nПодробности в логе (LOG_LEVEL=DEBUG в .env)",
        "en": "💥 Unexpected error: {hint}\nDetails in the log (LOG_LEVEL=DEBUG in .env)",
    },
    "help.party_remove": {
        "ru": "удалить персонажа из партии",
        "en": "remove a character from the party",
    },
    # ── Экономика рынка (v1.2) ───────────────────────────────────────────
    "shop.offer_ignored": {
        "ru": "Своя цена {offer} не применяется — здесь {price} монет",
        "en": "Custom price {offer} is ignored — local price is {price} coins",
    },
    "help.market": {
        "ru": "цены и профиль рынка (!рынок; тип/достаток/сброс)",
        "en": "market prices and profile (!market; type/wealth/reset)",
    },
    "market.title": {
        "ru": "🛒 РЫНОК: <<{loc}>>",
        "en": "🛒 MARKET: <<{loc}>>",
    },
    "market.size_hamlet": {"ru": "хутор", "en": "hamlet"},
    "market.size_village": {"ru": "деревня", "en": "village"},
    "market.size_settlement": {"ru": "посёлок", "en": "settlement"},
    "market.size_town": {"ru": "городок", "en": "town"},
    "market.size_city": {"ru": "город", "en": "city"},
    "market.size_capital": {"ru": "столица", "en": "capital"},
    "market.wealth_poor": {"ru": "бедный", "en": "poor"},
    "market.wealth_normal": {"ru": "обычный", "en": "normal"},
    "market.wealth_rich": {"ru": "богатый", "en": "rich"},
    "market.tag_smith": {"ru": "кузнечный", "en": "smith"},
    "market.tag_port": {"ru": "портовый", "en": "port"},
    "market.src_auto": {"ru": "по имени", "en": "by name"},
    "market.src_dm": {"ru": "мастер", "en": "dm"},
    "market.src_manual": {"ru": "вручную", "en": "manual"},
    "market.wealth_part": {
        "ru": "достаток: {wealth} ({src})",
        "en": "wealth: {wealth} ({src})",
    },
    "market.tags_part": {"ru": "теги: {tags}", "en": "tags: {tags}"},
    "market.profile_neutral": {
        "ru": "обычные цены (профиль не задан)",
        "en": "standard prices (no profile)",
    },
    "market.conditions_line": {
        "ru": "Условия: {conds} (итог {total})",
        "en": "Conditions: {conds} (total {total})",
    },
    "market.conditions_none": {
        "ru": "Условия: без изменений",
        "en": "Conditions: none",
    },
    "market.prices_header": {"ru": "Покупка / скупка:", "en": "Buy / sell:"},
    "market.mark_dm": {"ru": " (мастер)", "en": " (dm)"},
    "market.hint": {
        "ru": "Настроить: !рынок тип хутор|деревня|посёлок|городок|город|столица · "
        "!рынок достаток бедный|обычный|богатый · !рынок сброс",
        "en": "Tune: !market type hamlet|village|settlement|town|city|capital · "
        "!market wealth poor|normal|rich · !market reset",
    },
    "market.no_location": {
        "ru": "Сначала нужно оказаться в локации (!идти <<место>>).",
        "en": "You need to be in a location first (!go <<place>>).",
    },
    "market.unknown_value": {
        "ru": "Не знаю значения «{value}». Доступно: {options}",
        "en": "Unknown value '{value}'. Available: {options}",
    },
    "market.size_options": {
        "ru": "хутор|деревня|посёлок|городок|город|столица",
        "en": "hamlet|village|settlement|town|city|capital",
    },
    "market.wealth_options": {"ru": "бедный|обычный|богатый", "en": "poor|normal|rich"},
    "market.type_set": {
        "ru": "✅ Рынок <<{loc}>>: тип — {size} (вручную)",
        "en": "✅ Market <<{loc}>>: size — {size} (manual)",
    },
    "market.wealth_set": {
        "ru": "✅ Рынок <<{loc}>>: достаток — {wealth} (вручную)",
        "en": "✅ Market <<{loc}>>: wealth — {wealth} (manual)",
    },
    "market.reset_done": {
        "ru": "↩️ Рынок <<{loc}>>: ручные настройки и наценки сняты.",
        "en": "↩️ Market <<{loc}>>: manual settings and overrides cleared.",
    },
    "market.reset_none": {
        "ru": "У рынка <<{loc}>> нет ручных настроек.",
        "en": "Market <<{loc}>> has no manual settings.",
    },
    "market.note_profile": {
        "ru": "⚖ Рынок <<{loc}>>: {parts}",
        "en": "⚖ Market <<{loc}>>: {parts}",
    },
    "market.note_price": {
        "ru": "⚖ Цена «{item}»: {price} монет",
        "en": "⚖ Price of '{item}': {price} coins",
    },
    "market.note_clamped": {
        "ru": "⚖ Цена «{item}» ограничена коридором ±×2 — стала {price} монет",
        "en": "⚖ Price of '{item}' clamped to ±×2 — now {price} coins",
    },
    "market.note_unknown": {
        "ru": "⚖ «{item}» не в каталоге — мастеру: сначала [[ТОВАР: имя|база|категория]]",
        "en": "⚖ '{item}' is not in the catalog — DM: use [[GOOD: name|base|category]] first",
    },
    "market.note_cap_price": {
        "ru": "⚖ Слишком много [[ЦЕНА]] за ход — лишние пропущены",
        "en": "⚖ Too many [[PRICE]] markers this turn — extras skipped",
    },
    "market.note_cap_good": {
        "ru": "⚖ Слишком много [[ТОВАР]] за ход — лишние пропущены",
        "en": "⚖ Too many [[GOOD]] markers this turn — extras skipped",
    },
    "market.note_good": {
        "ru": "⚖ Новый товар: «{name}» — {base} монет",
        "en": "⚖ New good: '{name}' — {base} coins",
    },
    "market.note_known": {
        "ru": "⚖ «{name}» уже в прайсе торговца — [[ТОВАР]] не нужен",
        "en": "⚖ '{name}' is already in the merchant price list — no [[GOOD]] needed",
    },
    "market.note_registry_full": {
        "ru": "⚖ Каталог товаров полон — [[ТОВАР]] пропущен",
        "en": "⚖ Goods registry is full — [[GOOD]] skipped",
    },
}


def set_lang(lang: str):
    """Set current language ('ru' or 'en')."""
    global _lang
    _lang = lang.lower() if lang.lower() in ("ru", "en") else "ru"


def get_lang() -> str:
    """Get current language code."""
    return _lang


def t(key: str, **kwargs) -> str:
    """Translate a key to the current language.

    Supports {placeholder} substitution:
        t("main.session_loaded", session="default")
    """
    entry = _T.get(key)
    if entry is None:
        return key  # fallback: return the key itself
    template = entry.get(_lang) or entry.get("ru") or key
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
    return template


def variants(key: str) -> list:
    """Все переводы ключа на всех языках.

    Нужно для языконезависимого сравнения текста (например, детект
    первого сообщения игры в любом режиме локали).
    """
    entry = _T.get(key)
    if not entry:
        return []
    return [v for v in entry.values() if isinstance(v, str)]
