# Tianhu icon library

This directory is the local icon library used by Tianhu 2.0 / 3.0 imports.

Lookup order:

1. `3.0/<normalized-tool-name>.*` or `2.0/<normalized-tool-name>.*`
2. `common/<normalized-tool-name>.*`
3. the normal `resources/icons` directory
4. Tianhu default icon

Naming rule: use lowercase ASCII names where possible, with non-alphanumeric
characters converted to underscores. Examples:

- `dirsearch.svg`
- `nmap.png`
- `burp.png`
- `fofa.ico`
