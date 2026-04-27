# 写作练习应用

本地运行的 AI 写作练习应用：每日 AI 出题（图片或场景）→ 用户写 ≥500 字 → AI 7 维度评分 → 据最弱维度生成下次专项作业 → 雷达图与折线图可视化。

## 启动

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
python -m my_writing
```

启动后浏览器自动打开 `http://localhost:3000`。第一次进入请先到「设置」tab 填写 API Key 与模型。

## 模型配置

应用支持多家 AI 服务，通过设置页随时切换：

- **Anthropic Claude**：`https://api.anthropic.com`，模型如 `claude-sonnet-4-6`
- **OpenAI / 兼容服务**：`https://api.openai.com/v1`，模型如 `gpt-4o`
- **Ollama 本地**：`http://localhost:11434`，模型如 `qwen2.5:7b`，无需 API Key
- **图片生成**：当前默认 OpenAI `gpt-image-1`

## 数据存储

所有数据保存在项目目录下的 `data.db`（SQLite 单文件）。删除即可重置。

## 开发

```bash
uvicorn my_writing.app:app --reload --port 3000
```
