# cg3d-maya-core

A collection of Maya functions and classes that can be reused by other tools.

## Packages

- `cg3dguru_v2` is the current implementation. It uses `maya.cmds` and
  `maya.api.OpenMaya` and has no PyMEL dependency.
- `cg3dguru` is the unchanged legacy implementation. Install the optional
  `legacy` dependency if a project still imports it.

```shell
pip install .
pip install ".[legacy]"  # Only for the original cg3dguru package.
```

## uData v2

The declarative API is retained, so custom data classes stay compact:

```python
from cg3dguru_v2 import udata


class ExportData(udata.BaseData):
    @staticmethod
    def get_attributes():
        return [
            udata.create_attr("identifier", "string"),
            udata.create_attr("enabled", "bool"),
            udata.create_attr("source", "message"),
        ]

    @classmethod
    def post_create(cls, data):
        data.enabled.set(True)
```

`BaseData` accepts Maya node names or `cg3dguru_v2.maya.Node` handles. It
returns a lightweight `Attribute` handle supporting `get`, `set`, `lock`,
`unlock`, `inputs`, `outputs`, indexed attributes, and child access such as
`data.enabled`. These handles intentionally cover the package's common node
and plug operations rather than reproducing PyMEL's full object model.

Existing code can migrate package imports first:

```python
import cg3dguru_v2.udata as udata
```

Code outside uData should pass Maya node names to v2 functions. Matrix helpers
use `maya.api.OpenMaya.MVector` and `MMatrix`.
