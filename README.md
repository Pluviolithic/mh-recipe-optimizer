# Getting Started

- Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Sync & source the virtual environment
- Run the optimizer

```
git clone https://github.com/Pluviolithic/mh-recipe-optimizer.git
cd mh-recipe-optimizer
uv sync
source .venv/bin/activate
```

Examples
```
optimize "Vulcan's Wrath" -r
optimize "Daestrophe" -a
optimize "Garden of Gaia" -rs
```