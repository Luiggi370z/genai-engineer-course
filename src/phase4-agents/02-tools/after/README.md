# 4.2 Tools — reference

Read-only, reversible, and gated-irreversible tools with docstring-as-interface, validation, and error-as-data. The approval for the irreversible tool lives in application state (`grant_approval`), never in the tool signature — the model fills tool arguments, so an `approve` parameter would let it approve itself.
