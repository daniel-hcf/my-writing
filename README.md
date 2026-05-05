# 写作练习应用

本地运行的 AI 写作练习应用：每日故事种子扩写（300~800 字）/ 看图写作 / 每 3 天辅助梗概练习 → AI 7 维度评分 → 据最弱维度生成下次专项作业 → 雷达图与折线图可视化。

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

## API Key 加密

AI 服务商的 API Key 会加密后保存到 `data.db`。应用首次启动时会自动生成本机加密主密钥，默认放在当前用户配置目录下，例如 Windows 的 `%APPDATA%\my-writing\secret.key`。

已有明文 `apiKey` 会在启动时自动迁移为 `enc:v1:...` 密文；设置页仍然只显示 `***`。如果只泄露 `data.db`，无法直接读出 API Key。

如果删除或丢失 `secret.key`，已加密的 API Key 将无法解密，需要在设置页重新填写。服务器或容器部署可以用 `MY_WRITING_ENCRYPTION_KEY` 指定 Fernet 主密钥。
