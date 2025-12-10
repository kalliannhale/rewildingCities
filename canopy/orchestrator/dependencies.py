# === DAG Building ===
# canopy/orchestrator/dependencies.py

@dataclass
class ExecutionPlan:
    steps_in_order: list[str]
    dependency_graph: dict[str, set[str]]

class DependencyResolver:
    """
    Resolves step dependencies and builds execution order.
    
    Analyzes $steps.{id}.{output} references to determine which steps
    depend on which, then produces a topologically sorted execution plan.
    """
    
    # Pattern to extract step dependencies from references
    STEPS_PATTERN = re.compile(r'\$steps\.([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)')
    
    def __init__(self, experiment: Experiment):
        self.experiment = experiment
        self.steps_by_id = {step.id: step for step in experiment.steps}
    
    def _extract_step_references(self, value: Any) -> set[str]:
        """
        Recursively extract all step IDs referenced in a value.
        
        Handles nested dicts, lists, and strings.
        """
        refs = set()
        
        if isinstance(value, str):
            match = self.STEPS_PATTERN.match(value)
            if match:
                refs.add(match.group(1))
        
        elif isinstance(value, list):
            for item in value:
                refs.update(self._extract_step_references(item))
        
        elif isinstance(value, dict):
            for v in value.values():
                refs.update(self._extract_step_references(v))
        
        return refs
    
    def build_dependency_graph(self) -> dict[str, set[str]]:
        """
        Build a graph of step dependencies.
        
        Returns:
            Dict mapping step_id -> set of step_ids it depends on
        
        Raises:
            ValueError: If a step references an unknown step
        """
        graph: dict[str, set[str]] = {}
        
        for step in self.experiment.steps:
            dependencies = set()
            
            # Check inputs for $steps references
            for input_name, ref in step.inputs.items():
                step_refs = self._extract_step_references(ref)
                dependencies.update(step_refs)
            
            # Check params for $steps references (shouldn't happen, but be thorough)
            for param_name, value in step.params.items():
                step_refs = self._extract_step_references(value)
                dependencies.update(step_refs)
            
            # Validate all dependencies exist
            for dep_id in dependencies:
                if dep_id not in self.steps_by_id:
                    raise ValueError(
                        f"Step '{step.id}' references unknown step '{dep_id}'. "
                        f"Available steps: {', '.join(sorted(self.steps_by_id.keys()))}"
                    )
            
            graph[step.id] = dependencies
        
        return graph
    
    def _detect_cycle(self, graph: dict[str, set[str]]) -> list[str] | None:
        """
        Detect if graph contains a cycle using DFS.
        
        Returns:
            List of step IDs forming the cycle, or None if no cycle
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node: WHITE for node in graph}
        parent = {node: None for node in graph}
        
        def dfs(node: str, path: list[str]) -> list[str] | None:
            color[node] = GRAY
            
            for neighbor in graph.get(node, set()):
                if color[neighbor] == GRAY:
                    # Found cycle — reconstruct it
                    cycle_start = neighbor
                    cycle = [cycle_start]
                    current = node
                    while current != cycle_start:
                        cycle.append(current)
                        current = parent[current]
                    cycle.append(cycle_start)
                    return list(reversed(cycle))
                
                if color[neighbor] == WHITE:
                    parent[neighbor] = node
                    result = dfs(neighbor, path + [neighbor])
                    if result:
                        return result
            
            color[node] = BLACK
            return None
        
        for node in graph:
            if color[node] == WHITE:
                result = dfs(node, [node])
                if result:
                    return result
        
        return None
    
    def topological_sort(self, graph: dict[str, set[str]]) -> list[str]:
        """
        Topological sort of the dependency graph using Kahn's algorithm.
        
        Returns:
            List of step_ids in execution order
        
        Raises:
            ValueError: If cycle detected (with helpful message showing the cycle)
        """
        # Check for cycles first (better error message)
        cycle = self._detect_cycle(graph)
        if cycle:
            cycle_str = " -> ".join(cycle)
            raise ValueError(
                f"Circular dependency detected in experiment steps:\n"
                f"  {cycle_str}\n"
                f"Each step in this cycle depends on another step in the cycle. "
                f"Restructure your experiment to break the loop."
            )
        
        # Kahn's algorithm
        in_degree = {node: 0 for node in graph}
        
        for node, deps in graph.items():
            in_degree[node] = len(deps)
        
        # Start with nodes that have no dependencies
        queue = sorted([node for node, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            # Reduce in-degree for nodes that depend on this one
            for other, deps in graph.items():
                if node in deps:
                    in_degree[other] -= 1
                    if in_degree[other] == 0:
                        # Insert sorted to maintain deterministic order
                        queue.append(other)
                        queue.sort()
        
        # Sanity check (should never fail if cycle detection worked)
        if len(result) != len(graph):
            remaining = set(graph.keys()) - set(result)
            raise ValueError(
                f"Internal error: topological sort incomplete. "
                f"Remaining steps: {remaining}"
            )
        
        return result
    
    def create_execution_plan(self) -> ExecutionPlan:
        """
        Create an ordered execution plan for the experiment.
        
        Returns:
            ExecutionPlan with steps_in_order and dependency_graph
        
        Raises:
            ValueError: If dependencies are invalid or cyclic
        """
        graph = self.build_dependency_graph()
        order = self.topological_sort(graph)
        
        return ExecutionPlan(
            steps_in_order=order,
            dependency_graph=graph
        )
    
    def visualize(self) -> str:
        """
        Generate ASCII visualization of the execution plan.
        
        Returns:
            Human-readable string showing execution order and dependencies
        """
        plan = self.create_execution_plan()
        
        lines = [
            f"Experiment: {self.experiment.name}",
            f"ID: {self.experiment.id}",
            f"Steps: {len(self.experiment.steps)}",
            "",
            "Execution Order:",
            "─" * 50
        ]
        
        for i, step_id in enumerate(plan.steps_in_order, 1):
            step = self.steps_by_id[step_id]
            deps = plan.dependency_graph.get(step_id, set())
            
            # Format dependencies
            if deps:
                dep_str = f"← depends on: {', '.join(sorted(deps))}"
            else:
                dep_str = "← (no dependencies, can run first)"
            
            lines.append(f"")
            lines.append(f"  {i}. {step_id}")
            lines.append(f"     primitive: {step.primitive}")
            lines.append(f"     {dep_str}")
            
            # Show inputs
            if step.inputs:
                lines.append(f"     inputs:")
                for name, ref in step.inputs.items():
                    lines.append(f"       {name}: {ref}")
            
            # Show outputs
            if step.outputs:
                outputs_str = ", ".join(f"{k}: {v}" for k, v in step.outputs.items())
                lines.append(f"     outputs: {outputs_str}")
        
        lines.append("")
        lines.append("─" * 50)
        
        return "\n".join(lines)