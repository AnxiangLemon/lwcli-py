import json
from pathlib import Path
from typing import Dict

SWAGGER_PATH = Path("swagger.json")
OUT_DIR = Path(__file__).resolve().parent.parent / "models"

type_map = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
    "array": "list",
    "object": "dict",
}

def swagger_to_pydantic():
    if not SWAGGER_PATH.exists():
        print("swagger.json not found at", SWAGGER_PATH)
        return
    spec = json.loads(SWAGGER_PATH.read_text(encoding="utf-8"))
    defs: Dict = spec.get("definitions", {})
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for name, schema in defs.items():
        # sanitize name to python file/class
        cls_name = name.replace(".", "_").replace("-", "_")
        props = schema.get("properties", {})
        lines = ["from pydantic import BaseModel", "from typing import Optional, Any\n", f"class {cls_name}(BaseModel):"]
        if not props:
            lines.append("    pass\n")
        else:
            for prop_name, prop_schema in props.items():
                t = prop_schema.get("type", "Any")
                py_t = type_map.get(t, "Any")
                # simple handling for arrays
                if t == "array":
                    items = prop_schema.get("items", {})
                    it_type = type_map.get(items.get("type", ""), "Any")
                    py_t = f"list[{it_type}]"
                lines.append(f"    {prop_name}: Optional[{py_t}] = None")
        out_file = OUT_DIR / f"{cls_name}.py"
        out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("Wrote", out_file)

if __name__ == "__main__":
    swagger_to_pydantic()
