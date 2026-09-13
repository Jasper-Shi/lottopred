# 既定长期频率与固定五组规则：源码身份和精确模块映射

状态：外部设计材料；未登记、未实现、未运行模型或测试，不分配科学版本。本文不是授权或独立审查结论，也不决定下一实验一定启动。

实际作者：`/root/v13_test_exception_contract_map`。依据仅为原有概念草案以及下列固定源码/配置；没有按结果选择概率模型、参数、候选池或分组变种。

原草案：`/private/tmp/v13-successor-modular-design-before-v13-outcomes-20260913.md`，SHA-256 `687889c948d9351c012a4e291c905ee4d469d87a5d8e25f2ea34cc7d5edb4e89`，本次复核保持不变。原草案的既定身份是 V1 长期频率概率源 + Top-30 + 五个不相交的蛇形六数组。

## 读取边界与适用范围

只读核对位置：`/Users/jaspershi/CodexResearch/lottopred-v13-formal-historical-run-20260913`。固定源码检查点为 `182a4245bbaf0c444ef1e16c1b5beb120eec327f`。下列源码与该提交的 Git blob 字节逐项相等；这里只认证列出的源码，不宣称检查了运行中工作树的全局状态。

边界偏差明示：为核对项目协议，本次额外读取了 `docs/MODEL_PROTOCOL.md` 的前 200 行，其中夹有旧 V1/V12 已提交结果摘要。没有打开历史数据文件、结果报告文件或任何 V13 结果；没有调用项目 API、运行模型/模拟/测试、读取凭据、检查或干预现行 worker。上述旧摘要不用于任何选择或调整。因此本文不得称为“全局 outcome-blind”。此事已即时告知父代理；本文保持原草案的唯一候选不变。

## 1. 概率模块：实际既有实现

入口是 [`LongFrequencyModel.predict`](/Users/jaspershi/CodexResearch/lottopred-v13-formal-historical-run-20260913/src/lotto649/models/baselines.py:30)，类名 `LongFrequencyModel`，`name = "long_frequency"`，没有初始化参数、可训练状态或随机数调用。[`build_models`](/Users/jaspershi/CodexResearch/lottopred-v13-formal-historical-run-20260913/src/lotto649/models/factory.py:24) 直接构造 `LongFrequencyModel()`。

其签名为 `predict(history: list[Draw], target_date: date) -> dict[int, float]`。现有逻辑按下列具体顺序执行，不能把闭式说明偷偷替换成另一种浮点实现：

1. 调用 `number_feature_frame(history, target_date.weekday())`。
2. 固定 `strength = 250.0`，遍历该 DataFrame 的 49 行。
3. 每号取 `count_equiv = r.long_freq * len(history)`。
4. 取 `posterior = (count_equiv + strength * BASE_P) / (len(history) + strength)`。
5. 写入 `scores[int(r.number)] = posterior`，最后调用 `normalize_expected_six(scores)`。

[`features.py`](/Users/jaspershi/CodexResearch/lottopred-v13-formal-historical-run-20260913/src/lotto649/features.py:8) 定义 `BASE_P = 6 / 49`。`indicator_matrix` 以 NumPy 浮点零矩阵建立每期主号指示矩阵，逐号将相应位置设为 `1.0`；特别号不参与。每号 `long_freq = float(x.mean())`。概率模型使用全部传入的历史，不截成近期窗口，不按 RNG 日期切段，也不使用递减时间权重。

数学说明：对于已验证的 N 个历史开奖，若号码 i 出现 c_i 次，则理想实数计算为

`q_i = (c_i + 250 × 6/49) / (N + 250)`。

这等于以权重 `N/(N+250)` 使用历史频率、以 `250/(N+250)` 使用公平常数。合法每期六个主号时，`Σc_i = 6N`，所以理想实数下 `Σq_i = 6`，且 `0 < q_i < 1`。这是闭式 oracle，不是已经运行的预测；实际源码经过 `mean × N`、Pandas 行迭代和下述归一化，浮点最后几位不可由实数等式代替。

固定强度改变概率离公平常数的距离；在理想实数下它不改变按计数排序的顺序。故本草案的五组主要指标实质上检查这个长期频率排序和既定覆盖/分组；它不能单独验证 `250.0` 的概率校准优劣。Brier 的预定次要诊断才使用概率大小。本文不据此调整强度或改主要指标。

### 归一化、截断及有效输入

[`normalize_expected_six`](/Users/jaspershi/CodexResearch/lottopred-v13-formal-historical-run-20260913/src/lotto649/models/base.py:17) 精确为：

- 按号码 `1..49` 建立 `arr[n-1] = max(float(scores.get(n, 0.0)), 1e-9)`。
- `total = sum(arr)`，使用 Python 内置 `sum`。
- 按号码 `1..49` 输出 `min(0.999999, arr[n-1] * 6.0 / total)`；乘法先于除法。
- 上限截断后没有第二次归一化。不存在现成的概率总和容差或失败检查。

因此不能声称该工具对任意输入都严格保证总和六。极端分数触发上限时会丢失总质量；即使不截断也存在浮点求和误差。本候选必须保留现有计算顺序，另在登记中定义有限值、全键域、开区间和总和容差的验收及拒绝规则；不得为了满足声明而追加一遍归一化。本文不擅自选一个尚未登记的容差。

`Draw.__post_init__` 在 [`domain.py:14`](/Users/jaspershi/CodexResearch/lottopred-v13-formal-historical-run-20260913/src/lotto649/domain.py:14) 排序主号并检查六个、不重复、1..49；这不等于已认证历史权威、开奖连续性、数据可用时间或严格原生整数类型。未来输入边界必须完成这些验证。

### 未被概率公式使用、但源码仍会计算的内容

`number_feature_frame` 同时计算近期频率、EMA、gap、weekday、上一期出现、号码缩放和若干 lag 特征。它的默认 windows 为 `(10,25,50,100,250)`，EMA half-life 为 `35`。`LongFrequencyModel` 没有传配置覆盖值，也不读取这些特征来生成 posterior；target weekday 被写入无关列，target 日期不参与该概率公式。

这不意味着可以在未说明的情况下删除这些计算。直接复用既有入口时，其 NumPy/Pandas 依赖和全部调用路径仍属于执行行为。若以后为了缩小模块重写成纯计数代码，必须明示它是新的实现并预先证明所要求的数值等价，不能把数学同式当作原源码的逐字节或逐位等价。本次不提供该重写。

### 历史长度与 chronology 的实际责任

- `number_feature_frame` 仅对空历史抛出 `ValueError("history is empty")`；底层模块最小是 N=1。
- [`config.yaml:18`](/Users/jaspershi/CodexResearch/lottopred-v13-formal-historical-run-20260913/config.yaml:18) 的 `backtest.min_history_draws` 为 `300`；[`run_backtest:78–84`](/Users/jaspershi/CodexResearch/lottopred-v13-formal-historical-run-20260913/src/lotto649/backtest.py:78) 在外部筛选 `idx >= min_hist` 并传 `draws[:idx]`。该门槛属于回测调用器，不是模型强度或内部参数。
- [`make_prediction:19`](/Users/jaspershi/CodexResearch/lottopred-v13-formal-historical-run-20260913/src/lotto649/predictor.py:19) 没有 300 期检查，也不自行筛掉目标期或未来期。
- 所以“既有最少历史”有两层含义。若下一登记沿用历史诊断入口门槛，明确记录 `min_history_draws=300` 有现成配置依据；这仍是对原概念草案未明确项的新增登记决定，不能声称它早已冻结。禁止在 N 不足时改窗口或静默降级。
- 新协调层须传入严格早于 t 且在预测冻结时已经可用的完整合格历史前缀；模型自身不会保护这个条件。必须固定历史权威、起点、排序/唯一性、可用时间和 cutoff。目标日期本身不能替代输入验证。

## 2. 选择模块：唯一固定 Top-30 / 五列蛇形映射

输入是已通过合同检查的完整 `p_i`，i 为全部整数 `1..49`。复用 [`rank_numbers`](/Users/jaspershi/CodexResearch/lottopred-v13-formal-historical-run-20260913/src/lotto649/optimizer.py:7) 的精确键 `(-probabilities[n], n)`：先按实际浮点值降序，同值才按号码升序。不引入 jitter、近似并列容差、日期种子或随机打破并列。

设完整排名为 `r_1,...,r_49`。保存该排名和 `r_1..r_6`、`r_1..r_12`、`r_1..r_18`，候选池永久为 `r_1..r_30`。行从上至下、列从左至右均从 1 开始，前 30 个排名位置的矩阵精确为：

| 行 | 列1 | 列2 | 列3 | 列4 | 列5 |
|---|---:|---:|---:|---:|---:|
| 1 | 1 | 2 | 3 | 4 | 5 |
| 2 | 10 | 9 | 8 | 7 | 6 |
| 3 | 11 | 12 | 13 | 14 | 15 |
| 4 | 20 | 19 | 18 | 17 | 16 |
| 5 | 21 | 22 | 23 | 24 | 25 |
| 6 | 30 | 29 | 28 | 27 | 26 |

列身份永久为 `G1..G5`。每列取真实号码 r 对应位置，而不是把表内排名位置当作实际预测号码：

- G1 的排名位置：`(1,10,11,20,21,30)`。
- G2 的排名位置：`(2,9,12,19,22,29)`。
- G3 的排名位置：`(3,8,13,18,23,28)`。
- G4 的排名位置：`(4,7,14,17,24,27)`。
- G5 的排名位置：`(5,6,15,16,25,26)`。

五组分别是六元素集合。建议快照组内按实际号码升序序列化，同时单独保留上述不可变列身份和完整排名；组内表示排序不会改变集合。不得按事后命中数重排组身份，也不得以概率和重新排五组来假装第一个是“最可能全中组”。

所有排名位置 1..30 恰出现一次，因此五组互异、任意两组交集为空、覆盖恰好 30 个号码。每列排名位置之和都是 93；这只是构造性质，并不证明组概率或期望命中相等，也不是一个关于真实中奖号码之和的约束。

旧 [`select_combination`](/Users/jaspershi/CodexResearch/lottopred-v13-formal-historical-run-20260913/src/lotto649/optimizer.py:11) 在默认前 12 个号码中枚举六数组，最大化独立 log-score，只返回一组。它不是本次五组选择模块。`config.yaml` 的 `prediction.candidate_pool_size=12`、`final_size=6` 不能默默驱动新 Top-30 规则；旧 `make_prediction`/`Prediction.final_combination` 也不能直接装下五组合同。

模块之间的接口只传冻结的完整概率与排名及其版本/cutoff/时间身份。每组的 `Σp_i` 是边际概率给出的期望命中数，不能称为全中概率；本方案不产生联合概率，不按 `∏p_i` 宣称“最可能中奖”。

五组均须先冻结后揭晓。同一期主指标是五组命中的最大值，仍只有一个开奖观察。指定一组为旧式 `Final-6`、或将任何五组之一首次 6/6 纳入项目停止触发器，是尚需明确登记的输出/停止合同，不能在见到结果后把获胜组改名为原来唯一的 Final-6。

## 3. 只供将来独立实现验证的合成/数学 fixtures

以下只是在纸面上给出的 oracle，没有构造项目对象、读取真值、执行模型或生成预测文件。

1. 空输入边界：既有底层模型应在特征入口拒绝空 history。若登记沿用 N>=300 的运行门槛，则 N=299 在协调层拒绝、N=300 仅通过长度条件；其他完整性条件仍须独立满足。底层 N=1 fixture 不等于正式运行允许只用一期。
2. 均衡计数：用 49 个循环六元素集合组成一个完全合成周期，每个号码在周期内出现六次；重复七个周期得到 N=343、每号 c_i=42。赋予严格递增的虚构日期且 target 在其后。理想 posterior 全为 6/49；既有浮点流水线应使 49 个输出彼此相等（与实数 6/49 的最后几位须按登记数值规则比较），完整排名为 1..49，选择器得到上表的精确排名位置分配。这里的数字是测试构造，绝非历史结果或购票建议。
3. 单期平滑公式：纯数学 N=1、任意六元素集合 A 时，A 中号码 q=1549/12299，其余 q=1500/12299；总和六，前者大于后者。它检验固定强度 250 的推导，不应作为绕过正式最少历史门槛的执行案例。
4. 一步正常更新：均衡 N=343 合成 fixture 后新增一个合成六元素集合 A，则 N=344，A 中 c=43、其余 c=42；理想 q 分别为 `3607/29106` 和 `3558/29106`。这是正常已可见历史更新，不是以目标答案修正同一期输出。既有 mean×N 浮点路径与该实数 oracle 的差异须事前定义容差，不能根据实际结果调整。
5. 选择器独立 fixture：令号码 i 的理想输入为 `p_i=6(50-i)/1225`，i=1..49。它严格递减、全在 (0,1)、和六，故排名为 1..49；预期组位置就是上表。这个 fixture 只用于选择模块，不声称该向量来自长期频率模型。等概率 fixture 则单独验证升序并列规则。
6. 标签映射 fixture：对上一条严格不同概率使用任意事前写定的标签双射 π，令 π(i) 继承 p_i，则新排名为 π(1)..π(49)，各组是原排名位置集合经 π 映射。对于等概率输入，预期仍按新标签数值升序；不能误把 tie-breaking 声称为标签置换等变。
7. 合同拒绝 fixture：缺失键、多余键、非整数/布尔键、非有限值、0/1 或越界值、总质量不符，均应在新模块入口按事前明确规则拒绝；不借助旧归一化函数的 `scores.get` 默认值修补。概率相同但字典插入顺序不同，必须产生相同排名和列身份。
8. 归一化边界 oracle：给旧工具极度集中的非模型原始 scores，可令缩放后的最大值超过 0.999999，触发 cap 后总和不再为六。该 fixture 证明“cap 后无重归一化”的源码事实，不证明正常长期频率输入会出现该情况。新实验不能用该 fixture 为由改动既有公式而隐去版本差异。

## 4. 固定源码身份

下表中全部工作树文件已与固定提交的 blob 字节一致比较，Git 文件模式均为 `100644`。文件 SHA 只是源码身份；不是已注册新 runtime closure。

| 路径 | Git blob SHA-1 | 文件 SHA-256 |
|---|---|---|
| src/lotto649/models/baselines.py | 4f4817a5f7895e325c1adebbcd18d933117b53fd | 76f9050a13bde44d51584397ecd6acb358f320e1617ef329b70bd6a22d23e28a |
| src/lotto649/models/base.py | 31a01009c50bdeb3b73b7a9d9f289a23a6e1deb6 | e2f0c90c376ea6063b906bcca042e8903b351a1ed4b76e9d83e17be3bcf166ec |
| src/lotto649/features.py | a735fd3092a6a3de226823f0491b437e1e69cada | b7bc67b9038b2e3d78230c3087c3ac4e3f17751aeab678574f3601af00671979 |
| src/lotto649/domain.py | 7465f79ca3548ca9c61ba173220b04dadec5d6b9 | fbcb22747ae361767df070c6e50af49fda1aa190b72fd39894afa1c879a50b7a |
| src/lotto649/optimizer.py | 5a7dfeacd16e7f34e19ceda361ae5fc57d3873ac | f5bda2a8ee8cd19c7b719a8f3344a7e4ca76def75971d5e8fe49489189abd1a4 |
| src/lotto649/models/factory.py | e86691165fb3a790e01d69e89fea3a208378e59d | 9dc00bb860ee5e786116d8d2ffa767de932f96419e18d81753bb438f975260b7 |
| src/lotto649/backtest.py | 5ab48a163f378c6503b0eac1dfd0a38de8b59e65 | 3d188c18b520199d86a5e1063e54f1c0ef0896e28cc55dea61c056698974bba8 |
| src/lotto649/predictor.py | adec41c55b7b690cc0941c66b0d558e8f1f8ad4c | f14223a213af0bbac668300f9d8ae6b67b3a61ce5f0294985e98ab4e8d87d721 |
| src/lotto649/models/__init__.py | e69de29bb2d1d6434b8b29ae775ad8c2e48c5391 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| src/lotto649/__init__.py | 3dc1f76bc69e3f559bee6253b24fc93acee9e1f9 | 91447944015cec709e8aa7655f7e9d64e1e4508e7023a57fe3746911c0fc6fed |
| config.yaml | 228297cb4253f4f05a85373a7672f36c2b1f739f | d53a9a9eed5ab434b021472135d6aed65c2c052339e0dfb88f8c00d46c0d8931 |
| pyproject.toml | b8dd0ef183ebae29c43792414667a181b14ed46e | 0a95b02b8852c33727100165da4696ede65cd6acedc1e1fbc5b65e091ad76d0e |
| requirements/v12-historical.txt | bd577c57cbcabac1f4409665547ff36015f378c8 | a0dfeac17ad7e1c41dffe4b41b4810156fb028f879d312430bfc517672a570c6 |

额外只读追踪的 `live.py` 与 `evaluation.py` 同样字节匹配固定提交，但不属于五组选择器：前者只是确认既有入口委托 `make_prediction`；后者现有 Brier 按每期 49 号平均。没有把这些源码引到新授权执行链。

`pyproject.toml` 当前只给 Python>=3.11、NumPy/Pandas 的范围约束，不足以固定精确数值行为。仓库另有 `requirements/v12-historical.txt` 固定 NumPy 2.3.5、Pandas 2.3.3 等依赖，但其存在不自动把 V12/V13 的 runtime 权威授予新实验。必须在未来登记里明确所采用的解释器、依赖和完整 import/runtime closure；本次没有检查实际解释器/安装环境或执行任何 import。

## 5. 在登记前仍须闭合的事项

1. 明确完整历史权威/起点、可用时间定义、N>=300 是否沿用、非法/缺失输入及日历失败处理。不能让模型读取目标答案以填补缺失。
2. 定义保留既有浮点流水线的具体 runtime、概率质量容差和 fail-closed 规则。这个选择只能基于源码/合成数值论证，不能基于任何真实结果。
3. 明确新五组快照 schema、固定组 ID、Final-6 的兼容含义，以及首次任一组 6/6 的冻结/审计动作如何与原项目单组完成条件衔接。不得事后选择命中组充当预先指定组。
4. 由独立数学规范负责主零分布、固定队列/缺失/提前停止、次要对照和多重比较。本文没有改写原草案的主要指标、五组结构或观察规模。

除这些必须明示的未定合同外，没有提出概率模型替换、参数网格、其他候选池、其他分组法、联合模型、历史重跑或新版本号。本文只把原候选从名称映射到可审计源码和确定的排名位置规则。

实际排他新增写入时间（UTC）：2026-09-13T19:25:39.342651+00:00
