# NeedleRust v2: 全维度上下文分析框架

NeedleRust v2 是一个专业的实验框架,旨在量化大语言模型(LLM)在复杂、多维度约束下,信息检索与推理能力的衰减情况。

不同于简单的 "Needle In A Haystack"(大海捞针)测试,v2 构建了一个严谨的建模引擎,用于分析结构、语义和动态因素如何影响模型对上下文的维持能力。

## 🚀 项目目标

本框架将简单的"检索"任务转化为对 **上下文衰减 (Context Rust)** 的多维度量化分析,重点关注:
- **衰减量化**: 性能如何随距离、噪声和结构复杂度的增加而下降。
- **压力下推理**: 测试模型在碎片化上下文中处理冲突信息或执行多跳检索的能力。
- **结构敏感度**: 分析不同的数据封装格式(如 JSON, XML, Markdown)如何影响检索的稳定性。
- **输出压力下的漂移**: 强制长输出,观察自回归生成对早期上下文召回的影响。

## ✨ 核心功能

### 🏗️ 基础设施重构
- **`ExperimentPlan` 实验计划系统**: 支持通过 JSON 定义复杂的实验矩阵。允许定义多个因子的笛卡尔积组合(例如:长度 × 噪声 × 历史轮次 × 任务复杂度)。
- **`ContextAssembler` 组装管线**: 实现分层组装逻辑:
  `距离建模` → `碎片化建模` → `结构定义` → `语义填充` → `干扰注入` → `边界包装`。
- **`TurnManager` 轮次管理器**: 模拟多轮对话历史,量化对话长度和"新鲜度 (Recency)"对信息检索的影响。

### 📐 多维度建模

#### 空间与结构
- **埋点策略**: 支持 `Cluster`(簇状)和 `Interleaved`(交织)两种针点分布方式。
- **指令-数据距离**: 通过 `instruction_distance` / `query_distance` 因子,量化 system prompt → context → query 的绝对 token 距离。
- **边界分析**: 对比 `Plaintext`、`Markdown`、`XML` 和 `JSON` 等不同包装方式对检索率的影响。
- **KV 碎片化**: 通过 `fragment_count` / `needle_fragment_index` / `gap_tokens` 因子,将上下文切成多个不连续块,模拟 KV 碎片化对检索稳定性的影响。

#### 语义与逻辑
- **语义干扰**: 引入 `Semantic Distractors`(语义接近但事实错误)的干扰项。
- **多针冲突**: 实现 N 根针并发埋入,测试模型对 `Conflicting`(冲突)与 `Complementary`(互补)信息的消解能力。
- **任务复杂度阶梯**: `task_complexity` 因子在 `simple` → `multi_hop` → `complex` 三档模板间切换,逐步引入多跳与演绎推理。

#### 动态压力
- **历史累积**: 建模对话轮数增加对目标信息"可见度"的影响。
- **输出长度压力**: `output_pressure` 因子强制模型在最终答案后继续生成指定长度的 token,测试自回归漂移。

### 📊 评估系统升级
- **灵活评分机制**: 支持在 `Exact Match`(精确匹配)和 `Semantic Similarity`(语义相似度/Token 重叠)之间切换。
- **专项量化指标**:
  - **冲突消解率 (Conflict Resolution Rate)**: 衡量模型在面对矛盾信息时的正确率。
  - **基础检索率 (Retrieval Accuracy)**: 实验矩阵上的标准成功率。
- **自动分析报告**: 运行 `python main.py analyze` 后,会扫描 `results/*.csv`,为每个实验生成相关性矩阵 + 因子摘要 markdown(`results/<name>_report.md`),并汇总为 `results/report.md`。

## 📂 项目结构

```text
needlerust/
├── main.py               # 实验主入口 (run / analyze 子命令)
├── requirements.txt      # 项目依赖
├── todo.md               # 路线图与待办事项
├── src/
│   ├── client.py         # OpenAI 兼容 API 客户端
│   ├── config.py         # ExperimentPlan 与因子定义
│   ├── generators.py     # ContextAssembler 与分层管线、任务模板
│   ├── evaluator.py      # 多维度评估系统
│   ├── simulator.py      # 实验编排与缓存管理
│   ├── turn_manager.py   # 对话历史模拟
│   └── report.py         # 实验结果自动分析
├── configs/              # JSON 实验配置文件
│   ├── instruction_distance.json
│   ├── kv_fragmentation.json
│   ├── task_complexity.json
│   └── output_pressure.json
└── results/              # CSV 报表、cache.json、报告
```

## 🛠️ 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 环境配置
在项目根目录创建 `.env`(可参考 `.env.example`):
```env
LLM_API_KEY=你的API密钥
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o
```

### 3. 运行实验
v2 采用配置驱动模式。定义一个 JSON 实验计划文件,然后通过模拟器运行。

**`plan.json` 示例**:
```json
{
  "name": "depth_noise_test",
  "model": "gpt-4o",
  "base_url": "...",
  "api_key": "...",
  "needle": "秘密代码是 12345。",
  "question": "秘密代码是什么?",
  "factors": [
    { "name": "depth", "values": [0.1, 0.5, 0.9] },
    { "name": "noise", "values": [0.0, 0.2, 0.4] },
    { "name": "format", "values": ["plaintext", "json", "xml"] }
  ]
}
```

执行:
```bash
python main.py run --plan configs/instruction_distance.json
```

常用参数:
- `--results-dir results` — 输出目录
- `--no-cache` — 关闭缓存
- `--force-refresh` — 忽略已有缓存重新跑

### 4. 生成分析报告
```bash
python main.py analyze --results-dir results --output results/report.md
```
报告会输出每个实验的因子相关性矩阵(对数值型因子给出与 accuracy 的 Pearson r),以及每个因子的均值/分组摘要。

## 📑 可用因子一览

| 因子 | 适用范围 | 说明 |
|---|---|---|
| `total_tokens` | 通用 | 目标上下文 token 长度(×4 ≈ 字符数) |
| `depth` | 结构 | 簇状/交织埋点的相对位置 0..1 |
| `placement_strategy` | 结构 | `cluster` 或 `interleaved` |
| `noise` | 干扰 | 随机干扰词比例 0..1 |
| `semantic_distractors` | 语义 | 语义相近但事实错误的干扰句列表 |
| `format` | 边界 | `plaintext` / `markdown` / `xml` / `json` |
| `instruction_distance` | 距离 | 插入在 context 之前的 padding token 数 |
| `query_distance` | 距离 | 插入在 context 之后的 padding token 数 |
| `fragment_count` | 碎片化 | 上下文分块数 |
| `needle_fragment_index` | 碎片化 | needle 所在块的索引 |
| `gap_tokens` | 碎片化 | 相邻块之间省略的 token 数 |
| `task_complexity` | 任务 | `simple` / `multi_hop` / `complex` |
| `output_pressure` | 输出 | 强制要求长输出的 token 数 |
| `max_tokens` | 输出 | API 层的最大生成 token 数 |
| `turns` | 多轮 | 多轮对话历史(由 `TurnManager` 消费) |
| `additional_needles` | 多针 | 额外的 needle 列表(用于冲突/互补) |
| `eval_method` | 评估 | `exact` / `semantic` |

## 💰 Token 优化 (Caching)
为了最大限度降低成本,NeedleRust v2 引入了严谨的哈希机制:
- **确定性指纹**: 缓存键由全套实验参数(`plan.name` + `needle` + 因子组合 + `question`)共同生成。
- **零浪费执行**: 如果某个场景的参数已被测试,系统将直接从 `results/cache.json` 检索响应。

## 📝 许可证
MIT License
