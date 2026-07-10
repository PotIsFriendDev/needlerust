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
- [x] **identifier-fallback** (2026-07-10, 7e3991d) — 在 4 步 substring / fact / prefix / digit-fallback 之前插入新 step 0:从 needle 提取大写+连字符 ID (`BLUE-OCEAN-7421`、`HARRIER-19`、`12345`、`NIGHTHAWK`),作为子串匹配 normalized response。修了 23 条假阴性。
- [x] **needle 措辞统一** (2026-07-10, 5a03eed) — `instruction_distance.json` variant 1/2 把 "vault code" 改为 "secret code",与 question 对齐。配套 test `test_instruction_distance_needle_wording_matches_question` 防回归。

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

## ⚠️ 项目设计问题(2026-07-09 reasoner 复盘)

跑了 4 个 plan × 80 场景,发现以下项目层的问题,**这些问题限制了实验结论的有效性,即使加大样本量也无法解决**,需要先修才能继续扩实验。

### P-A. 评估器对 reasoner 不友好 (根因,优先级最高)
- **现象**: `task_complexity` 12 场景里 0.5 准确率,响应记录显示 reasoner 习惯先输出 `Reasoning: ...` 再给答案,触发 `evaluator.check_accuracy` 的精确匹配失败。
- **直接影响**: 简单任务 reasoner 写得最啰嗦,反而判错最多 → `simple < multi_hop < complex` 的反直觉结果(0.25/0.5/0.75)。
- **修复方向**:
    - `client.py` 截取 `Final Answer:` 之后的内容(若 reasoner 用了 thinking,截掉 reasoning 段)。
    - 或 `evaluator.py` 加 fuzzy / token-set 匹配,允许 markdown 强调符号变体(`**12345**` / `12345.` / `\boxed{12345}` 都算对)。
    - 数字型 needle 单独走 `normalize_response()` 工具,提取数字子串后做精确匹配。
- **已修部分** (7e3991d):identifier-fallback 让 bare-ID response 在长 needle 下也判 1.0(解决了 23/23 假阴性)。Reasoner 走 Final Answer 截取的逻辑还没接。

### P-B. Needle 太短,准确率钉在 1.0 (天花板效应)
- **现象**: `instruction_distance` 24 场景全 1.0,`output_pressure` 4 场景全 1.0。`"The secret code is 12345."` 仅 7 token,reasoner 几乎不可能丢。
- **影响**: 这两个 plan **永远测不出衰减**,无论跑多少样本。`noise` 也没足够空间起作用。
- **修复方向**:
    - 准备 3 档 needle: 短(7 token,当前)/ 中(50–100 token,多个实体)/ 长(200+ token,信息密集)。
    - 长 needle 强制模型"找"而不是"扫"。
- **已修** (7e3991d):所有 plan 加 `needle_variant: [0, 1, 2]` 3 档 tier;`instruction_distance` / `output_pressure` 三个 variant 实际长度 25 / 401 / 1193 字符(v0/v1/v2)。

### P-C. 因子水平数过少,看不出趋势
- **现象**: `instruction_distance` 三个水平 `[0, 500, 2000]` 跳 4 倍;`fragment_count` `[1, 3, 6, 12]` 指数跳。
- **影响**: 即便有衰减也拟合不出曲线,只能给"是/否"判断。
- **修复方向**: 在已知敏感区间加 5–8 个水平(如 `instruction_distance` 在 0–2000 内补 200/500/1000/1500),输出曲线而不是 r。
- **已修** (部分):4 个 config 现在都加 `needle_variant: [0, 1, 2]` 3 档,但**总长水平仍 4k/16k 两个**——见 P-F。

### P-D. 单次实验无重复,无法做统计推断
- **现象**: `simulator.py:64` 用 `params` 算 hash,每个组合只跑 1 次,无 `seed` 维度,无 `deepseek-chat` 对照。
- **影响**: Pearson r 在小样本(每格 1–2 样本)下极不稳定,目前所有 r 值都不应作为结论引用。
- **修复方向**:
    - 给 `factor` 加 `seed` 维度(3–5 个 seed)做无成本扩样本。
    - 每个 plan 跑两次(chat + reasoner),出 `Δaccuracy` 矩阵,才能说"reasoner 在哪强"。
- **已修** (2378e74):4 个 config `seed: [1,2,3]` → `[1..10]`,每格 n=3 → n=10。Baseline 模型对照未做。

### P-E. Report 合并污染数据 (工程问题,小)
- **现象**: `analyze_all` 扫 `results/*.csv` 全部合并,2026-07-09 第一次跑代理故障的 0 分 CSV 进入了 `report.md`。
- **修复方向**: `analyze` 子命令加 `--exclude <glob>`,或让 `run` 把成功 CSV 写到 `results/success/`,失败写到 `results/failed/`。
- **已修** (2378e74, partial):`--exclude <glob>` 加到 `analyze` 子命令;`results/success/failed/` 目录未分。

### P-F. 4k-16k 尺度测不出 attention 衰减(新发现,P0)
- **现象**: 3 份 sweep 全部钉在 4-16k context(`total_tokens ∈ {4000, 8000, 16000}`),在这个尺度下 `fragment_count` / `gap_tokens` / `instruction_distance` / `output_pressure` 都看不到信号(全 0.9+ 或全 0.4-,无趋势)。
- **影响**: **现有 sweep 在错尺度上跑**,跟 P-B 的"needle 太短"叠加后,所有"距离/分片/续写"因子都被天花板或地板钉死。
- **修复**: 加 `context_length_sweep.json` (14cf812),拉到 4k → 131072,4 档 × 10 seed = 40 scenarios,只测 length,其他全钉死。**未跑**。
- **配套**:跑出真信号后,后续所有 sweep 都把 scale 提到 ≥64k,否则同病。

---

## 🧾 Commit 流水 (2026-07-10)

按时间倒序:

| Commit | 主题 | 关键改动 |
|---|---|---|
| `14cf812` | **P0-1: context_length_sweep** | 新 plan + 7 smoke test |
| `2378e74` | **error 列 + seed×10** | client `(content, error)`,report 跳过 error,4 config seed 10 |
| `5a03eed` | **needle 措辞统一** | instruction_distance variant 1/2 vault→secret + 措辞 guard test |
| `7e3991d` | **v2 多 tier + 23 grader 假阴性** | identifier-fallback + 3 档 needle_variant + seed/CLI/analyze exclude |
| `610d543` | v2: factor 收尾 + auto-analyze | (pre-this-session) |
| `abbe283` | v2 | (pre-this-session) |
| `f1f5955` | Initial commit | (pre-this-session) |

测试总览: `47/47` pass(`test_evaluator.py` 33 + `test_client_and_report.py` 7 + `test_context_length_sweep.py` 7)。

---

## 📊 当前状态 (2026-07-10)

- 4 份 plan(原 3 份 + context_length_sweep)全部 ready,seed×10,基础设施修复全到位。
- `results/` 有 3 份 CSV,全部 5a03eed / 7e3991d 修复**之前**跑出来的,留作历史对照,不应再用作分析依据。
- **下一步触发**: `python main.py run --plan configs/context_length_sweep.json` —— 40 scenarios,4k-128k,直接给 length-attention 曲线。

---

## 🚧 下一阶段待办 (Next Sprint)

### 4. 评估器精细化 (Evaluator Hardening)
- [x] **identifier-fallback** (2026-07-10) — 修复 23 条假阴性:在 `check_accuracy('exact')` 的 4 步检查之前,从 needle 提取 `BLUE-OCEAN-7421` / `HARRIER-19` / `12345` 这类大写+连字符 ID,作为子串匹配 normalized response。覆盖 kv_fragmentation / instruction_distance / output_pressure 三个 plan 的长 needle 场景。配套测试: `tests/test_evaluator.py` 33 case 全过(25 + 8 wording-robustness)。
- [x] **needle 措辞 vs question 防漂移** (2026-07-10) — `test_instruction_distance_needle_wording_matches_question` 加载 config,断言每个 needle variant 包含 question 用的关键词。防 grader 走 fact-substring 路径时因措辞偏置再咬一口。
- [x] **基础设施失败透出** (2026-07-10, 2378e74) — `client.get_completion` 不再静默吞错,改为 `(content, error)` tuple;error 写到 CSV 的 `error` 列;`report.analyze` 跳过 error 行,Mean accuracy 不再被 API 失败拉低。改 4 个 config 的 `seed` 因子从 `[1,2,3]` → `[1..10]`。
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
- [x] **context_length_sweep** (2026-07-10, 14cf812) — 新 plan,4 length × 10 seed = 40 scenarios,`total_tokens: [4096, 16384, 65536, 131072]`,其他全钉死。**P0-1 任务:在 4k-128k 全尺度测"长度 → 召回"。** 配套 7 个 smoke test(锁住 scenario 数、length 范围、length 误差 ≤5%、needle 必在、非 length/seed 因子单值)。**未跑**,等用户触发。
- [ ] **`semantic_distractors` 数量化** — 当前接受 list,改接受 `count` 字段并由生成器动态造出语义相似但事实错误的句子(用 LLM 一次性预生成 cache)。
- [ ] **多 needle 冲突显式开关** — `needle_mode: "conflicting" | "complementary" | "duplicate"`,自动构造 N 个版本。`calculate_conflict_resolution` 函数已写好,只需接入主流程。
- [ ] **格式 (format) 之外的边界实验** — `code_fence` / `csv` / `yaml` / `numbered_list`,作为 `format` 的扩展值。
- [ ] **Recency 衰减曲线** — 当前 `turns` 是任意轮数,改为 `recency_factor = position_from_query / total_turns`,可输出"新鲜度 vs 准确率"曲线。**优先级 P0-2**:在 context_length_sweep 跑出 ≥64k 信号后,挪 needle 位置 0%→100%,5 档 × 64k context × 10 seed = 50 scenarios。
- [ ] **noise 正交化** — **P0-3**:在 `instruction_distance` plan 里钉 `noise=0` 单独重测,目前 noise 把 instruction_distance 信号完全盖住。7 档 instruction_distance × 10 seed = 70 scenarios。

### 7. 真实数据再跑一轮 (Validation Sweep)
- [ ] **跑通 `configs/context_length_sweep.json`** (P0-1, 2026-07-10 已建)— 40 scenarios,验证 4k-128k 的长度-召回曲线。**未跑**。
- [ ] 跑通 `configs/kv_fragmentation.json`(12 场景)— 验证 `fragment_count` 对 deepseek-chat 的影响。
- [ ] 跑通 `configs/task_complexity.json`(12 场景)— 验证多跳 prompt 模板的指令遵循度。
- [ ] 跑通 `configs/output_pressure.json`(8 场景)— 验证长输出下是否出现 context drift。**用 2378e74 的 error 列修复后重跑,旧 CSV 里 2 条空响应就是 API 失败而非模型失忆。**
- [ ] **重跑 `configs/instruction_distance.json`** (5a03eed 后)— 旧 CSV 数据陈旧(措辞 drift),需重跑以验证 grader 修复在 5x3x2x5 = 150 scenarios 上是否稳定 1.0。
- [ ] 综合 plan:把 `instruction_distance × output_pressure × task_complexity`(3×2×3 = 18 场景)作为 P0 综合验证。

### 8. 工程化 (Engineering)
- [x] **`--exclude <glob>` on `analyze`** (2026-07-10) — 修 §10 P-E 报告合并污染。`analyze_all` 支持 exclude_globs 参数,main.py 加 `--exclude` flag。
- [x] **`--model-override` / `--base-url-override` / `--api-key-override`** on `run` (2026-07-10) — 不改 .env 就能换 baseline 模型,出 Δaccuracy 矩阵。
- [x] **CSV `error` 列 + 错误标签** (2026-07-10, 2378e74) — `client.get_completion` 返回 `(content, error)`,`simulator` 写入 CSV,`report.analyze` 排除 error 行。`--exclude` 还能从 command line 跳过失败 CSV。
- [x] **CI smoke test 雏形** (2026-07-10) — `tests/test_context_length_sweep.py` 7 case 端到端跑 plan+assembler,无 API 调用。`tests/test_client_and_report.py` 7 case mock client 验证错误传递。**扩到 4 plan 全覆盖后再加 note**。
- [ ] **JSON Schema 校验** — 为 `plan.json` 写 pydantic / jsonschema,`from_json` 失败时给出明确错误。
- [ ] **YAML 支持** — todo 中已承诺,目前只支持 JSON;补 `pyyaml` + `from_yaml`。
- [ ] **并发 / 异步** — 当前串行跑 24 场景,加 `--workers` 用 `concurrent.futures.ThreadPoolExecutor` 加速(OpenAI 客户端线程安全)。
- [ ] **重试与超时** — 错误已透出,加 `tenacity` 重试:同一 scenario 失败 N 次后才写入 error 列。Short-term 不急:每个 plan seed=10 重试开销 = 4×10×重试次数。
- [ ] **TUI 进度** — 替换 `tqdm`,加入 ETA / 失败计数 / 当前 token 估算。

### 9. 文档与复现 (Docs)
- [ ] **方法论文档** — 在 `docs/methodology.md` 写清每个因子的定义、为何重要、引用(LEval / RULER / NeedleBench)。
- [ ] **结果解读指南** — `docs/interpreting_results.md`:相关性 r 的强度如何解读、什么时候噪声胜过主效应。
- [ ] **复现脚本** — 顶层 `scripts/reproduce_all.py`,一键顺序跑 4 个示例 plan + analyze。
- [ ] **更新 README** — 把已新增的"因子一览"和"报告章节"链接到 docs。

---

## 📈 实验优先级(2026-07-10 重排)

1. **P0 (立即, 决定后续一切)**: **跑 `context_length_sweep`** (§7, 14cf812 已建)→ 看 4k-128k 的 length-attention 曲线。**信号决定方法论**:
    - 4 档全 1.0 → needle 形态 / 位置 / filler 设计需重做(可能换 needle 长度 + 复杂结构)
    - 64k+ 开始掉 → 进入 P0-2 (recency 位置) 和 P0-3 (noise 正交化),scale 全部升到 ≥64k
    - 128k 才掉 → 边界效应,设计贴近 131072 的细档梯度
2. **P1 (本周)**: §10 P-A 修完(reasoner 截取)→ §4 评估器精细化(多针 / semantic upgrade)→ §5 报告增强(baseline 对比)→ 重跑 4 份 sweep 用新基础设施。
3. **P2 (后续)**: §6 因子扩展(semantic distractors / 多 needle 冲突)→ §8 工程化(并发 / TUI)→ §9 文档。

## 📝 备注
- 所有实验必须通过 `cache.json` 保证 Token 零浪费。
- 每个维度应提供对应的 Baseline 场景以便对比(§5 强制 baseline 对比将作为 P0)。
- 真实数据中 `noise` 效应远大于 `instruction_distance`,未来 plan 设计应把 `noise` 因子与目标因子正交化(固定 noise=0 再测距离)以避免共线性。
- **OpenAI gpt-4o 硬 context 上限 131072 token**——任何 plan 的 `total_tokens` 不得超过此值。`context_length_sweep.json` 用了 131072 顶到上限。
- **Grug 原则**:每个新 plan 在没看到 4k-16k 之外的真信号前,不要扩散到更多 dimension。先把"length → recall" 这条曲线测清楚,才有坐标轴。
