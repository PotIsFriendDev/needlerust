# NeedleRust (上下文检索衰减建模工具)

这是一个用于研究大语言模型（LLM）在不同因素影响下，上下文检索能力如何衰减（Context Rust / Degradation）的实验框架。

## 🚀 项目目标

本项目旨在量化 LLM 在处理长文本时，由于信息位置、上下文长度以及噪声干扰而导致的性能下降，类似于业界常用的 "Needle In A Haystack" (大海捞针) 测试，但提供了更灵活的建模参数。

## ✨ 核心功能

- **位置衰减建模 (Position Rust)**: 支持将目标信息（Needle）放置在上下文的任意百分比位置（0.0 - 1.0），用于检测 "Lost in the Middle" 现象。
- **规模衰减建模 (Scale Rust)**: 可自定义不同的上下文总长度（Token 数量），观察模型在不同窗口大小下的稳定性。
- **噪声干扰模拟 (Noise Interference)**: 支持向上下文中注入特定比例的无关干扰信息，模拟真实场景中低信噪比对检索的影响。
- **动态参数配置**: 通过命令行参数快速定义测试矩阵，无需修改代码即可调整 Tokens、深度和噪声。
- **智能结果缓存 (Token Saving)**: 自动对实验场景进行哈希校验，缓存已完成的请求响应，避免在调试或重复运行相同参数时浪费 Token。
- **通用 API 接入**: 基于 OpenAI 协议，可无缝接入任何兼容 OpenAI 接口的 LLM 提供商。

## 📂 项目结构

```text
needlerust/
├── main.py               # 实验主入口，支持命令行参数配置
├── requirements.txt      # 项目依赖
├── src/
│   ├── client.py         # OpenAI 兼容 API 客户端封装
│   ├── generators.py     # 上下文生成器（包含大海捞针与噪声注入逻辑）
│   ├── evaluator.py      # 结果评估器（计算检索准确率与衰减率）
│   └── simulator.py      # 实验编排层，管理多场景运行
├── configs/              # 实验配置目录
└── results/              # 结果输出目录（时间戳 CSV 报表与 cache.json）
```

## 🛠️ 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 环境配置
在项目根目录下创建 `.env` 文件或设置环境变量：
```env
LLM_API_KEY=你的API密钥
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o
```

### 3. 运行实验
使用默认参数运行：
```bash
python main.py
```

## ⚙️ 高级用法 (命令行参数)

你可以通过参数快速自定义测试矩阵，无需修改源代码：

| 参数 | 说明 | 默认值 | 示例 |
| :--- | :--- | :--- | :--- |
| `--tokens` | 想要测试的 Token 长度列表 | `4000 8000 16000` | `--tokens 8000 32000` |
| `--depths` | 目标信息所在位置 (0.0-1.0) | `0.1 0.3 0.5 0.7 0.9` | `--depths 0.1 0.5 0.9` |
| `--noise` | 噪声注入比例 (0.0-1.0) | `0.0 0.2` | `--noise 0.0 0.3` |
| `--needle` | 要埋入的秘密信息 | `"The secret code is 12345."` | `--needle "Password is ABC"` |
| `--question` | 针对信息的提问内容 | `"What is the secret code?"` | `--question "What is the password?"` |

**组合示例：**
测试 32k 长度、在 50% 深度、注入 30% 噪声的单一场景：
```bash
python main.py --tokens 32000 --depths 0.5 --noise 0.3
```

## 💰 Token 优化 (Caching)

为了防止在实验过程中产生高额费用，本项目内置了缓存机制：
- **自动缓存**: 所有请求结果默认保存在 `results/cache.json` 中。
- **哈希校验**: 系统会根据 `(场景名, 信息内容, 长度, 深度, 噪声, 问题)` 自动生成唯一指纹。
- **时间戳快照**: 结果文件以时间戳命名 (例如 `experiment_results_2023...csv`)，防止文件锁定且方便对比。
- **强制刷新**: 如果需要重新测试，可在代码中调用 `run_experiment` 时设置 `force_refresh=True`。

## 📊 结果分析

运行结束后，实验结果将保存至 `results/` 目录下的 CSV 文件。你可以通过该文件分析以下维度：
- **Depth vs Accuracy**: 目标信息位置与准确率的关系图（检测 U 型曲线）。
- **Tokens vs Accuracy**: 上下文长度增加时性能的下降趋势。
- **Noise vs Accuracy**: 噪声比例对模型鲁棒性的影响。

## 📝 许可证
MIT License
