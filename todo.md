# NeedleRust v2: Comprehensive Context Analysis Framework

## 🎯 目标
将项目从简单的 "Needle In A Haystack" 测试工具升级为多维度上下文衰减建模引擎，量化 LLM 在复杂约束下的信息检索与推理能力。

---

## 🏗️ 核心模块开发计划

### 1. 基础设施重构 (Infrastructure)
- [x] **引入 `ExperimentPlan` 配置系统**
    - 支持 JSON/YAML 定义实验矩阵。
    - 允许定义多个因子 (Factors) 的交叉组合（例如：长度 × 噪声 × 历史轮次）。
- [x] **升级 `ContextAssembler` (原 Generator)**
    - 实现分层组装逻辑：`距离建模` → `碎片化建模` → `结构定义` → `语义填充` → `干扰注入` → `边界包装`。
- [x] **实现 `TurnManager` (多轮对话模拟)**
    - 支持模拟 $N$ 轮历史对话，动态增加上下文压力。
- [x] **CLI 子命令化** — `python main.py run` / `analyze`。
- [x] **缓存机制** — `results/cache.json` 哈希键 = `plan.name|needle|params|question`。

### 2. 维度建模实现 (Factor Implementation)
#### 🔹 空间与结构维度
- [x] **Token 几何关系建模** — `Cluster` / `Interleaved` 埋点。
- [x] **指令-数据距离分析** — `DistanceAssembler`,因子 `instruction_distance` / `query_distance`。
- [x] **结构边界清晰度** — `Plaintext` / `Markdown` / `XML` / `JSON`。
- [x] **KV 碎片化模拟** — `FragmentationAssembler`,因子 `fragment_count` / `needle_fragment_index` / `gap_tokens`。

#### 🔹 语义与逻辑维度
- [x] **语义维度干扰** — `Semantic Distractors`。
- [x] **多针冲突现象** — `additional_needles`,支持 `Conflicting` / `Complementary` 消解。
- [x] **任务复杂程度阶梯** — `task_complexity`: `simple` / `multi_hop` / `complex`。

#### 🔹 动态与输出维度
- [x] **历史轮次累积** — `turns` 因子。
- [x] **输出长度压力** — `output_pressure` / `max_tokens`,在 prompt 尾部追加压力指令。

### 3. 评估系统升级 (Evaluation)
- [x] **升级判定算法** — `exact` / `semantic` (token overlap)。
- [x] **多维指标** — `Retrieval Accuracy` / `Conflict Resolution Rate` / `Instruction Following Score`。
- [x] **自动分析报告** — `src/report.py`,生成 Pearson 相关性矩阵 + 因子摘要。

---

## ✅ 已验证事实 (来自 DeepSeek 实测)

- 2026-07-09 用 `deepseek-chat` 跑通 `configs/instruction_distance.json` 的 24 场景,平均 ~1.1s/场景。
- 24 场景整体 mean accuracy = **0.417**。
- 关键发现:
    - `noise` r = **-0.507**,噪声 0.0→0.2 准确率 0.667→0.167,影响最显著。
    - `instruction_distance` r = -0.133,`0→2000` 准确率 0.625→0.375,呈现距离衰减但被噪声淹没。
    - `query_distance` r = -0.169,`0→1000` 准确率 0.500→0.333。
    - `total_tokens` r = +0.169(异常,推测是 4k 场景 instruction_distance=0 集中导致样本不均衡)。

---

## 🚧 下一阶段待办 (Next Sprint)

### 4. 评估器精细化 (Evaluator Hardening)
- [ ] **多针拆解评估**:当前 `check_accuracy` 用第一个 needle 做单点匹配,需要在多针场景下逐根 needle 评估并输出:
    - `per_needle_accuracy` 列表
    - `conflict_resolution_rate`(主指标,从 `calculate_conflict_resolution` 接入主流程)
    - `all_correct` / `majority` / `first_only` 三档聚合。
- [ ] **`semantic` 评估升级**:当前是简单 token 重叠,改为可选 BERTScore / sentence-transformer cosine;允许 plan 中通过 `eval_method: "bert"` 切换(并把 bert-score / sentence-transformers 写入可选依赖)。
- [ ] **数字与列表型 needle 解析**:当前 "12345" 用 `contains` 命中,但模型答 "the code is **12345**" 已 OK;对长数字串/邮箱/JSON 值要更稳。加入 `normalize_response()` 工具(去 markdown 强调符号、统一标点、提取数字子串)。
- [ ] **`Instruction Following Score`**:在 `task_complexity=complex` 场景下,要求模型按 3 步格式输出;新增评估器检查"是否按步骤作答"(`has_step_1` / `has_step_2` / `has_step_3`)。

### 5. 报告系统增强 (Report)
- [ ] **Baseline 强制对比** — 在 `report.py` 中,允许 plan 通过 `global_settings.baseline_plan` 指向一个对照组 plan 的 CSV,生成 Δaccuracy 矩阵(实现 todo 备注里的 "Baseline 场景" 要求)。
- [ ] **多 CSV 聚合相关矩阵** — `analyze_all` 当前只输出 per-file 相关,需加入:把同 plan 名下的多次 run 合并后再算相关,避免单次 24 场景的样本抖动。
- [ ] **JSON 报告输出** — 与 markdown 同步输出 `results/report.json`,便于 CI / Dashboard 抓取。
- [ ] **可视化** — 输出 `results/heatmap_<plan>.png`(因子 1 × 因子 2 → accuracy 热力图),用 matplotlib 即可。

### 6. 因子扩展 (Factors)
- [ ] **`semantic_distractors` 数量化** — 当前接受 list,改接受 `count` 字段并由生成器动态造出语义相似但事实错误的句子(用 LLM 一次性预生成 cache)。
- [ ] **多 needle 冲突显式开关** — `needle_mode: "conflicting" | "complementary" | "duplicate"`,自动构造 N 个版本。
- [ ] **格式 (format) 之外的边界实验** — `code_fence` / `csv` / `yaml` / `numbered_list`,作为 `format` 的扩展值。
- [ ] **Recency 衰减曲线** — 当前 `turns` 是任意轮数,改为 `recency_factor = position_from_query / total_turns`,可输出"新鲜度 vs 准确率"曲线。

### 7. 真实数据再跑一轮 (Validation Sweep)
- [ ] 跑通 `configs/kv_fragmentation.json`(12 场景)— 验证 `fragment_count` 对 deepseek-chat 的影响。
- [ ] 跑通 `configs/task_complexity.json`(12 场景)— 验证多跳 prompt 模板的指令遵循度。
- [ ] 跑通 `configs/output_pressure.json`(8 场景)— 验证长输出下是否出现 context drift。
- [ ] 综合 plan:把 `instruction_distance × output_pressure × task_complexity`(3×2×3 = 18 场景)作为 P0 综合验证。

### 8. 工程化 (Engineering)
- [ ] **JSON Schema 校验** — 为 `plan.json` 写 pydantic / jsonschema,`from_json` 失败时给出明确错误。
- [ ] **YAML 支持** — todo 中已承诺,目前只支持 JSON;补 `pyyaml` + `from_yaml`。
- [ ] **并发 / 异步** — 当前串行跑 24 场景,加 `--workers` 用 `concurrent.futures.ThreadPoolExecutor` 加速(OpenAI 客户端线程安全)。
- [ ] **重试与超时** — `client.get_completion` 当前 `except` 吞掉错误返回空串,改为带 `tenacity` 重试 + 错误标记列。
- [ ] **TUI 进度** — 替换 `tqdm`,加入 ETA / 失败计数 / 当前 token 估算。
- [ ] **CI smoke test** — `pytest` 中加 1 个 mock client 的端到端测试,验证 4 个 plan 都能跑通。

### 9. 文档与复现 (Docs)
- [ ] **方法论文档** — 在 `docs/methodology.md` 写清每个因子的定义、为何重要、引用(LEval / RULER / NeedleBench)。
- [ ] **结果解读指南** — `docs/interpreting_results.md`:相关性 r 的强度如何解读、什么时候噪声胜过主效应。
- [ ] **复现脚本** — 顶层 `scripts/reproduce_all.py`,一键顺序跑 4 个示例 plan + analyze。
- [ ] **更新 README** — 把已新增的"因子一览"和"报告章节"链接到 docs。

---

## 📈 实验优先级

1. **P0 (立即)**: 评估器精细化 §4 → 多 CSV 聚合 §5 → 综合 plan 跑通 §7。
2. **P1 (本周)**: 因子扩展 §6 → 工程化 §8 中重试/并发/JSON Schema。
3. **P2 (后续)**: 报告可视化 §5 → 文档 §9 → YAML 支持 §8。

## 📝 备注
- 所有实验必须通过 `cache.json` 保证 Token 零浪费。
- 每个维度应提供对应的 Baseline 场景以便对比(§5 强制 baseline 对比将作为 P0)。
- 真实数据中 `noise` 效应远大于 `instruction_distance`,未来 plan 设计应把 `noise` 因子与目标因子正交化(固定 noise=0 再测距离)以避免共线性。
