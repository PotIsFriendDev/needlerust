# NeedleRust v2: 全维度上下文分析框架

NeedleRust v2 是一个专业的实验框架，旨在量化大语言模型（LLM）在复杂、多维度约束下，信息检索与推理能力的衰减情况。

不同于简单的 "Needle In A Haystack" (大海捞针) 测试，v2 构建了一个严谨的建模引擎，用于分析结构、语义和动态因素如何影响模型对上下文的维持能力。

## 🚀 项目目标

本框架将简单的“检索”任务转化为对 **上下文衰减 (Context Rust)** 的多维度量化分析，重点关注：
- **衰减量化**: 性能如何随距离、噪声和结构复杂度的增加而下降。
- **压力下推理**: 测试模型在碎片化上下文中处理冲突信息或执行多跳检索的能力。
- **结构敏感度**: 分析不同的数据封装格式（如 JSON, XML, Markdown）如何影响检索的稳定性。

## ✨ 核心功能

### 🏗️ 基础设施重构
- **`ExperimentPlan` 实验计划系统**: 支持通过 JSON/YAML 定义复杂的实验矩阵。允许定义多个因子的笛卡尔积组合（例如：长度 $\times$ 噪声 $\times$ 历史轮次）。
- **`ContextAssembler` 组装管线**: 实现分层组装逻辑：
  `结构定义` $\rightarrow$ `语义填充` $\rightarrow$ `干扰注入` $\rightarrow$ `边界包装`。
- **`TurnManager` 轮次管理器**: 模拟多轮对话历史，量化对话长度和“新鲜度 (Recency)”对信息检索的影响。

### 📐 多维度建模
- **空间与结构维度**:
    - **埋点策略**: 支持 $\text{Cluster}$ (簇状) 和 $\text{Interleaved}$ (交织) 两种针点分布方式。
    - **边界分析**: 对比 `Plaintext`、`Markdown`、`XML` 和 `JSON` 等不同包装方式对检索率的影响。
- **语义与逻辑维度**:
    - **语义干扰**: 引入 $\text{Semantic Distractors}$ (语义接近但事实错误) 的干扰项。
    - **多针冲突**: 实现 $N$ 根针并发埋入，测试模型对 $\text{Conflicting}$ (冲突) 与 $\text{Complementary}$ (互补) 信息的消解能力。
- **动态压力维度**:
    - **历史累积**: 建模对话轮数增加对目标信息“可见度”的影响。

### 📊 评估系统升级
- **灵活评分机制**: 支持在 `Exact Match` (精确匹配) 和 `Semantic Similarity` (语义相似度/Token重叠) 之间切换。
- **专项量化指标**: 
    - **冲突消解率 (Conflict Resolution Rate)**: 衡量模型在面对矛盾信息时的正确率。
    - **基础检索率 (Retrieval Accuracy)**: 实验矩阵上的标准成功率。

## 📂 项目结构

```text
needlerust/
├── main.py               # 实验主入口
├── requirements.txt      # 项目依赖
├── src/
│   ├── client.py         # OpenAI 兼容 API 客户端
│   ├── config.py          # ExperimentPlan 与因子定义 (新)
│   ├── generators.py     # ContextAssembler 与分层管线
│   ├── evaluator.py       # 多维度评估系统
│   ├── simulator.py      # 实验编排与缓存管理
│   └── turn_manager.py    # 对话历史模拟 (新)
├── configs/              # JSON 实验配置文件
└── results/              # CSV 报表与 cache.json
```

## 🛠️ 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 环境配置
设置环境变量：
```env
LLM_API_KEY=你的API密钥
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o
```

### 3. 运行实验
v2 采用配置驱动模式。您可以定义一个 JSON 实验计划文件，然后通过模拟器运行。

**`plan.json` 示例**:
```json
{
  "name": "depth_noise_test",
  "model": "gpt-4o",
  "base_url": "...",
  "api_key": "...",
  "needle": "秘密代码是 12345。",
  "question": "秘密代码是什么？",
  "factors": [
    { "name": "depth", "values": [0.1, 0.5, 0.9] },
    { "name": "noise", "values": [0.0, 0.2, 0.4] },
    { "name": "format", "values": ["plaintext", "json", "xml"] }
  ]
}
```

## 💰 Token 优化 (Caching)
为了最大限度降低成本，NeedleRust v2 引入了严谨的哈希机制：
- **确定性指纹**: 缓存键由全套实验参数共同生成。
- **零浪费执行**: 如果某个场景的参数已被测试，系统将直接从 `results/cache.json` 检索响应。

## 📝 许可证
MIT License
