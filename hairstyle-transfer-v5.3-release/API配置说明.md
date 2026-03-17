# API密钥配置说明

## 问题诊断

根据您的日志输出，应用当前运行在**演示模式**，原因是：

```
⚠️ 当前运行在演示模式（API密钥未设置）
💡 请设置环境变量 BAILIAN_API_KEY 以使用真实API
```

您设置的是 `DASHSCOPE_API_KEY`，但应用需要的是 `BAILIAN_API_KEY`。

---

## 解决方案

### 方法1：设置正确的环境变量名（推荐）

在终端执行以下命令：

```bash
# 设置API密钥
export BAILIAN_API_KEY='your-bailian-api-key-here'

# 运行应用
python app.py
```

### 方法2：永久配置到shell配置文件

```bash
# 添加到 ~/.zshrc
echo "export BAILIAN_API_KEY='your-bailian-api-key-here'" >> ~/.zshrc

# 重新加载配置
source ~/.zshrc

# 运行应用
python app.py
```

### 方法3：在代码中直接设置（不推荐，仅用于测试）

修改 `app.py` 文件，在第22行之前添加：

```python
import os
os.environ['BAILIAN_API_KEY'] = 'your-bailian-api-key-here'
```

---

## 验证配置是否成功

运行应用后，如果看到以下输出，说明配置成功：

```
✅ 当前运行在生产模式（百炼图生图）
💡 已设置环境变量 BAILIAN_API_KEY
```

如果仍然显示"演示模式"，说明环境变量未生效。

---

## 注意事项

1. **环境变量名必须是 `BAILIAN_API_KEY`**，不是 `DASHSCOPE_API_KEY`
2. 每次打开新终端窗口都需要重新 `export`，或者写入 `~/.zshrc` 永久生效
3. 修改 `~/.zshrc` 后必须执行 `source ~/.zshrc` 才能生效
4. API密钥请妥善保管，不要泄露给他人

---

## 常见问题

### Q: 为什么我设置了 DASHSCOPE_API_KEY 但还是演示模式？
A: 因为代码中读取的是 `BAILIAN_API_KEY`，两个环境变量名不同。

### Q: 如何确认环境变量已设置？
A: 在终端执行 `echo $BAILIAN_API_KEY`，如果显示您的密钥，说明设置成功。

### Q: 我不想每次都手动 export，怎么办？
A: 将 export 命令写入 `~/.zshrc` 文件，每次打开终端会自动加载。
