"""
Tree Structure Manager

Reusable component for managing hierarchical structures following the pattern:
module:domain:strategy:step

This provides a generic tree structure that can be used across different
workflows, domains, and strategies.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger("nexus.core.tree_structure")

@dataclass
class TreePath:
    """
    Represents a path in the tree structure.
    Pattern: module:domain:strategy:step
    """
    module: str  # e.g., "workflow"
    domain: str  # e.g., "eligibility"
    strategy: str  # e.g., "TABULA_RASA"
    step: str  # e.g., "gate", "planning", "execution"
    
    def to_key(self) -> str:
        """Convert to key string: module:domain:strategy:step"""
        return f"{self.module}:{self.domain}:{self.strategy}:{self.step}"
    
    @classmethod
    def from_key(cls, key: str) -> 'TreePath':
        """Parse key string into TreePath."""
        parts = key.split(":")
        if len(parts) != 4:
            raise ValueError(f"Invalid tree key format: {key}. Expected module:domain:strategy:step")
        return cls(
            module=parts[0],
            domain=parts[1],
            strategy=parts[2],
            step=parts[3]
        )
    
    def get_parent_path(self) -> Optional['TreePath']:
        """Get parent path (one level up)."""
        # For now, parent is same path with step=None
        # Can be extended for more complex hierarchies
        return None
    
    def get_children_paths(self) -> List['TreePath']:
        """Get possible child paths."""
        # Can be extended to return child steps
        return []

@dataclass
class TreeNode:
    """
    A node in the tree structure.
    Can contain configuration, data, or references to other nodes.
    """
    path: TreePath
    config: Dict[str, Any] = field(default_factory=dict)
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    children: List['TreeNode'] = field(default_factory=list)
    parent: Optional['TreeNode'] = None
    
    def add_child(self, child: 'TreeNode'):
        """Add a child node."""
        child.parent = self
        self.children.append(child)
    
    def find_child(self, step: str) -> Optional['TreeNode']:
        """Find a child node by step name."""
        for child in self.children:
            if child.path.step == step:
                return child
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary."""
        return {
            "path": self.path.to_key(),
            "config": self.config,
            "data": self.data,
            "metadata": self.metadata,
            "children": [child.to_dict() for child in self.children]
        }

class TreeStructureManager:
    """
    Manages tree structures following module:domain:strategy:step pattern.
    Provides reusable functionality for navigation, extraction, and updates.
    """
    
    def __init__(self):
        self._trees: Dict[str, TreeNode] = {}  # Cache of loaded trees
    
    def build_path(
        self,
        module: str,
        domain: str,
        strategy: str,
        step: str
    ) -> TreePath:
        """Build a tree path from components."""
        return TreePath(
            module=module,
            domain=domain,
            strategy=strategy,
            step=step
        )
    
    def parse_key(self, key: str) -> TreePath:
        """Parse a key string into TreePath."""
        return TreePath.from_key(key)
    
    def create_node(
        self,
        path: TreePath,
        config: Dict[str, Any] = None,
        data: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ) -> TreeNode:
        """Create a new tree node."""
        return TreeNode(
            path=path,
            config=config or {},
            data=data or {},
            metadata=metadata or {}
        )
    
    def build_tree(
        self,
        root_path: TreePath,
        structure: Dict[str, Any]
    ) -> TreeNode:
        """
        Build a tree from a nested structure.
        
        Example structure:
        {
            "gate": {
                "config": {...},
                "children": {
                    "1_patient_info": {...},
                    "2_use_case": {...}
                }
            }
        }
        """
        root = self.create_node(root_path, config=structure.get("config", {}))
        
        # Recursively build children
        for child_key, child_data in structure.get("children", {}).items():
            child_path = TreePath(
                module=root_path.module,
                domain=root_path.domain,
                strategy=root_path.strategy,
                step=child_key
            )
            child_node = self.build_tree(child_path, child_data)
            root.add_child(child_node)
        
        return root
    
    def extract_from_tree(
        self,
        tree: TreeNode,
        extraction_path: List[str]
    ) -> Optional[Any]:
        """
        Extract data from tree following a path.
        
        Args:
            tree: Root node
            extraction_path: List of step names to follow
        
        Returns:
            Extracted node or None if path doesn't exist
        """
        current = tree
        
        for step in extraction_path:
            current = current.find_child(step)
            if not current:
                return None
        
        return current
    
    def update_tree_node(
        self,
        tree: TreeNode,
        update_path: List[str],
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update a node in the tree.
        
        Args:
            tree: Root node
            update_path: List of step names to follow
            updates: Dictionary of updates to apply
        
        Returns:
            True if update successful, False if path doesn't exist
        """
        node = self.extract_from_tree(tree, update_path)
        if not node:
            return False
        
        # Update config, data, or metadata based on updates
        if "config" in updates:
            node.config.update(updates["config"])
        if "data" in updates:
            node.data.update(updates["data"])
        if "metadata" in updates:
            node.metadata.update(updates["metadata"])
        
        return True
    
    def find_nodes_by_pattern(
        self,
        tree: TreeNode,
        pattern: Dict[str, Any]
    ) -> List[TreeNode]:
        """
        Find nodes matching a pattern.
        
        Args:
            tree: Root node
            pattern: Dictionary with keys like "module", "domain", "step" to match
        
        Returns:
            List of matching nodes
        """
        matches = []
        
        def _match_node(node: TreeNode) -> bool:
            """Check if node matches pattern."""
            if "module" in pattern and node.path.module != pattern["module"]:
                return False
            if "domain" in pattern and node.path.domain != pattern["domain"]:
                return False
            if "strategy" in pattern and node.path.strategy != pattern["strategy"]:
                return False
            if "step" in pattern and node.path.step != pattern["step"]:
                return False
            return True
        
        def _traverse(node: TreeNode):
            """Traverse tree and collect matches."""
            if _match_node(node):
                matches.append(node)
            for child in node.children:
                _traverse(child)
        
        _traverse(tree)
        return matches
    
    def get_all_paths(
        self,
        tree: TreeNode
    ) -> List[TreePath]:
        """Get all paths in the tree."""
        paths = []
        
        def _traverse(node: TreeNode):
            paths.append(node.path)
            for child in node.children:
                _traverse(child)
        
        _traverse(tree)
        return paths
    
    def serialize_tree(self, tree: TreeNode) -> Dict[str, Any]:
        """Serialize tree to dictionary."""
        return tree.to_dict()
    
    def deserialize_tree(
        self,
        root_path: TreePath,
        data: Dict[str, Any]
    ) -> TreeNode:
        """Deserialize dictionary to tree."""
        return self.build_tree(root_path, data)

# Singleton instance
tree_structure_manager = TreeStructureManager()







