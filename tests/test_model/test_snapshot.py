"""Tests for snapshot/restore state management."""

from omega.config.dice import DiceSpec
from omega.model.constants import CLASSEID_WARRIOR, LAYER_CHEST, LAYER_HAND1
from omega.model.items import Armor, Weapon
from omega.model.mobile import Mobile
from omega.model.snapshot import MobileSnapshot, restore, snapshot


class TestSnapshot:
    def test_captures_vitals(self):
        m = Mobile()
        m.hp = 100
        m.max_hp = 100
        m.mana = 50
        m.stamina = 80
        snap = snapshot(m)
        assert snap.hp == 100
        assert snap.mana == 50
        assert snap.stamina == 80

    def test_captures_stat_mods(self):
        m = Mobile()
        m.str_mod = 50
        m.int_mod = -20
        snap = snapshot(m)
        assert snap.str_mod == 50
        assert snap.int_mod == -20

    def test_captures_properties(self):
        m = Mobile()
        m.set_property(CLASSEID_WARRIOR, 5)
        m.set_property("Type", "Human")
        snap = snapshot(m)
        assert snap.properties[CLASSEID_WARRIOR] == 5
        assert snap.properties["Type"] == "Human"

    def test_captures_frozen(self):
        m = Mobile()
        m.frozen = True
        snap = snapshot(m)
        assert snap.frozen is True

    def test_captures_frozen_default(self):
        m = Mobile()
        snap = snapshot(m)
        assert snap.frozen is False

    def test_captures_equipment_hp(self):
        m = Mobile()
        w = Weapon(name="Sword", hp=50, max_hp=50)
        a = Armor(name="Plate", hp=100, max_hp=100)
        m.equip(LAYER_HAND1, w)
        m.equip(LAYER_CHEST, a)
        snap = snapshot(m)
        assert snap.equipment_hp[LAYER_HAND1] == 50
        assert snap.equipment_hp[LAYER_CHEST] == 100

    def test_snapshot_is_frozen(self):
        m = Mobile()
        m.hp = 100
        snap = snapshot(m)
        assert isinstance(snap, MobileSnapshot)
        # Frozen dataclass — can't modify
        try:
            snap.hp = 50  # type: ignore[misc]
            assert False, "Should have raised"
        except AttributeError:
            pass


class TestRestore:
    def test_restores_vitals(self):
        m = Mobile()
        m.hp = 100
        m.max_hp = 100
        m.mana = 50
        snap = snapshot(m)

        # Simulate combat damage
        m.hp = 30
        m.mana = 10

        restore(m, snap)
        assert m.hp == 100
        assert m.mana == 50

    def test_restores_stat_mods(self):
        m = Mobile()
        m.str_mod = 0
        snap = snapshot(m)

        m.str_mod = 100  # temp buff during combat
        restore(m, snap)
        assert m.str_mod == 0

    def test_restores_dead_flag(self):
        m = Mobile()
        m.dead = False
        snap = snapshot(m)

        m.dead = True
        restore(m, snap)
        assert not m.dead

    def test_restores_frozen(self):
        m = Mobile()
        m.frozen = True
        snap = snapshot(m)

        m.frozen = False
        restore(m, snap)
        assert m.frozen is True

    def test_restores_frozen_to_false(self):
        m = Mobile()
        m.frozen = False
        snap = snapshot(m)

        m.frozen = True
        restore(m, snap)
        assert m.frozen is False

    def test_restores_properties(self):
        m = Mobile()
        m.set_property("poison", 0)
        snap = snapshot(m)

        m.set_property("poison", 3)
        m.set_property("new_prop", "added during combat")

        restore(m, snap)
        assert m.get_property("poison") == 0
        assert m.get_property("new_prop") is None

    def test_restores_equipment_hp(self):
        m = Mobile()
        w = Weapon(name="Sword", hp=50, max_hp=50)
        m.equip(LAYER_HAND1, w)
        snap = snapshot(m)

        w.hp = 49  # degraded during combat
        restore(m, snap)
        assert w.hp == 50

    def test_snapshot_properties_independent(self):
        """Modifying mobile after snapshot doesn't affect snapshot."""
        m = Mobile()
        m.set_property("data", [1, 2, 3])
        snap = snapshot(m)

        m.get_property("data").append(4)
        assert snap.properties["data"] == [1, 2, 3]

    def test_restore_properties_independent(self):
        """Modifying mobile after restore doesn't affect snapshot."""
        m = Mobile()
        m.set_property("data", [1, 2, 3])
        snap = snapshot(m)

        restore(m, snap)
        m.get_property("data").append(4)
        assert snap.properties["data"] == [1, 2, 3]
