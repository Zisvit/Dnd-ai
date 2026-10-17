"""RPG-системы: заклинания, уровни, статус-эффекты, квесты, время,
погода, журнал, макросы, тон/жанр, тихий режим, проверка фактов."""
import re
import random

from dndai.commands.context import GameContext
from dndai.commands.result import CommandResult
from dndai.game.rpg import (
    parse_spell_command, parse_quest_command, parse_status_command,
    parse_macro_command,
)
from dndai.core.colors import GREEN, RED, YELLOW, CYAN, BLUE, RESET
from dndai.core.text import emoji
from dndai.core.i18n import t


# ── Заклинания ──
def spell_command(act, ctx: GameContext):
    parsed = parse_spell_command(act)
    if parsed:
        action, data = parsed
        if action == "spell_add":
            name, desc, dmg, dc = data
            if ctx.spells.add(name, desc, dmg=dmg, save_dc=dc):
                extra = []
                if dmg:
                    extra.append(t('rpg.spell_dmg', dmg=dmg))
                if dc:
                    extra.append(t('rpg.spell_dc', dc=dc))
                ex = f" ({', '.join(extra)})" if extra else ""
                ctx.persist()
                return CommandResult(f"{GREEN}{t('rpg.spell_added', name=name, extra=ex)}{RESET}")
            return CommandResult(f"{YELLOW}{t('rpg.spell_add_fail')}{RESET}")

    if re.match(r'(?i)!?\s*закл(?:инания)?\s*$', act) or re.match(r'(?i)!?\s*spells\s*$', act):
        ctx.spells.show()
        return CommandResult.silent()

    m_del = re.match(r'(?i)!?\s*закл(?:инание)?\s+удал(?:ить)?\s+(\S+)', act)
    if m_del:
        if ctx.spells.remove(m_del.group(1)):
            ctx.persist()
            return CommandResult(f"{GREEN}{t('rpg.spell_removed')}{RESET}")
        return CommandResult(f"{YELLOW}{t('rpg.spell_not_found')}{RESET}")
    return None


# ── Уровни и опыт ──
def xp_command(act, ctx: GameContext):
    m = re.match(r'(?i)!?\s*(?:xp|опыт)\s+(\d+)', act)
    if m:
        from dndai.commands.rewards import sync_levels
        lvl = ctx.prog.add_xp(int(m.group(1)))
        out = f"{GREEN}{t('rpg.xp_gained', xp=m.group(1))}{RESET}"
        for line in sync_levels(ctx, lvl):
            out += f"\n{line}"
        ctx.persist()
        return CommandResult(out)

    if re.match(r'(?i)!?\s*(?:лвл|уровень|level)\s*$', act):
        ctx.prog.show()
        return CommandResult.silent()

    m_up = re.match(r'(?i)!?\s*(?:улучшить|statup)\s+(\w+)\s+(\d+)', act)
    if m_up:
        stat = m_up.group(1).upper()
        amt = int(m_up.group(2))
        if ctx.prog.xp_bonus >= amt and stat in ("STR", "DEX", "CON", "INT", "WIS", "CHA"):
            ctx.prog.xp_bonus -= amt
            ctx.character.stats[stat] = ctx.character.stats.get(stat, 10) + amt
            ctx.persist()
            return CommandResult(
                f"{GREEN}{t('rpg.statup_ok', stat=stat, amt=amt, left=ctx.prog.xp_bonus)}{RESET}")
        return CommandResult(
            f"{YELLOW}{t('rpg.statup_fail', pts=ctx.prog.xp_bonus, stat=stat)}{RESET}")
    return None


# ── Статус-эффекты ──
def status_command(act, ctx: GameContext):
    parsed = parse_status_command(act)
    if parsed:
        action, data = parsed
        if action == "status_add":
            name, rounds = data
            if ctx.status.add(name, rounds):
                desc = ctx.status.KNOWN.get(name, "")
                d = f" — {desc}" if desc else ""
                ctx.persist()
                return CommandResult(
                    f"{GREEN}{t('rpg.effect_applied', name=name, rounds=rounds, desc=d)}{RESET}")
            return CommandResult(f"{YELLOW}{t('rpg.effect_apply_fail')}{RESET}")

    if (re.match(r'(?i)!?\s*статус-эффект\s+удал(?:ить)?\s+(\S+)', act)
            or re.match(r'(?i)!?\s*эффект\s+удал(?:ить)?\s+(\S+)', act)):
        m = re.search(r'(?i)(?:статус-эффект|эффект)\s+удал(?:ить)?\s+(\S+)', act)
        if m and ctx.status.remove(m.group(1)):
            ctx.persist()
            return CommandResult(f"{GREEN}{t('rpg.effect_removed')}{RESET}")
        return CommandResult(f"{YELLOW}{t('rpg.effect_not_found')}{RESET}")

    if re.match(r'(?i)!?\s*(?:эффекты|статус)\s*$', act):
        ctx.status.show()
        return CommandResult.silent()
    return None


# ── Квесты ──
def quest_command(act, ctx: GameContext):
    parsed = parse_quest_command(act)
    if parsed:
        action, data = parsed
        if action == "quest_add":
            title, desc = data
            if ctx.quests.add(title, desc):
                ctx.persist()
                return CommandResult(f"{GREEN}{t('rpg.quest_added', title=title)}{RESET}")
            return CommandResult(f"{YELLOW}{t('rpg.quest_exists')}{RESET}")
        if action == "quest_done":
            done = ctx.quests.complete(data)
            if done:
                from dndai.commands.rewards import sync_levels
                lvl = ctx.prog.add_xp(100)
                out = f"{GREEN}{t('rpg.quest_done', title=done)}{RESET}"
                for line in sync_levels(ctx, lvl):
                    out += f"\n{line}"
                ctx.persist()
                return CommandResult(out)
            return CommandResult(f"{YELLOW}{t('rpg.quest_not_found')}{RESET}")
        if action == "quest_del":
            rem = ctx.quests.abandon(data)
            if rem:
                ctx.persist()
                return CommandResult(f"{YELLOW}{t('rpg.quest_removed', title=rem)}{RESET}")
            return CommandResult(f"{YELLOW}{t('rpg.quest_not_found')}{RESET}")
        return None

    if re.match(r'(?i)!?\s*квесты\s*$', act):
        ctx.quests.show()
        return CommandResult.silent()
    return None


# ── Время и погода ──
def time_command(act, ctx: GameContext):
    m = re.match(r'(?i)!?\s*время\s+(?:\+)?(\d+)\s*(ч|h|час)?', act)
    if m:
        ctx.timew.advance(int(m.group(1)))
        ctx.persist()
        info = t('rpg.time_info', day=ctx.timew.day, part=ctx.timew._part(),
                 hour=f"{ctx.timew.hour:02d}", weather=ctx.timew.weather)
        return CommandResult(
            f"{CYAN}{emoji('⏰')} {t('rpg.time_advanced')}{RESET}\n"
            f"  {GREEN}{info}{RESET}")
    if re.match(r'(?i)!?\s*время\s*$', act):
        info = t('rpg.time_info', day=ctx.timew.day, part=ctx.timew._part(),
                 hour=f"{ctx.timew.hour:02d}", weather=ctx.timew.weather)
        return CommandResult(
            f"  {GREEN}{info}{RESET}")
    return None


def weather_command(act, ctx: GameContext):
    m = re.match(r'(?i)!?\s*погода\s+(.+)', act)
    if m:
        w = m.group(1).strip().lower()
        if ctx.timew.set_weather(w):
            ctx.persist()
            return CommandResult(
                f"{CYAN}{emoji('🌤')} "
                f"{t('rpg.weather_set', weather=ctx.timew.weather)}{RESET}")
        weathers = ', '.join(ctx.timew.WEATHERS)
        return CommandResult(
            f"{YELLOW}{t('rpg.weather_unknown', list=weathers)}{RESET}")
    return None


# ── Журнал ──
def journal_command(act, ctx: GameContext):
    author = ctx.party.active_name if ctx.party else (ctx.player_name or "player")
    m = re.match(r'(?i)!?\s*запись\s+(.+)', act)
    if m:
        text = f"[{author}] {m.group(1)}"
        if ctx.journal.add(text, day=ctx.timew.day, part=ctx.timew._part()):
            ctx.persist()
            return CommandResult(f"{GREEN}{t('rpg.journal_added')}{RESET}")
        return None
    if re.match(r'(?i)!?\s*(?:журнал|дневник|лог)\s*$', act):
        ctx.journal.show(10)
        return CommandResult.silent()
    return None


# ── Макросы ──
def macro_command(act, ctx: GameContext):
    parsed = parse_macro_command(act)
    if parsed:
        action, data = parsed
        if action == "macro_add":
            name, cmd = data
            if ctx.macros.add(name, cmd):
                ctx.persist()
                return CommandResult(f"{GREEN}{t('rpg.macro_added', name=name, cmd=cmd)}{RESET}")
            return CommandResult(f"{YELLOW}{t('rpg.macro_add_fail')}{RESET}")
        if action == "macro_del":
            if ctx.macros.remove(data):
                ctx.persist()
                return CommandResult(f"{GREEN}{t('rpg.macro_removed')}{RESET}")
            return None
    if re.match(r'(?i)!?\s*макросы\s*$', act):
        ctx.macros.show()
        return CommandResult.silent()
    return None


# ── Тон и жанр ──
def style_command(act, ctx: GameContext):
    m_tone = re.match(r'(?i)!?\s*тон\s+(.+)', act)
    if m_tone:
        if ctx.style.set_tone(m_tone.group(1)):
            ctx.persist()
            return CommandResult(
                f"{GREEN}{emoji('🎭')} "
                f"{t('rpg.tone_set', tone=ctx.style.tone)}{RESET}")
        tones = ', '.join(ctx.style.TONES)
        return CommandResult(
            f"{YELLOW}{t('rpg.tone_unknown', tone=m_tone.group(1), list=tones)}{RESET}")

    m_genre = re.match(r'(?i)!?\s*жанр\s+(.+)', act)
    if m_genre:
        if ctx.style.set_genre(m_genre.group(1)):
            ctx.persist()
            return CommandResult(
                f"{GREEN}{emoji('🎭')} "
                f"{t('rpg.genre_set', genre=ctx.style.genre)}{RESET}")
        genres = ', '.join(ctx.style.GENRES)
        return CommandResult(
            f"{YELLOW}{t('rpg.genre_unknown', genre=m_genre.group(1), list=genres)}{RESET}")

    if re.match(r'(?i)!?\s*(?:тон|жанр|стиль)\s*$', act):
        info = t('rpg.style_info', tone=ctx.style.tone or '—',
                 genre=ctx.style.genre or '—')
        return CommandResult(f"  {info}")
    return None


# ── Долгий отдых ──
def rest_command(act, ctx: GameContext):
    """`!отдых` — долгий отдых: полное HP, снятие эффектов, ячейки и +8 часов.

    В активном бою отдых невозможен — враги не ждут."""
    if not re.match(r'(?i)!?\s*(?:отдых|longrest|сон|rest)\s*$', act):
        return None
    if ctx.enemies is not None and len(ctx.enemies) > 0:
        return CommandResult(
            f"{RED}{emoji('⚔️')} {t('rpg.rest_in_combat')}{RESET}")
    c = ctx.character
    healed = c.max_hp - c.hp
    c.hp = c.max_hp
    removed = [e["name"] for e in ctx.status.effects]
    ctx.status.effects = []
    restored = ctx.spells.restore_slots() if ctx.spells else 0
    c.reset_death_saves()
    ctx.timew.advance(8)
    ctx.persist()
    hour_str = "%02d" % ctx.timew.hour
    msg = t('rpg.rest_done', day=ctx.timew.day,
            hour=hour_str, hp=c.hp, max_hp=c.max_hp)
    out = f"{GREEN}{emoji('🛏')} {msg}{RESET}"
    if healed:
        out += f"\n  {GREEN}{t('rpg.rest_healed', amt=healed)}{RESET}"
    if restored:
        out += f"\n  {BLUE}{t('rpg.rest_slots', n=restored)}{RESET}"
    if removed:
        out += f"\n  {YELLOW}{t('rpg.rest_effects_cleared', names=', '.join(removed))}{RESET}"
    return CommandResult(out)


# ── Репутация фракций ──
def reputation_command(act, ctx: GameContext):
    """`!репутация` — отношение фракций к партии."""
    if not re.match(r'(?i)!?\s*(?:репутац\w*|rep)\s*$', act):
        return None
    if ctx.reputation is None:
        return None
    ctx.reputation.show()
    return CommandResult.silent()


# ── Добавление врага без раунда боя ──
def enemy_add_command(act, ctx: GameContext):
    """`!враг Имя HP КД` — добавить врага в бой (бросает инициативу)."""
    m = re.match(r'(?i)!?\s*(?:враг|enemy)\s+(\S+)\s+(\d+)(?:\s+(\d+))?\s*$', act)
    if not m:
        return None
    name = m.group(1).strip("{}").strip()
    hp = int(m.group(2))
    ac = int(m.group(3)) if m.group(3) else 10
    e = ctx.enemies.add(name, hp=hp, ac=ac)
    if e:
        ctx.persist()
        return CommandResult(
            f"{RED}{t('combat.enemy_joined', name=name, hp=hp, ac=ac)}"
            f" ({t('combat.initiative')} {e['init']}){RESET}")
    return CommandResult(f"{YELLOW}{t('combat.enemy_exists', name=name)}{RESET}")


# ── Стабилизация при смертельных ранениях ──
def stabilize_command(act, ctx: GameContext):
    """`!стабилизироваться` / `!медицина` — проверка WIS (СЛ 10) у умирающего."""
    if not re.match(r'(?i)!?\s*(?:стабилиз|медицина|medicine|стабилизироваться)\w*\s*$', act):
        return None
    c = ctx.character
    if not c.is_dying and c.hp > 0:
        return CommandResult(f"{YELLOW}{t('combat.not_dying')}{RESET}")
    if c.death_saves["stabilized"]:
        return CommandResult(f"{YELLOW}{t('combat.already_stable')}{RESET}")
    wis_mod = c.modifier("WIS")
    roll = random.randint(1, 20) + wis_mod
    if roll >= 10 or c.death_saves["successes"] >= 3:
        c.stabilize()
        ctx.persist()
        return CommandResult(
            f"{GREEN}{emoji('✚')} {t('combat.stabilized_ok', roll=roll)}{RESET}")
    c.death_saves["failures"] += 1
    ctx.persist()
    if c.death_saves["failures"] >= 3:
        return CommandResult(f"{RED}{emoji('💀')} {t('main.you_died')}{RESET}")
    return CommandResult(
        f"{RED}{t('combat.stabilize_fail', roll=roll, fails=c.death_saves['failures'])}{RESET}")


# ── Тихий режим ──
def quiet_command(act, ctx: GameContext):
    m = re.match(r'(?i)!?\s*тихо\s+(вкл|on|выкл|off)', act)
    if m:
        ctx.quiet_mode["on"] = m.group(1).lower() in ("вкл", "on")
        msg = t('rpg.quiet_on') if ctx.quiet_mode["on"] else t('rpg.quiet_off')
        return CommandResult(f"{GREEN}{emoji('🔇')} {msg}{RESET}")
    return None


# ── Проверка соответствия фактам ──
def check_command(act, ctx: GameContext):
    m = re.match(r'(?i)!?\s*проверка\s+(.+)', act)
    if not m:
        return None
    claim = m.group(1).strip()
    conflicts = _check_fact_conflict(claim, ctx.world.facts)
    if conflicts:
        out = f"{RED}{t('rpg.check_conflict')}{RESET}"
        for c in conflicts:
            out += f"\n  • {c}"
        return CommandResult(out)
    return CommandResult(f"{GREEN}{t('rpg.check_ok')}{RESET}")


def _fact_words(text):
    stop = {"этот", "эта", "это", "тот", "там", "здесь", "когда", "где",
            "что", "котор", "такой", "такое", "быть", "есть", "наш", "ваш",
            "их", "свой", "весь", "всё", "ещё", "уже", "только", "самый"}
    words = set()
    for w in re.findall(r'[а-яёa-z0-9]+', text.lower()):
        if len(w) > 3 and w not in stop:
            words.add(w)
    return words


def _check_fact_conflict(claim, facts):
    claim_words = _fact_words(claim)
    if not claim_words:
        return []
    neg_markers = ("не ", "нет", "разреш", "без ", "можно", "дозвол")
    pos_markers = ("запрещ", "нельзя", "нет ", "отсутств")
    conflicts = []
    for fct in facts:
        fact_words = _fact_words(fct)
        shared = claim_words & fact_words
        if len(shared) < 2:
            continue
        claim_l = claim.lower()
        fct_l = fct.lower()
        claim_neg = any(mk in claim_l for mk in neg_markers)
        fact_neg = any(mk in fct_l for mk in pos_markers)
        if claim_neg and fact_neg:
            conflicts.append(fct)
            continue
        if claim_neg and len(shared) >= len(fact_words) - 1:
            conflicts.append(fct)
            continue
        if any(f"не {w}" in claim_l or f"{w} не" in claim_l for w in fact_words):
            conflicts.append(fct)
    return conflicts
