# NeedleRust v2: Comprehensive Context Analysis Framework

## 🎯 目标
将项目从简单的 "Needle In A Haystack" 测试工具升级为多维度上下文衰减建模引擎，量化 LLM 在复杂约束下的信息检索与推理能力。

---

## 🏗️ 核心模块开发计划

### 1. 基础设施重构 (Infrastructure)
- [x] **引入 `ExperimentPlan` 配置系统**
    - 支持 JSON/YAML 定义实验矩阵。
    - 允许定义多个因子 (Factors) 的交叉组合（例如：长度 $\times$ 噪声 $\times$ 历史轮次）。
- [x] **升级 `ContextAssembler` (原 Generator)**
    - 实现分层组装逻辑：`结构定义` $\rightarrow$ `语义填充` $\rightarrow$ `干扰注入` $\rightarrow$ `边界包装`。
- [x] **实现 `TurnManager` (多轮对话模拟)**
    - 支持模拟 $N$ 轮历史对话，动态增加上下文压力。

### 2. 维度建模实现 (Factor Implementation)
#### 🔹 空间与结构维度
- [x] **Token 几何关系建模**: 实现 $\text{Cluster}$ (簇状) 和 $\text{Interleaved}$ (交织) 埋点。
- [ ] **指令-数据距离分析**: 量化 $\text{System Prompt} \rightarrow \text{Context} \rightarrow \text{Query}$ 的绝对 Token 距离。
- [x] **结构边界清晰度**: 实现 `Plaintext` / `Markdown` / `XML` / `JSON` 不同包装方式的对比。
- [ ] **KV 碎片化模拟**: 构造非连续、高度碎片化的上下文片段，测试检索稳定性。

#### 🔹 语义与逻辑维度
- [x] **语义维度干扰**: 引入 $\text{Semantic Distractors}$ (与目标信息语义接近但事实错误的干扰项)。
- [x] **多针冲突现象**: 实现 $N$ 根针的并发埋入，测试 $\text{Conflicting}$ (冲突) 与 $\text{Complementary}$ (互补) 信息的消解能力。
- [ ] **任务复杂程度阶梯**: 构建 $\text{Simple Retrieval} \rightarrow \text{Multi-hop} \rightarrow \text{Complex Reasoning}$ 的 Prompt 链。

#### 🔹 动态与输出维度
- [x] **历史轮次累积**: 建模对话轮数对信息新鲜度 (Recency) 的影响。
- [ ] **输出长度压力**: 强制要求长输出，测试自回归生成过程中的上下文漂移。

### 3. 评估系统升级 (Evaluation)
- [x] **升级判定算法**: 从 `simple contains` $\rightarrow$ `Semantic Similarity (BERTScore/Cosine)`。
- [x] **引入多维指标**:
    - $\text{Retrieval Accuracy}$ (基础检索率)
    - $\text{Conflict Resolution Rate}$ (冲突消解率)
    - $\text{Instruction Following Score}$ (指令遵循度)
- [ ] **自动分析报告**: 生成各因子对准确率影响的 $\text{Correlation Matrix}$ (相关性矩阵)。

---

## 📈 实验优先级
1. **P0 (基础)**: `ExperimentPlan` 重构 $\rightarrow$ 多轮对话模拟 $\rightarrow$ 结构边界分析。
2. **P1 (进阶)**: 多针冲突 $\rightarrow$ 语义干扰 $\rightarrow$ 指令距离建模。
3. **P2 (深度)**: KV 碎片化模拟 $\rightarrow$ 输出长度压力 $\rightarrow$ 复杂任务阶梯。

## 📝 备注
- 所有的实验必须通过 `cache.json` 保证 Token 零浪费。
- 每个维度应提供对应的 $\text{Baseline}$ (基准) 场景以便对比。
