# NeedleRust (上下文检索衰减建模工具)

这是一个用于研究大语言模型（LLM）在不同因素影响下，上下文检索能力如何衰减（Context Rust / Degradation）的实验框架。

## 🚀 项目目标

本项目旨在量化 LLM 在处理长文本时，由于信息位置、上下文长度以及噪声干扰而导致的性能下降，类似于业界常用的 "Needle In A Haystack" (大海捞针) 测试，但提供了更灵活的建模参数。

## ✨ 核心功能

- **位置衰减建模 (Position Rust)**: 支持将目标信息（Needle）放置在上下文的任意百分比位置（0.0 - 1.0），用于检测 "Lost in the Middle" 现象。
- **规模衰减建模 (Scale Rust)**: 可自定义不同的上下文总长度（Token 数量），观察模型在不同窗口大小下的稳定性。
- **噪声干扰模拟 (Noise Interference)**: 支持向上下文中注入特定比例的无关干扰信息，模拟真实场景中低信噪比对检索的影响。
- **智能结果缓存 (Token Saving)**: 自动对实验场景进行哈希校验，缓存已完成的请求响应，避免在调试或重复运行相同参数时浪费 Token。
- **通用 API 接入**: 基于 OpenAI 协议，可无缝接入任何兼容 OpenAI 接口的 LLM 提供商。

## 📂 项目结构

```text
needlerust/
├── main.py               # 实验主入口，定义测试场景并运行
├── requirements.txt      # 项目依赖
├── src/
│   ├── client.py         # OpenAI 兼容 API 客户端封装
│   ├── generators.py     # 上下文生成器（包含大海捞针与噪声注入逻辑）
│   ├── evaluator.py      # 结果评估器（计算检索准确率与衰减率）
│   └── simulator.py      # 实验编排层，管理多场景运行
├── configs/              # 实验配置目录
└── results/              # 结果输出目录（CSV 报表与 cache.json）
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
```bash
python main.py
```

## 💰 Token 优化 (Caching)

为了防止在实验过程中产生高额费用，本项目内置了缓存机制：
- **自动缓存**: 所有请求结果默认保存在 `results/cache.json` 中。
- **哈希校验**: 系统会根据 `(场景名, 信息内容, 长度, 深度, 噪声, 问题)` 自动生成唯一指纹。
- **强制刷新**: 如果需要重新测试（例如更换了模型版本），可以在调用 `run_experiment` 时设置 `force_refresh=True`。

## 📊 结果分析

运行结束后，实验结果将保存至 `results/experiment_results.csv`。你可以通过该文件分析以下维度：
- **Depth vs Accuracy**: 目标信息位置与准确率的关系图（检测 U 型曲线）。
- **Tokens vs Accuracy**: 上下文长度增加时性能的下降趋势。
- **Noise vs Accuracy**: 噪声比例对模型鲁棒性的影响。

## 📝 许可证
MIT License
