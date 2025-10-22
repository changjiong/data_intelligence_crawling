
## 使用 uv（无需 CI）
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.profile 2>/dev/null || source ~/.bashrc

bash setup_uv.sh 3.11
# 或者
make setup PY=3.11

uv run python src/pipeline.py --dry-run
uv run -m pytest
```
