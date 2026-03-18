import os
import sys
from typing import Dict, List, Optional, Any
from langchain.tools import BaseTool
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from npc.multi_npc.managers.emotion_manager import EmotionManager

class EmotionManagerTool(BaseTool):
    """Tool for managing NPC emotions"""
    name: str = "emotion_manager"
    description: str = "Analyzes and updates NPC emotional state based on player input"
    
    def __init__(self, emotion_manager: Optional[EmotionManager] = None):
        super().__init__()
        self.emotion_manager = emotion_manager
        
    def _run(self, source_npc: str, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Run the tool to update emotion"""
        self.emotion_manager.update_emotion(source_npc, game_state)
        return {
            "status": "success",
            "message": f"Updated emotion for {source_npc}"
        }
        
    async def _arun(self, source_npc: str, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Run the tool asynchronously"""
        return self._run(source_npc, game_state)

class ToolManager:
    """
    Manager class for handling various tools used by NPCs.
    Manages tool execution order: emotion_tool -> intention_tool
    """
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        # 定义工具调用顺序：先 emotion 后 intention
        self.tool_execution_order = ["emotion_manager", "intention_manager"]
        
    def register_tool(self, tool: BaseTool):
        """
        Register a new tool.
        
        Args:
            tool: Tool instance to register
        """
        self.tools[tool.name] = tool
        
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        Get a specific tool by name.
        
        Args:
            tool_name: Name of the tool to retrieve
            
        Returns:
            Tool instance if found, None otherwise
        """
        return self.tools.get(tool_name)
        
    def get_all_tools(self) -> List[BaseTool]:
        """
        Get all registered tools.
        
        Returns:
            List of all registered tool instances
        """
        return list(self.tools.values())
    
    def execute_tools_in_order(self, npc_name: str, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute tools in the specified order for player mode.
        Order: relationship_manager -> intention_manager
        
        Args:
            npc_name: Name of the NPC
            game_state: Current game state
            
        Returns:
            Dict containing results from both tools
        """
        results = {
            "npc_name": npc_name,
            "relationship_result": None,
            "intention_result": None,
            "execution_order": self.tool_execution_order,
            "status": "success"
        }
        
        try:
            # 1. 先执行关系工具
            relationship_tool = self.get_tool("relationship_manager")
            if relationship_tool:
                relationship_result = relationship_tool._run(npc_name, game_state)
                results["relationship_result"] = relationship_result
                
                # 关系更新由 relationship_tool 写回 state["npc_state"]
            
            # 2. 再执行意图工具
            intention_tool = self.get_tool("intention_manager")
            if intention_tool:
                intention_result = intention_tool._run(npc_name, game_state)
                results["intention_result"] = intention_result
                
        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)
            print(f"[ToolManager] Error executing tools for {npc_name}: {e}")
            
        return results
    
    def get_ordered_tools(self) -> List[BaseTool]:
        """
        Get tools in execution order.
        
        Returns:
            List of tools in execution order
        """
        ordered_tools = []
        for tool_name in self.tool_execution_order:
            tool = self.get_tool(tool_name)
            if tool:
                ordered_tools.append(tool)
        return ordered_tools 