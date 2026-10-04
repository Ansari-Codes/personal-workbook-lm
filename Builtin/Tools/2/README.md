# PAWM workbook tools

Built-in functions for workbook sources and outputs, bounded PDF text extraction, web requests, sandboxed process execution, and workbook-scoped notes.

Functions that access workbook data receive an internal workbook context from PAWM. That parameter is intentionally omitted from the model-facing schema.

Python and shell commands run in a temporary directory with a timeout. This is not an operating-system security sandbox; only use this local application with trusted prompts and data.
