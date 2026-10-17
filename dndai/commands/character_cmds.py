"""Команды персонажа (D&D-механика) и инвентаря."""
import re

from dndai.commands.context import GameContext
from dndai.commands.result import CommandResult
from dndai.core.colors import GREEN, RED, RESET, YELLOW
from dndai.core.i18n import t
from dndai.game import economy
from dndai.game.character import parse_character_command, show_character


def character_create(act, ctx: GameContext):
    if not (act.lower().startswith('!персонаж') or act.lower().startswith('!character')):
        return None
    from dndai.game import commands as cmd_names
    parsed = parse_character_command(act)
    if parsed and parsed[0] == "create":
        character = parsed[1]
        if not character.name:
            character.name = cmd_names.PLAYER_NAME
        if not character.char_class:
            character.char_class = "Искатель"
        # Заменяем активного персонажа в партии (а не только локальную ссылку),
        # чтобы изменение сохранилось в party.to_dict()
        if ctx.party is not None:
            ctx.party.replace_active(character)
            ctx.character = ctx.party.active_character
        else:
            ctx.character = character
        ctx.persist()
        return CommandResult(
            f"{GREEN}{t('char.created', name=character.name, cls=character.char_class)}{RESET}")
    if act.lower().startswith('!персонаж') or act.lower().startswith('!character'):
        return CommandResult(
            f"{YELLOW}{t('char.create_format')}{RESET}")
    return None


def character_status(act, ctx: GameContext):
    if act.lower() in ('!статус', '!status', '!перс'):
        show_character(ctx.character)
        return CommandResult.silent()
    return None


def character_modify(act, ctx: GameContext):
    parsed = parse_character_command(act)
    if not parsed:
        return None
    action, data = parsed
    c = ctx.character
    if action == "damage":
        c.hp = max(0, c.hp - data)
        ctx.persist()
        return CommandResult(
            f"{RED}{t('char.damage', dmg=data, hp=c.hp, max_hp=c.max_hp)}{RESET}")
    if action == "heal":
        c.hp = min(c.max_hp, c.hp + data)
        ctx.persist()
        return CommandResult(
            f"{GREEN}{t('char.heal', amt=data, hp=c.hp, max_hp=c.max_hp)}{RESET}")
    if action == "sethp":
        c.hp = min(c.max_hp, max(0, data))
        ctx.persist()
        return CommandResult(f"{GREEN}{t('char.sethp', hp=c.hp, max_hp=c.max_hp)}{RESET}")
    if action == "inv_add":
        c.inventory.extend(data)
        ctx.persist()
        return CommandResult(f"{GREEN}{t('char.inv_add', items=', '.join(data))}{RESET}")
    if action == "inv_del":
        c.inventory = [i for i in c.inventory if i not in data]
        ctx.persist()
        return CommandResult(f"{YELLOW}{t('char.inv_del', items=', '.join(data))}{RESET}")
    return None


def inventory_show(act, ctx: GameContext):
    if re.match(r'(?i)!?\s*инвентарь\s*$', act) or re.match(r'(?i)!?\s*inv\s*$', act):
        inv = ctx.character.inventory
        if inv:
            return CommandResult(
                f"{GREEN}{t('char.inv_show')}{RESET} {', '.join(inv)}")
        return CommandResult(f"{YELLOW}{t('char.inv_empty')}{RESET}")
    return None


def gold_command(act, ctx: GameContext):
    """Кошелёк: `!золото` — показать, `!золото +50` / `!золото -20`."""
    from dndai.core.colors import ORANGE
    m = re.match(r'(?i)!?\s*(?:золото|gold|монеты)\s*([+-]?\s*\d+)?\s*$', act)
    if not m:
        return None
    c = ctx.character
    if m.group(1):
        try:
            delta = int(m.group(1).replace(' ', ''))
        except ValueError:
            return None
        c.gold = max(0, c.gold + delta)
        ctx.persist()
        sign = f"+{delta}" if delta >= 0 else str(delta)
        col = GREEN if delta >= 0 else RED
        return CommandResult(
            f"{col}{t('char.gold_changed', delta=sign, gold=c.gold)}{RESET}")
    return CommandResult(
        f"{ORANGE}{t('char.gold_show', gold=c.gold)}{RESET}")


# ── Прайс торговца переехал в dndai.game.economy ──
# Цены зависят от локации и условий мира; SHOP_PRICES оставлен
# как нейтральный прайс для обратной совместимости.
SHOP_PRICES = economy.SHOP_PRICES


def shop_command(act, ctx: GameContext):
    """`!купить <предмет> [цена]` / `!продать <предмет> [цена]`.

    Цена берётся из экономики локации; своё число — только подсказка,
    в сделке не участвует (игроку показываем, что она не применена).
    """
    m_buy = re.match(r"(?i)!?\s*(?:купить|куплю|buy)\s+(.+?)\s*$", act)
    m_sell = re.match(r"(?i)!?\s*(?:продать|продаю|sell)\s+(.+?)\s*$", act)
    if not m_buy and not m_sell:
        return None
    from dndai.core.colors import ORANGE

    def parse_body(body):
        parts = body.rsplit(None, 1)
        if len(parts) == 2 and parts[1].isdigit():
            return parts[0], int(parts[1])
        return body, None

    c = ctx.character

    def offer_note(offer, price):
        """Своя цена в команде не применяется — нота игроку."""
        if offer is None:
            return ""
        return f"\n{YELLOW}{t('shop.offer_ignored', offer=offer, price=price)}{RESET}"

    if m_buy:
        item, offer = parse_body(m_buy.group(1).strip())
        price = economy.buy_price(ctx.world, item)
        if c.gold < price:
            return CommandResult(
                f"{RED}{t('shop.cant_afford', item=item, price=price, gold=c.gold)}{RESET}"
            )
        c.gold -= price
        c.inventory.append(item.title() if item.islower() else item)
        ctx.persist()
        return CommandResult(
            f"{GREEN}{t('shop.bought', item=item, price=price, gold=c.gold)}{RESET}"
            + offer_note(offer, price)
        )

    # продажа
    assert m_sell is not None  # m_buy уже обработан выше
    item, offer = parse_body(m_sell.group(1).strip())
    found = next((i for i in c.inventory if item.lower() in i.lower()), None)
    if not found:
        return CommandResult(f"{YELLOW}{t('shop.not_owned', item=item)}{RESET}")
    price = economy.sell_price(ctx.world, found)
    c.inventory.remove(found)
    c.gold += price
    ctx.persist()
    return CommandResult(
        f"{ORANGE}{t('shop.sold', item=found, price=price, gold=c.gold)}{RESET}"
        + offer_note(offer, price)
    )


def equip_command(act, ctx: GameContext):
    """`!надеть <предмет>` / `!снять [предмет]` — экипировка.

    Оружие задаёт кость урона, броня и щит добавляют КД."""
    from dndai.game.character import ARMORS, WEAPONS, _lookup
    m_on = re.match(r'(?i)!?\s*(?:надеть|экипировать|equip|взять оружие)\s+(.+?)\s*$', act)
    m_off = re.match(r'(?i)!?\s*(?:снять|unequip|убрать)(?:\s+(.+?))?\s*$', act)
    c = ctx.character

    if m_off and not m_on:
        removed = c.unequip(m_off.group(1))
        if not removed:
            return CommandResult(f"{YELLOW}{t('char.equip_nothing')}{RESET}")
        ctx.persist()
        return CommandResult(f"{YELLOW}{t('char.unequipped', items=', '.join(removed))}{RESET}")

    if not m_on:
        # просто `!экипировка` — показать текущее
        if re.match(r'(?i)!?\s*(?:экипировка|equipment)\s*$', act):
            eq = {k: v for k, v in c.equipped.items() if v}
            if not eq:
                return CommandResult(f"{YELLOW}{t('char.equip_empty')}{RESET}")
            parts = []
            for slot, item in eq.items():
                extra = ""
                if slot == "weapon":
                    extra = f" ({c.weapon_damage_dice()})"
                elif slot in ("shield", "armor"):
                    extra = f" (+{_lookup(ARMORS, item) or 0} КД)"
                parts.append(f"{item}{extra}")
            return CommandResult(f"{GREEN}{t('char.equipment')}{RESET} {', '.join(parts)}")
        return None

    item = m_on.group(1).strip()
    in_inv = any(item.lower() in inv.lower() for inv in c.inventory)
    if not in_inv:
        return CommandResult(
            f"{YELLOW}{t('char.equip_not_in_inventory', item=item)}{RESET}")
    slot, old = c.equip(item)
    bonus = ""
    if slot == "weapon":
        dice = _lookup(WEAPONS, item) or "1d6"
        bonus = f" (урон {dice})"
    elif slot in ("shield", "armor"):
        bonus = f" (КД {c.ac}→{c.ac + c.equip_ac_bonus()})"
    old_str = f", снято: {old}" if old else ""
    ctx.persist()
    return CommandResult(
        f"{GREEN}{t('char.equipped', item=item, slot=slot)}{bonus}{old_str}{RESET}")
