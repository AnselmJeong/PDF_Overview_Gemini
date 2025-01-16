This is a tool to summarize and overview PDFs.

## How to Use

### Run the UI
```bash
uv run streamlit run src/ui_main.py
```

### Run the CLI
```bash
# summarize a single pdf
uv run src/main.py <path-to-pdf>

# summarize a directory of pdfs
uv run src/main.py --directory <path-to-directory>
uv run src/main.py -d <path-to-directory>

# write the summary to a markdown file
uv run src/main.py <path-to-pdf> --write_md 
uv run src/main.py <path-to-pdf> -w
```

Developed by Anselm Jeong
