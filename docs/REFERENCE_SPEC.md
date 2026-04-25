# Technical Reference for Logos Parser (Extracted from Blueprint)

## 1. Node Data Structure (LogseqNode)
The core Pydantic V2 model must strictly follow this structure to ensure AOT compatibility:
- `uuid`: str (UUID v4)
- `content`: str (Raw block content)
- `clean_text`: str (Content stripped of id::, properties, and metadata)
- `indent_level`: int (Calculated from leading whitespace / 2 or 4)
- `properties`: Dict[str, Any] (Extracted from `key:: value` lines)
- `wikilinks`: List[str] (Matches `[[link]]`)
- `tags`: List[str] (Matches `#tag` or `[[#tag]]`)
- `block_refs`: List[str] (Matches `((uuid))`)
- `parent_id`: Optional[str] (Pointer to parent UUID)
- `children`: List['LogseqNode'] (Recursive children list)

## 2. The Stack-Machine Algorithm (Parsing Logic)
The parser must avoid regex-recursion. Use a `Stack` to track nesting:
1. Iterate line by line.
2. Determine `indent_level`.
3. `IF` indent > current_stack_top: `Push` new node as child.
4. `IF` indent == current_stack_top: `Sibling` node (same parent).
5. `IF` indent < current_stack_top: `Pop` stack until matching level is found.
6. **Property Stripping:** Lines matching `^[a-zA-Z0-9-]+::\s.*` must be extracted into `properties` and removed from `clean_text`.

## 3. Visitor Pattern Interface
To decouple AST traversal from logic, implement this interface:
```python
class ASTVisitor(ABC):
    @abstractmethod
    def visit_node(self, node: "LogseqNode") -> None: pass
    @abstractmethod
    def depart_node(self, node: "LogseqNode") -> None: pass

## 4. Compilation Constraints (Nuitka)
NO dynamic imports (__import__, importlib).

NO eval() or exec().

Use explicit model_rebuild() for recursive Pydantic models.

All dependencies must be defined in pyproject.toml (uv).