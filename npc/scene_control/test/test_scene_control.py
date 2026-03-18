#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scene_control 模块测试：SceneData、SceneRegistry、SceneStatus、SceneManager
用于验证场景数据加载、按索引/路径切换、以及 location 与 NPC 的对应关系。
"""

import os
import sys
import json
import pytest

# 保证能导入 npc.scene_control
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from npc.scene_control.scene_data import SceneData, SceneRegistry
from npc.scene_control.scene_status import SceneStatus
from npc.scene_control.scene_manager import SceneManager


# demo.json 路径（与 scene_status 默认一致）
DEMO_JSON = os.path.join(os.path.dirname(__file__), "..", "..", "data", "demo.json")


def _ensure_demo_exists():
    if not os.path.isfile(DEMO_JSON):
        pytest.skip(f"demo.json 不存在: {DEMO_JSON}")


class TestSceneData:
    """SceneData 数据类"""

    def test_from_dict_full(self):
        raw = {
            "name": "01 00 00",
            "location": "The Bureau",
            "time": "Morning",
            "max_turns": 8,
            "environment": "Fluorescent lights...",
            "current_topic": "Receive a confidential document",
            "key_npcs": ["Player", "Haruko"],
            "interactive_npc": [{"name": "Haruko", "goal": "Assign the player..."}],
            "npc_relationships": [{"character1": "Haruko", "character2": "Player"}],
            "worldstate_tasks": [{"state_key": "WS_D1", "expected_text": "Player accepted."}],
            "trigger_conditions": {"additional_conditions": "Player has just arrived"},
            "scene_end_state_reference": {"goal_achievement": "Player receives the document"},
        }
        scene = SceneData.from_dict(raw)
        assert scene.name == "01 00 00"
        assert scene.location == "The Bureau"
        assert scene.time == "Morning"
        assert scene.max_turns == 8
        assert "Fluorescent" in scene.environment
        assert scene.current_topic == "Receive a confidential document"
        assert scene.key_npcs == ["Player", "Haruko"]
        assert len(scene.interactive_npc) == 1
        assert scene.interactive_npc[0]["name"] == "Haruko"
        assert len(scene.npc_relationships) == 1
        assert len(scene.worldstate_tasks) == 1
        assert scene.raw_data is raw

    def test_from_dict_minimal(self):
        raw = {}
        scene = SceneData.from_dict(raw)
        assert scene.name == "Unknown"
        assert scene.location == "Unknown"
        assert scene.time == "Morning"
        assert scene.max_turns == 10
        assert scene.key_npcs == []
        assert scene.raw_data == raw


class TestSceneRegistry:
    """SceneRegistry 单例与当前场景"""

    def setup_method(self):
        SceneRegistry.clear()

    def teardown_method(self):
        SceneRegistry.clear()

    def test_register_and_get_scene(self):
        raw = {"name": "Test", "location": "Test Location"}
        scene = SceneData.from_dict(raw)
        SceneRegistry.register_scene(0, scene)
        assert SceneRegistry.get_scene(0) is scene
        assert SceneRegistry.get_scene(1) is None

    def test_set_current_scene_by_index(self):
        raw = {"name": "A", "location": "LocA"}
        scene_a = SceneData.from_dict(raw)
        SceneRegistry.register_scene(0, scene_a)
        SceneRegistry.set_current_scene(0)
        assert SceneRegistry.get_current_scene() is scene_a
        assert SceneRegistry.get_current_scene_index() == 0

    def test_set_current_scene_override(self):
        raw = {"name": "Override", "location": "Override Loc"}
        override = SceneData.from_dict(raw)
        SceneRegistry.register_scene(0, SceneData.from_dict({"name": "B", "location": "B"}))
        SceneRegistry.set_current_scene(0)
        SceneRegistry.set_current_scene_override(override)
        assert SceneRegistry.get_current_scene() is override
        assert SceneRegistry.get_current_scene_index() is None

    def test_override_cleared_when_set_index(self):
        override = SceneData.from_dict({"name": "O", "location": "O"})
        scene = SceneData.from_dict({"name": "I", "location": "I"})
        SceneRegistry.register_scene(0, scene)
        SceneRegistry.set_current_scene_override(override)
        SceneRegistry.set_current_scene(0)
        assert SceneRegistry.get_current_scene() is scene
        # 再次用 override 覆盖
        SceneRegistry.set_current_scene_override(override)
        assert SceneRegistry.get_current_scene() is override


class TestSceneStatus:
    """SceneStatus 加载与注册"""

    def setup_method(self):
        SceneRegistry.clear()
        self.status = SceneStatus()

    def teardown_method(self):
        SceneRegistry.clear()

    def test_load_all_scenes_from_demo(self):
        _ensure_demo_exists()
        ok = self.status.load_all_scenes(DEMO_JSON)
        assert ok is True
        assert len(self.status.all_scenes) > 0
        # 检查 Registry 已按索引注册
        first = SceneRegistry.get_scene(0)
        assert first is not None
        assert first.name == "01 00 00"
        assert first.location == "The Bureau"

    def test_get_scene_by_index_after_load(self):
        _ensure_demo_exists()
        self.status.load_all_scenes(DEMO_JSON)
        d = self.status.get_scene_by_index(0)
        assert d is not None
        assert d.get("name") == "01 00 00"
        assert d.get("location") == "The Bureau"
        assert "Haruko" in d.get("key_npcs", [])
        d8 = self.status.get_scene_by_index(8)
        assert d8 is not None
        assert d8.get("location") == "Ancient Medicine Shop"
        assert "Huang Qiye" in d8.get("key_npcs", [])

    def test_load_scene_by_index_updates_registry_current(self):
        _ensure_demo_exists()
        self.status.load_all_scenes(DEMO_JSON)
        ok = self.status.load_scene_by_index(8)
        assert ok is True
        current = SceneRegistry.get_current_scene()
        assert current is not None
        assert current.location == "Ancient Medicine Shop"
        assert current.name == "02 01 01-3"
        # 当前场景的 NPC 应为 Huang Qiye
        npc_names = [n.get("name") if isinstance(n, dict) else n for n in current.interactive_npc]
        assert "Huang Qiye" in npc_names
        assert "Haruko" not in npc_names

    def test_load_scene_by_index_0_is_bureau_haruko(self):
        _ensure_demo_exists()
        self.status.load_all_scenes(DEMO_JSON)
        ok = self.status.load_scene_by_index(0)
        assert ok is True
        current = SceneRegistry.get_current_scene()
        assert current.location == "The Bureau"
        assert "Haruko" in current.key_npcs
        npc_names = [n.get("name") if isinstance(n, dict) else n for n in current.interactive_npc]
        assert "Haruko" in npc_names


class TestSceneManager:
    """SceneManager 与 location/NPC 一致性"""

    def setup_method(self):
        SceneRegistry.clear()
        self.manager = SceneManager()

    def teardown_method(self):
        SceneRegistry.clear()

    def test_load_demo_by_path_then_index(self):
        _ensure_demo_exists()
        ok = self.manager.scene_status.load_all_scenes(DEMO_JSON)
        assert ok is True
        ok = self.manager.load_scene_by_index(8)
        assert ok is True
        current = self.manager.get_current_scene_data()
        assert current is not None
        assert current.location == "Ancient Medicine Shop"
        assert "Huang Qiye" in current.key_npcs

    def test_get_scene_data_by_index_does_not_switch(self):
        _ensure_demo_exists()
        self.manager.scene_status.load_all_scenes(DEMO_JSON)
        self.manager.load_scene_by_index(0)
        # 取 index 8 的数据但不切换当前场景
        scene8 = self.manager.get_scene_data_by_index(8)
        assert scene8 is not None
        assert scene8.location == "Ancient Medicine Shop"
        assert self.manager.get_current_scene_data().location == "The Bureau"

    def test_load_scene_by_path_single_scene_sets_override(self):
        _ensure_demo_exists()
        # 构造只含一个场景的临时列表，写入临时文件
        with open(DEMO_JSON, "r", encoding="utf-8") as f:
            all_scenes = json.load(f)
        single = [all_scenes[8]]  # Ancient Medicine Shop
        tmp_path = os.path.join(os.path.dirname(__file__), "temp_single_scene.json")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(single, f, ensure_ascii=False, indent=2)
            ok = self.manager.load_scene_by_path(tmp_path, auto_select=False)
            assert ok is True
            current = self.manager.get_current_scene_data()
            assert current is not None
            assert current.location == "Ancient Medicine Shop"
            assert "Huang Qiye" in current.key_npcs
        finally:
            if os.path.isfile(tmp_path):
                os.remove(tmp_path)


class TestSceneDataConsistency:
    """验证 demo.json 中索引与 location/NPC 对应关系（你提到的数据问题）"""

    def setup_method(self):
        SceneRegistry.clear()

    def teardown_method(self):
        SceneRegistry.clear()

    def test_demo_index_0_bureau_haruko(self):
        _ensure_demo_exists()
        status = SceneStatus()
        status.load_all_scenes(DEMO_JSON)
        status.load_scene_by_index(0)
        current = SceneRegistry.get_current_scene()
        assert current is not None, "当前场景不应为空"
        assert current.location == "The Bureau", f"index 0 应为 The Bureau，实际: {current.location}"
        assert "Haruko" in current.key_npcs, f"index 0 应包含 Haruko，key_npcs: {current.key_npcs}"
        interactive_names = [
            n.get("name") if isinstance(n, dict) else n for n in current.interactive_npc
        ]
        assert "Haruko" in interactive_names, f"interactive_npc 应包含 Haruko: {interactive_names}"

    def test_demo_index_8_medicine_shop_huang_qiye(self):
        _ensure_demo_exists()
        status = SceneStatus()
        status.load_all_scenes(DEMO_JSON)
        status.load_scene_by_index(8)
        current = SceneRegistry.get_current_scene()
        assert current is not None, "当前场景不应为空"
        assert current.location == "Ancient Medicine Shop", (
            f"index 8 应为 Ancient Medicine Shop，实际: {current.location}"
        )
        assert "Huang Qiye" in current.key_npcs, (
            f"index 8 应包含 Huang Qiye，key_npcs: {current.key_npcs}"
        )
        interactive_names = [
            n.get("name") if isinstance(n, dict) else n for n in current.interactive_npc
        ]
        assert "Huang Qiye" in interactive_names, (
            f"interactive_npc 应包含 Huang Qiye: {interactive_names}"
        )
        assert "Haruko" not in interactive_names, "index 8 不应包含 Haruko"

    def test_demo_index_2_teahouse_chou_hu(self):
        _ensure_demo_exists()
        status = SceneStatus()
        status.load_all_scenes(DEMO_JSON)
        status.load_scene_by_index(2)
        current = SceneRegistry.get_current_scene()
        assert current is not None
        assert current.location == "Teahouse"
        assert "Chou Hu" in current.key_npcs
        interactive_names = [
            n.get("name") if isinstance(n, dict) else n for n in current.interactive_npc
        ]
        assert "Chou Hu" in interactive_names


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
