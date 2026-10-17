"""Боевые команды: спасбросок, полноценный бой с HP врагов и уроном.

Эти команды не завершают ход — они готовят контекст и возвращают
rewrite_act, который main передаёт мастеру для описания."""
import re

from dndai.commands.context import GameContext
from dndai.commands.result import CommandResult
from dndai.core.colors import BLUE, GREEN, RED, RESET, YELLOW
from dndai.core.dice import roll_dice
from dndai.core.i18n import t
from dndai.core.text import emoji


def save_command(act, ctx: GameContext):
    m = re.match(r'(?i)!?\s*спас\s+(\w+)\s+(\d+)', act)
    if not m:
        return None
    stat = m.group(1).upper()
    dc = int(m.group(2))
    char = ctx.character
    mod = char.modifier(stat) if hasattr(char, 'modifier') else 0
    sb = ctx.status.save_bonus()
    roll, _ = roll_dice(f"1d20+{mod + sb}")
    success = roll >= dc
    res = (f"{GREEN}{t('combat.save_success')}{RESET}" if success
           else f"{RED}{t('combat.save_fail')}{RESET}")
    bonus = t('combat.save_bonus_note', sb=sb) if sb else ""
    text = (f"{BLUE}{emoji('🎲')} "
            f"{t('combat.save_result', stat=stat, mod=mod, bonus=bonus, dc=dc, roll=roll, result=res)}"
            f"{RESET}")
    rewrite = (f"[МЕХАНИКА: спасбросок {stat} против СЛ {dc} уже брошен системой: "
               f"итог {roll} → {'УСПЕХ' if success else 'ПРОВАЛ'}. "
               f"Используй в повествовании ИМЕННО этот итог, свои броски не выполняй] " + act)
    return CommandResult(text, stop=False, rewrite_act=rewrite)


def fight_command(act, ctx: GameContext):
    """Полноценный бой: `!бой <имя> <КД> [HP]`.

    Первый вызов вводит врага в бой; каждая следующая команда `!бой имя КД`
    или `!атака имя` — раунд: игрок атакует (d20+модификатор vs КД,
    крит 20 — двойной урон), живые враги контратакуют по инициативе.
    HP врагов хранится в сессии."""
    m = re.match(r'(?i)!?\s*бой\s+(\S+)\s+(\d+)(?:\s+(\d+))?\s*$', act)
    if not m:
        m2 = re.match(r'(?i)!?\s*(?:атака|attack)\s+(.+?)\s*$', act)
        if m2:
            # даже если список врагов пуст — сообщим "враг не найден"
            return _attack_round(m2.group(1).strip(), ctx, act=act)
        if re.match(r'(?i)!?\s*(?:враги|enemies)\s*$', act):
            ctx.enemies.show()
            return CommandResult.silent()
        return None

    mob = m.group(1).strip("{}").strip()
    mob_ac = max(0, min(40, int(m.group(2))))
    mob_hp = int(m.group(3)) if m.group(3) else 10

    enemy = ctx.enemies.find(mob) if ctx.enemies else None
    intro = ""
    if enemy is None:
        enemy = ctx.enemies.add(mob, hp=mob_hp, ac=mob_ac)
        intro = t('combat.enemy_joined', name=mob, hp=mob_hp, ac=mob_ac)
    else:
        intro = t('combat.enemy_exists', name=enemy['name'])

    return _attack_round(enemy['name'], ctx, intro, act)


def _weapon_damage(char):
    """Урон по экипированному оружию (+ модификатор атаки). Кулаки — 1d2."""
    dice = char.weapon_damage_dice() or "1d2"
    dmg, parts = roll_dice(dice)
    dmg += char.attack_modifier() if hasattr(char, 'attack_modifier') else \
        char.modifier("STR")
    return dmg, parts


def _sync_levels(ctx, leveled):
    """Поднимает персонажа до уровней из Progression (+HP, лечение)."""
    from dndai.commands.rewards import sync_levels
    return sync_levels(ctx, leveled)


def _morale_check(ctx, foe):
    """Бросок морали: раненый враг может сдаться или сбежать.

    Возвращает строку сообщения или None (продолжает бой).
    """
    if foe["max_hp"] <= 0:
        return None
    if foe["hp"] / foe["max_hp"] > 0.35:
        return None
    import random
    if random.randint(1, 20) < 12:
        return None  # держится
    xp = max(10, (5 * foe['max_hp']) // 2)  # половина XP за убийство
    ctx.enemies.remove(foe["name"])
    lvl = ctx.prog.add_xp(xp)
    lines = [f"{YELLOW}{emoji('🏃')} {t('combat.morale_flee', name=foe['name'], xp=xp)}{RESET}"]
    lines.extend(_sync_levels(ctx, lvl))
    return "\n".join(lines)


def _attack_round(mob_name, ctx: GameContext, intro="", act=""):
    """Один раунд боя: атака игрока → исход → контратаки ВСЕХ живых
    врагов в порядке инициативы."""
    import random
    char = ctx.character
    enemy = ctx.enemies.find(mob_name)
    if enemy is None:
        return CommandResult(
            f"{YELLOW}{t('combat.no_such_enemy', name=mob_name)}{RESET}")

    mob_ac = enemy["ac"]
    eff_ac = char.ac + char.equip_ac_bonus() + ctx.status.ac_bonus()
    d20 = random.randint(1, 20)
    player_mod = char.attack_modifier() if hasattr(char, 'attack_modifier') else \
        char.modifier("STR")
    crit = d20 == 20
    total = d20 + player_mod
    hit = crit or total >= mob_ac

    lines = [intro] if intro else []
    applied, killed, dmg = 0, False, 0
    if hit:
        dmg, parts = _weapon_damage(char)
        if crit:
            dmg += sum(parts)  # крит: удвоенная порция костей (не модификатора)
        applied, killed = ctx.enemies.damage(enemy["name"], dmg)
        lines.append(t('combat.player_hit', name=enemy['name'], roll=d20,
                       mod=(f"{player_mod:+d}" if player_mod else ""), total=total,
                       ac=mob_ac, dmg=applied,
                       left_hp=enemy['hp'], max_hp=enemy['max_hp'])
                      + (f" 💥 {t('combat.critical')}" if crit else ""))
        if killed:
            xp = max(25, 5 * enemy['max_hp'])
            lvl = ctx.prog.add_xp(xp)
            lines.append(f"{GREEN}{emoji('🏆')} "
                         f"{t('combat.enemy_slain', name=enemy['name'], xp=xp)}{RESET}")
            lines.extend(_sync_levels(ctx, lvl))
        elif enemy in ctx.enemies.enemies:
            morale = _morale_check(ctx, enemy)
            if morale:
                lines.append(morale)
            if ctx.enemies.all_dead():
                lines.append(f"{YELLOW}{emoji('⚔️')} {t('combat.battle_won')}{RESET}")
                char.reset_death_saves()
    else:
        lines.append(t('combat.player_miss', name=enemy['name'], roll=d20,
                       mod=(f"{player_mod:+d}" if player_mod else ""), total=total,
                       ac=mob_ac))

    # Контратака КАЖДОГО живого врага по порядку инициативы.
    # Сила врага масштабируется от его max_hp (mob_attack_stats).
    from dndai.game.rpg import mob_attack_stats
    mdmg_total, mob_hits_desc = 0, []
    hp_at_round_start = char.hp
    for foe in ctx.enemies.attack_order():
        atk_bonus, dmg_dice = mob_attack_stats(foe)
        mob_roll = random.randint(1, 20)
        foe_crit = mob_roll == 20
        mob_hit = foe_crit or (mob_roll + atk_bonus >= eff_ac)
        if mob_hit:
            mdmg, _parts = roll_dice(dmg_dice)
            if foe_crit:
                mdmg += roll_dice(dmg_dice)[0]
            char.hp = max(0, char.hp - mdmg)
            mdmg_total += mdmg
            mob_hits_desc.append(t('combat.mob_hit_you', name=foe['name'],
                                   roll=mob_roll, ac=eff_ac, dmg=mdmg,
                                   hp=char.hp, max_hp=char.max_hp))
            if char.hp <= 0:
                # Урон по лежащему без сознания = провал спасброска
                # смерти (критический удар = два провала) — по RAW 5e.
                if hp_at_round_start > 0:
                    # только что упал без сознания
                    mob_hits_desc.append(
                        f"{RED}{emoji('💀')} {t('combat.dying_intro')}{RESET}")
                char.death_saves["failures"] += 2 if foe_crit else 1
                if char.death_saves["failures"] >= 3:
                    mob_hits_desc.append(f"{RED}{emoji('💀')} {t('main.you_died')}{RESET}")
                    break
                mob_hits_desc.append(
                    f"{RED}{t('combat.hit_while_down', fails=char.death_saves['failures'])}{RESET}")
        else:
            mob_hits_desc.append(t('combat.mob_miss_you', name=foe['name'],
                                   roll=mob_roll, ac=eff_ac))

    lines.extend(mob_hits_desc)

    out = "\n".join(lines)

    enemies_state = "; ".join(
        f"{e['name']} HP {e['hp']}/{e['max_hp']} КД {e['ac']}"
        for e in ctx.enemies.enemies) or t('combat.none_left')
    hit_detail = ""
    if hit:
        hit_detail = f", урон оружия {dmg} (применено {applied})"
        if killed:
            hit_detail += "; ВРАГ ПОВЕРЖЕН"
        elif enemy in ctx.enemies.enemies:
            hit_detail += f"; осталось HP {enemy['hp']}/{enemy['max_hp']}"
    rewrite = (
        f"[МЕХАНИКА БОЯ — система всё рассчитала, свои броски НЕ выполняй: "
        f"игрок атаковал {enemy['name']}: d20={d20}"
        f"{'+' + str(player_mod) if player_mod else ''}={total} vs КД {mob_ac} → "
        f"{'ПОПАДАНИЕ' if hit else 'ПРОМАХ'}{hit_detail}. "
        f"Врагов в бою: {enemies_state}"
        + (f". Враги ответили: игрок получил {mdmg_total} урона суммарно, "
           f"HP игрока {char.hp}/{char.max_hp}" if mdmg_total else "")
        + (". ИГРОК ПАЛ БЕЗ СОЗНАНИЯ — опиши падение и напряжение" if char.is_dying else "")
        + ". Опиши эти исходы ярко и кратко] " + act
    )
    ctx.persist()
    return CommandResult(out, stop=False, rewrite_act=rewrite)


def cast_command(act, ctx: GameContext):
    """`!каст <заклинание> [цель]` — тратит ячейку, применяет эффект.

    Уронные заклинания бьют врага, лечащие — восстанавливают HP игроку
    (и выводят из смертельных ранений). Имена заклинаний и врагов могут
    состоять из нескольких слов: ищем самое длинное совпадение имени
    заклинания, остаток считаем целью."""
    m = re.match(r'(?i)!?\s*(?:каст|cast|заклинание)\s+(.+?)\s*$', act)
    if not m:
        return None
    words = m.group(1).strip().split()

    # Самое длинное совпадение имени заклинания с начала фразы
    spell, spell_n = None, 0
    for i in range(len(words), 0, -1):
        s = ctx.spells.find(" ".join(words[:i]))
        if s:
            spell, spell_n = s, i
            break
    if not spell:
        return CommandResult(
            f"{YELLOW}{t('rpg.cast_unknown', name=' '.join(words))}{RESET}")

    rest_words = words[spell_n:]
    target = None
    target_given = bool(rest_words)
    if target_given and ctx.enemies is not None and len(ctx.enemies):
        target = ctx.enemies.find(" ".join(rest_words))
    if target is None and ctx.enemies is not None and len(ctx.enemies):
        # цель не распознана/не указана — берем первого по инициативе
        target = ctx.enemies.attack_order()[0]

    if ctx.spells.slots_left <= 0:
        return CommandResult(
            f"{YELLOW}{t('rpg.no_slots')}{RESET}")
    if not ctx.spells.use_slot():
        return CommandResult(f"{YELLOW}{t('rpg.no_slots')}{RESET}")

    from dndai.game.rpg import heal_dice, is_heal_spell
    char = ctx.character
    lines = [f"{BLUE}{emoji('✨')} {t('rpg.cast_ok', name=spell['name'], left=ctx.spells.slots_left)}{RESET}"]

    if is_heal_spell(spell):
        # ── Лечение: кость заклинания восстанавливает HP игрока ──
        heal_amt, _h = roll_dice(heal_dice(spell))
        before = char.hp
        char.hp = min(char.max_hp, char.hp + max(0, heal_amt))
        healed = char.hp - before
        if char.hp > 0 and healed > 0:
            # Регенерация HP выводит из смертельных ранений и сбрасывает броски
            char.reset_death_saves()
        lines.append(t('rpg.cast_healed', amt=healed, hp=char.hp,
                       max_hp=char.max_hp))
        applied, killed = 0, False
    else:
        applied, killed, heal_amt = 0, False, 0
        if target and spell.get("dmg"):
            dmg, _parts = roll_dice(str(spell["dmg"]))
            applied, killed = ctx.enemies.damage(target["name"], dmg)
            lines.append(t('rpg.cast_damage', target=target['name'], dmg=dmg,
                           left_hp=target['hp'], max_hp=target['max_hp']))
            if killed:
                xp = max(25, 5 * target['max_hp'])
                lvl = ctx.prog.add_xp(xp)
                lines.append(f"{GREEN}{emoji('🏆')} "
                             f"{t('combat.enemy_slain', name=target['name'], xp=xp)}{RESET}")
                lines.extend(_sync_levels(ctx, lvl))
                if ctx.enemies.all_dead():
                    lines.append(f"{YELLOW}{emoji('⚔️')} {t('combat.battle_won')}{RESET}")
        elif target:
            lines.append(t('rpg.cast_no_dmg', target=target['name']))
        elif target_given:
            lines.append(f"{YELLOW}{t('combat.no_such_enemy', name=' '.join(rest_words))}{RESET}")
    ctx.persist()

    tgt_state = ""
    if is_heal_spell(spell):
        tgt_state = (f"Игрок восстановил {healed} HP (теперь {char.hp}/{char.max_hp}). "
                     )
    elif target and applied:
        tgt_state = (f"Цель {target['name']}: получено {applied} урона"
                     + ("ЦЕЛЬ ПОВЕРЖЕНА. " if killed else
                        f", осталось HP {target['hp']}/{target['max_hp']}. "))
    rewrite = (f"[МЕХАНИКА — игрок произнёс заклинание «{spell['name']}»"
               + (f", потрачена ячейка (осталось {ctx.spells.slots_left})" if ctx.spells.slots_max else "")
               + (f". {tgt_state}Опиши эффект ярко]" if tgt_state else ". Опиши эффект ярко] ") + act)
    return CommandResult("\n".join(lines), stop=False, rewrite_act=rewrite)


def slots_command(act, ctx: GameContext):
    """`!ячейки` — остаток ячеек заклинаний."""
    if not re.match(r'(?i)!?\s*(?:ячейки|slots)\s*$', act):
        return None
    sp = ctx.spells
    if not sp.slots_max:
        return CommandResult(f"{YELLOW}{t('rpg.slots_none')}{RESET}")
    return CommandResult(
        f"{BLUE}{t('rpg.slots_left', left=sp.slots_left, max=sp.slots_max)}{RESET}")
