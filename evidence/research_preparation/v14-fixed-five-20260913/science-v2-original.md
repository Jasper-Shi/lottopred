# 长期频率排序与五个固定六数组：完整科学合同整合草案

**外部设计稿。未登记、未分配科学版本、未实现新实验、未获运行授权、没有本候选预测或结果。** 这份文档不创建封印、commit、claim、lease、worker、live 或邮件权限，也不借用任何旧版本权限。科学合同集中于唯一已指定候选；操作注册、实现及独立验收仍是之后的工作。

## v2 变更与待验收状态

本 v2 由 `/root` 整合；完整 v1 保持原字节，SHA-256 `dc3e0c8d2510d982e06544d57d5a975acc37d441657365bdc2ff30b06ce53153`。依据独立整合审查 `f14928c3b2b04e354fdf072a823d5b36f773a9fdad89f8b5c60a68831ea8eaac`，只明确解析基准的限定协议修订，以及按持久化阶段划分互斥失败状态。未改变概率算法、250强度、五组/排序、627目标、主要指标、零分布、阈值或统计流程。此 v2 仍需新的独立审查；没有声明正式注册、实现、合成运行或历史执行完成。

## 作者、来源和时间界限

本稿写作者：`/root/v13_test_exception_contract_map`，本轮贡献标识 `successor-complete-science-integration-20260913`。共同实质贡献者：`/root`，负责本轮五组与 Goal 衔接、数据/数值验收、完整评分及状态决定；这些决定由父代理明确声明基于源码与数学。原概念作者 `/root/multi_group_research_design_check`、源码映射作者 `/root/v13_test_exception_contract_map`、数学合同作者 `/root/v13_exception_spec_review` 的材料按下述摘要继承。独立审查者 `/root/five_group_independent_math_review` 的报告是已存在输入的审查，不是对本稿的提前验收。

本稿明确写于 V13 结果之后；没有将这一时点之后才明确的条款追溯为 V13 揭晓前已注册。本文写作者此前读取源码映射时，曾在 `docs/MODEL_PROTOCOL.md` 前 200 行接触旧 V1/V12 已提交摘要；偏差已经披露。数学稿作者也披露其先前结果审查角色。因此没有全局盲态声明。原候选、强度、Top-30、蛇形五组和主要指标均维持原备忘的唯一选择，本轮不依据结果更换它们。

本次只读取四份设计/审查材料和固定 R13 登记中的数据、日期摘要与 runtime 元数据，没有读取历史载荷、目标答案、报告载荷或新的 V13 结果，没有模型/模拟/测试/项目 API/worker 执行。登记元数据的读取不等于重新核验真实历史。

固定输入（原件保持不变）：

| 材料 | SHA-256 |
|---|---|
| 原概念 `/private/tmp/v13-successor-modular-design-before-v13-outcomes-20260913.md` | 687889c948d9351c012a4e291c905ee4d469d87a5d8e25f2ea34cc7d5edb4e89 |
| 源码映射 `/private/tmp/v13-successor-exact-modules-source-map-20260913.md` | 986b238a6d7424ff02089a8a8576bf00ca0887fd5f9eafc09f805747f95a2fda |
| 数学合同 `/private/tmp/v13-successor-five-group-math-contract-draft-20260913.md` | 65144487d26e4f889759e9b8d61304a8983b04361ff005b3524f9b09a8ac3c8c |
| 独立数学/科学审查 `/private/tmp/five-group-independent-science-math-review-20260913.md` | ee622a61a5a5cbfbf7733a369905e26ccb960307cd8f3b54f62765a3864c0176 |

独立输入审查确认闭式数学，但列出三个 major 合同缺项。本稿用父代理的明示决定分别闭合五组身份、输入/数值身份、完整报告/终态；这不自动意味着本稿也通过独立审查。新增评分及数值边界的合成验证尚未执行。

## 1. 唯一假设与解释范围

唯一概率源是既有 V1 `LongFrequencyModel`。新增科学对象只是“这个既定排序 + Top-30 + 固定五组结构 + 每期最大命中数”的完整系统。它不是新发现的号码概率信号、联合概率模型或已经更强的 V1。

唯一主要问题：固定 627 个 consumed historical diagnostic 目标上，完整系统的每期最大命中 M 的均值，是否高于同为五组、各六个号码、覆盖30个且零重叠的公平零分布均值？唯一主要检验是完整627期的精确单侧尾概率。314/313、概率评分、校准、组间安排、单组和年度结果全部是预定描述，不能替换主要指标。

在理想实数下，固定强度250不改变长期计数的排序，因此主要指标不能验证这一强度的概率校准。M 的改善可以来自更多普通低阶命中，不能转换成“6/6 概率提高”的结论。相同日期被其他版本评估过，不会成为新增独立开奖或 untouched blind confirmation。

## 2. 固定历史与目标身份

只继承 R13 seal 的明确元数据字段，不继承其科学公式、候选 RNG 起点、burn-in、V13 producer 列表、五项比较校正、十项 gates、版本、core、lease 或运行权限。

元数据源：固定源码检查点 `182a4245bbaf0c444ef1e16c1b5beb120eec327f` 中 `evidence/research_registrations/v13-post-rng-main-set-overlap-v1.json`，文件 SHA-256 `36543acd288418c0cfbf561024b2ca60fa483b8aae6a6988026b76dde861e759`，选择范围为 `scientific_contract.scope.history_identity`、日期 scope 摘要，以及明确下列历史范围字段。

- 仓库 `Jasper-Shi/lottopred`，固定历史权威 `main` 提交 `4a617f2c1575a165b42878600753a01ddf2ced03`。
- `PublishedHistory` 总数4,444，起点1982-06-12，截止2026-08-22；后续 append 不接受为本实验输入。
- 固定评分范围仅2020–2025共627期，按日期升序，前314期与后313期；所有2026主号不进入任何目标可见前缀或评分。
- 概率训练窗口为这个权威历史中严格早于每个目标 t 的**全部完整前缀**，起点1982-06-12，N>=300。没有后2019截断、滚动窗口或仅最近300期的含义。
- 输入须为已验证的六个不同原生整数主号，域1..49，排除 bool；日期严格有序、唯一、符合固定权威，完整性/连续性通过操作数据验证。特别号只保留身份，不进入概率特征或命中评分。
- 模型只接收 prior prefix 和目标日期；当期/未来主号不可进入特征、参数、排序、候选池、分组或选择。冻结完成后才揭晓当期。固定权威是2026年已修正历史身份，不声称其修正文件在2020年已提交；这里是合法程序顺序的已消费历史诊断。

有序目标身份固定如下，摘要编码为规范ISO日期按时间升序、LF连接、末尾恰好一个LF、UTF-8。本文不展开目标答案，不从历史文件重新构造日期；将来授权后的数据 seam 必须核对日期总数与摘要相等，禁止为了凑数改变目标。

| scope | n | 首目标 | 末目标 | target_dates_sha256 |
|---|---:|---|---|---|
| aggregate | 627 | 2020-01-01 | 2025-12-31 | c339733dccc04c3ac25aca15ce991c31421ba35580488e7acadbea5672705782 |
| first_half | 314 | 2020-01-01 | 2022-12-31 | c3bea21f775ce8077d25b255ae18a3701b08b22f2bf39c812ce40e78f6edc2e5 |
| second_half | 313 | 2023-01-04 | 2025-12-31 | 32f924f82aa85e2be7440c66cf7133ab1b16669ede77e7230efef8d7e473ee7b |

完整固定历史对象身份从上述 seal 原样复制为设计元数据，未读取任何对象载荷：

```json
{
  "branch": "main",
  "commit": "4a617f2c1575a165b42878600753a01ddf2ced03",
  "immutable_objects": {
    "base": {
      "bytes": 136540,
      "git_blob": "1957e6935a2a14f7a5326992067b75fe006178c1",
      "rows_sha256": "58988bbb130be2142bc5a2b20df571cc458eabe66cd873773f55ca1dbfae8874",
      "sha256": "1e1bb768877d3f1b3b901a8cb897b6f439ff80f675c57e786cb54ff1179ac8ad"
    },
    "registry": {
      "bytes": 1170,
      "genesis_commit": "a6857d6b4e6e532062f484bcce4466f76ba4327b",
      "git_blob": "e95aeaaa28d5c1b7e5fb636d0fc4a3c26ff31017",
      "head_sha256": "22bcfe219c091dbcdb751ef7a2d9d5251f3040770de6e2e825ac5c64fc69c63d",
      "sha256": "42a9df8ef861a5fad6e1d7e7639d3d9317e519c0e83e96d7b1148527215afb72"
    },
    "seal": {
      "bytes": 4586,
      "commit": "b3056cd1772f8e992e27a9eb87e5037eb15e2b79",
      "git_blob": "23c05e7d2c1344f77085b228bfc919e88e3c4af3",
      "sha256": "80397752105b567d6a8bdd3673b12ffa470a12efbd792719a4f6c89ef391f6fd"
    },
    "suffix": {
      "bytes": 3079,
      "commit": "0b476b6de1f6bed1382c29187fd5cdaa4f70c153",
      "event_count": 2,
      "evidence_commit": "60dbd42a502850091508491f9011f9a08acf894f",
      "git_blob": "3fa0319cc9d98fc17c49d4917e222d2da10aef07",
      "head_sha256": "3022b98fefbe3dbbc80423574319c169edcc845bf2218152c6abe18d0be27475",
      "sha256": "b91be6a4057648abd86dc0e6fc5d762fc4cd9b222519c147d635703cc550a803"
    }
  },
  "published_history": {
    "base_draw_count": 4442,
    "base_history_through": "2026-08-15",
    "base_seal_path": "evidence/data_integrity/DI-2026-08-20-registered-history/seal.json",
    "draw_count": 4444,
    "history_start": "1982-06-12",
    "history_through": "2026-08-22",
    "incident_id": "DI-2026-08-20-registered-history",
    "kind": "PublishedHistory",
    "pin_registry_path": "evidence/operational_history/DI-2026-08-20-registered-history/pin-registry.jsonl",
    "suffix_event_count": 2
  },
  "read_seam": "lotto649.operational_history.load_published_history",
  "repository": "Jasper-Shi/lottopred"
}
```

## 3. 概率模块与新数值验收

精确既有入口：`src/lotto649/models/baselines.py:30–41` 的 `LongFrequencyModel.predict`，不调用包含其他模型的 factory 来生成额外 producer。源码映射固定点为上述 M 提交；核心相关文件身份如下。

| 源码 | SHA-256 |
|---|---|
| models/baselines.py | 76f9050a13bde44d51584397ecd6acb358f320e1617ef329b70bd6a22d23e28a |
| models/base.py | e2f0c90c376ea6063b906bcca042e8903b351a1ed4b76e9d83e17be3bcf166ec |
| features.py | b7bc67b9038b2e3d78230c3087c3ac4e3f17751aeab678574f3601af00671979 |
| domain.py | fbcb22747ae361767df070c6e50af49fda1aa190b72fd39894afa1c879a50b7a |
| optimizer.py | f5bda2a8ee8cd19c7b719a8f3344a7e4ca76def75971d5e8fe49489189abd1a4 |

这些路径以 `src/lotto649/` 为共同前缀；完整 Git blob 和包初始化模块身份在源映射稿中已列明。这张表不是新实验完整 runtime closure 的替代品。

保留实际浮点流水线：`number_feature_frame(history,target_date.weekday())` 生成每号 NumPy 指示列均值 `float(x.mean())`；按 DataFrame `iterrows` 顺序读取 `r.long_freq`，先乘N得到 `count_equiv`，再以 `(count_equiv + 250.0 * BASE_P)/(N+250.0)` 得到 posterior，其中 `BASE_P=6/49`。依次调用既有 `normalize_expected_six`：

1. 对1..49按升序取 `a_i=max(float(scores.get(i,0.0)),1e-9)`。
2. `total=sum(a_i)` 使用 Python 内置sum。
3. `p_i=min(0.999999,a_i*6.0/total)`，保持先乘后除。

不追加归一化，不把 `mean*N` 换成直接计数实现，不改 clipping，也不删除特征函数内虽未用于 posterior 的 EMA/gap/weekday 等计算。特征函数默认 windows `(10,25,50,100,250)`、EMA half-life35 保留实际源码调用行为；它们不成为长期频率公式的有效预测特征。

理想实数 oracle 为 `q_i=(c_i+250×6/49)/(N+250)`，合法输入下和六。它只用于合成/数学对照，不替代真实源码浮点顺序。

新增输出验收在读取目标真值之前进行：

- key 集合必须恰为原生 `int` 的1..49，每个 `type(k) is int`，不接受bool或额外/缺失键。
- 每值必须为原生 Python float，有限且严格 `0<p_i<1`。
- 按号码升序检查 `abs(math.fsum(p_i for i in 1..49)-6.0)<=1e-12`。
- 任何失败立即进入永久停止分支；不修补、截断额外值、替换公平概率、降低最少历史或重新预测本期。

既有归一化 cap 后不会重新归一化，所以不能先假定以上门槛对所有输入天然成立。此精确 `1e-12` 门槛是父代理基于源码/数学作出的新设计决定，仍必须通过独立合成/数学边界验证后才允许实现验收；本稿不声称已验证成功。

## 4. 精确 runtime 的独立冻结要求

选用 CPython3.12.11、little-endian、arm64、IEEE754 binary64（radix2、mantissa53、maxexp1024），固定平台及27个发行包的确切身份如下。requirements 路径为 `requirements/v12-historical.txt`，SHA-256 `a0dfeac17ad7e1c41dffe4b41b4810156fb028f879d312430bfc517672a570c6`。

```json
{
  "byteorder": "little",
  "dependency_manifest_sha256": "a0dfeac17ad7e1c41dffe4b41b4810156fb028f879d312430bfc517672a570c6",
  "implementation": "cpython",
  "installed_distributions": {
    "beautifulsoup4": "4.13.5",
    "certifi": "2025.11.12",
    "charset-normalizer": "3.4.4",
    "idna": "3.11",
    "iniconfig": "2.3.0",
    "joblib": "1.5.2",
    "numpy": "2.3.5",
    "packaging": "26.3",
    "pandas": "2.3.3",
    "pip": "25.1.1",
    "pluggy": "1.6.0",
    "pygments": "2.21.0",
    "pypdf": "6.16.1",
    "pytest": "9.1.1",
    "python-dateutil": "2.9.0.post0",
    "pytz": "2025.2",
    "pyyaml": "6.0.3",
    "requests": "2.32.5",
    "ruff": "0.16.6",
    "scikit-learn": "1.7.2",
    "scipy": "1.16.3",
    "six": "1.17.0",
    "soupsieve": "2.5",
    "threadpoolctl": "3.5.0",
    "typing-extensions": "4.15.0",
    "tzdata": "2025.2",
    "urllib3": "2.5.0"
  },
  "machine": "arm64",
  "platform": "macOS-26.5.2-arm64-arm-64bit",
  "python_version": "3.12.11"
}
```

这一表从旧 seal 只提取数值/依赖身份；新实验须重新冻结自己的完整源码、包初始化、模块来源和本地运行闭包，独立验证正常入口与隔离进程安全、CPython/发行包无额外或重复、浮点和math oracle、每个冻结边界源身份不漂移。旧版本 runtime pass、core SHA、授权对象或外部helper均不成为新版本的授权。不得在正式单次执行中安装、修补或动态选择包/根路径。

本文没有给未来核心、闭包或执行提交伪造 SHA；这些只能在真实实现和独立审查后产生。没有执行本机环境检查或 import。

## 5. 选择模块与五组唯一身份

完整排序固定为 `sorted(probabilities,key=lambda i:(-probabilities[i],i))`，以实际浮点值判等。同值才按号码升序，无jitter、epsilon-tie、日期种子或随机选号。令排名为r1..r49；Top-6/12/18为前6/12/18号，候选池永久为前30号。

五列身份永久固定，元素是下面排名位置所指的真实号码。每组内部按号码升序保存，列ID保持不变，五组不按后验命中或概率和重排。

| 固定ID | 排名位置（不是推荐号码） |
|---|---|
| G1 | 1,10,11,20,21,30 |
| G2 | 2,9,12,19,22,29 |
| G3 | 3,8,13,18,23,28 |
| G4 | 4,7,14,17,24,27 |
| G5 | 5,6,15,16,25,26 |

等价于六行五列、第一行左至右、第二行右至左，逐行交替。恰好五组，每组六个不同号码，全部组对交集为空，合并恰为Top-30。每列排名位置和93只是构造性质，不等于概率和或6/6概率相等。

**捕获资格只属于预先冻结的 G1–G5。** 若保留兼容字段 `final_combination`，它永远只别名G1；旧字段的 `final_6_hits` 永远只别名H1。不得在结果出现后把其他获胜组填入旧字段。Top-6只是排名诊断，不是第六张ticket，不参与capture；Top-12/18全覆盖也不参与capture。没有另一个独立V1/随机实选组隐含捕获资格。

任一固定G第一次精确命中六个主号时，在进入下一期预测之前停止。必须保留并完成当期已冻结的五组以及全部预定概率/排名评分，报告具体固定组ID。其最终表述只能是“预先冻结五组之一的历史6/6”，不冒充原单组Final-6证据。这是父代理依据用户明确多组意图作出的范围决定，正式登记须明确更新该实验与Goal完成协议的衔接。

这里没有六元素集合上的联合概率；不得称任何G为联合最可能，不把Σp或∏p当作经过校准的全中概率。也不调用旧 `select_combination` 的Top-12单组枚举。

## 6. 两个解析置换对照与 V1/公平基准边界

1. **主对照：全球标签均匀置换。** 对固定五组施加同一个1..49均匀标签置换，保留五组大小、30号覆盖数和全部零重叠结构。使用其精确解析零分布，不实际生成随机票，不以多个随机种子的最佳值比较。
2. **次要对照：同一Top-30池内均匀置换。** 保留实际冻结的30号集合，再均匀重分为同样五组；使用给定q的解析条件分布。它只诊断同池安排，不选择新的分组。

公平常数p0=6.0/49.0用于Brier、binary Log Loss及校准参考；公平Top-K单期命中理论为Hypergeometric(49,K,6)，均值6K/49。每个固定G的公平平均命中36/49只作单组描述，不能取代五组主要公平均值。

既有V1长期频率就是本候选的概率来源，不能给它换名称后声称独立新V1对照。本文不重新生成V1 ensemble或 `RandomBaseline` 的经验票、不借用旧预测重组为新证据、不导入额外经验producer，也不把五组对一组的差称为预测优势。

**R-next 必须同时登记的限定协议修订：** 对本唯一五组历史诊断，`docs/MODEL_PROTOCOL.md` 中保留随机模型的基准要求及 `docs/RESEARCH_ROADMAP.md` 中相应公平/V1/负对照文字，须在同一新注册变更中明确以下范围，并接受独立 Spec 审查：

- 随机比较采用上述两个均匀标签置换的**精确解析积分**及公平概率模型 p0=6/49。它保留固定组数、覆盖和全部重叠结构，没有抽取额外随机票或挑选随机种子。这是本实验明确登记的随机基准形式。
- 没有执行经验 `RandomBaseline`、独立 V1 ensemble 或端到端扰动历史的经验实验；不得把解析对照标成这些程序的实测运行或以此声称这些路径通过了经验负控检验。输入、冻结和评分管线另由完整合成故障测试及正式后审计验证，解析正确性不替代它们。
- V1 联系仅为原有 `LongFrequencyModel` 概率源及其固定源码/数值身份；既有 V1 源码等价检查不是独立对照。没有“优于未运行 V1 ensemble”的结论，也没有把五组和 V1 一组机会数不匹配的比较当优势。
- 仅在这项新登记内以此明确形式履行基准用途；不删除仓库通用基准要求，也不改变旧版本实验。新的协议文字、科学合同与全部报告须一致。若独立审查仍认为不足，必须在看新候选结果前关闭该设计缺口，不能运行后补规则或追加经验 producer。

这是作者现已明确选择的登记条款，而不是声称现有仓库协议已经修改或注册审查已经通过。

## 7. 每期评分与严格顺序

每期t必须按下列单向顺序：认证源/runtime/输入前缀 → 计算一次概率 → 验收全49号概率 → 完整排名和G1..G5 → 生成真实运行UTC时间及全部预测元数据 → 不可变冻结并认证摘要 → 揭晓当期固定权威的真实主号/特别号 → 完成当期全部评分 → 若capture或故障停止，否则进入下一期。

预测入口不接受当期答案。不能先揭晓再补写冻结时间。历史目标日期、模拟训练截止与真实生成/冻结UTC时间分别记录，不把目标当天午夜伪称为实际计算时间。冻结方案与 hash-chain/源核对属于新操作注册，本文不创建它们。

记主号集合Y，五组H_j=|G_j∩Y|，M=max(H1..H5)，q=|Top30∩Y|=ΣH_j，d=M−μ_q。对每个G保存H及匹配号码；对Top-K保存命中数和匹配号码。全部真实主号的平均排名为 `math.fsum(float(rank[i]) for i in sorted(Y))/6.0`。

**Brier（按数学稿保持不变）：** 标签i升序，y_i=float(i in Y)，`B=math.fsum((p_i-y_i)**2 for i in 1..49)/49.0`。公平B0按同式使用p0计算，先形成每期B−B0，再按日期汇总。

**Binary Log Loss（本稿新增固定算术）：** 严格有限(0,1)验收通过后，按标签升序计算 `loss_i=-(y_i*math.log(p_i)+(1.0-y_i)*math.log(1.0-p_i))`，`L=math.fsum(loss_i for i in 1..49)/49.0`。公平L0按完全同式用p0计算。没有eps截断、log1p替换、概率修补或联合六数组score。这是新候选结果之前固定的评分算术，不声称与旧 `evaluation.binary_log_loss` 的截断/逐次累加逐位相同。应由独立合成/math fixtures验证；尚未测试。

**Calibration固定10箱：** 边界为Python float字面量 `[0.0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0]`。前9箱左闭右开，末箱[0.9,1.0]；有效p不含0或1。用明确区间比较，不按乘10后取整替代边界。每期及各描述scope分别列10行，保存箱内号码观察数、`math.fsum(p)`、实际主号指示和、平均p、实测频率及频率−平均p。合并scope时按日期然后号码升序扁平化49×n项，再用fsum；空箱计数/和为0，平均/频率/gap为null。所有49号贡献是同一期内相关观察，不能据箱样本量宣称独立检验。公平常数亦按同边界/公式列参考表。不合箱、不换边界、不拟合校准器，不添加校准显著性或额外通过门槛。

## 8. 每期不可省略的输出

预测快照须包含：目标ordinal/日期；历史权威及对象身份；严格训练截止日期、前缀期数和前缀摘要；原概率源身份、新实验/概率/选择/特征版本字段（本稿不填尚未分配的新版本）；完整源码/配置/Git commit/runtime身份；实际生成和冻结UTC时间；不可变快照路径/字节数/SHA及ledger关系。

科学输出须包含：号码1..49的Python float概率及各自 `float.hex()`；完整49排名；Top-6/12/18；Top-30池；按ID顺序G1..G5且每组号码升序；G1别名的旧字段；明确仅G1..G5有capture资格。不能只保存排名前列或只保存最终命中组。

揭晓后的独立评分记录须绑定快照SHA，保留权威实际主号六个、特别号原始身份（其缺失若违反权威验证则是完整性故障，而非任意补值），实际揭晓/评分UTC时间，全部H1..H5/匹配号、M、q、d、Top-K命中、平均实际排名、B/B0/B−B0、L/L0/L−L0、10箱校准计数/统计、capture固定组ID列表、当期审计状态。特别号绝不增加任何主号命中。

全体并列组全部保留。由于五组不相交且实际只有六号，数学上最多一个G可6/6，但实现仍以固定ID列表保存事实并验证不变量；不得靠选择一个组丢掉其他已冻结组证据。

## 9. 公平最大命中的精确零分布

H0要求给定全部开奖前信息后，下期Y在全部D=C(49,6)=13,983,816个六元素集合上均匀。五组必须对该过去信息可测；组间不是独立事件。

令 A_m(z)=Σ_(h=0)^m C(6,h)z^h，F_m=[z^6](1+z)^19 A_m(z)^5，F_(-1)=0；w_m=F_m−F_(m−1)。

| m | w_m |
|---:|---:|
| 0 | 27132 |
| 1 | 5093064 |
| 2 | 7564500 |
| 3 | 1230100 |
| 4 | 67725 |
| 5 | 1290 |
| 6 | 5 |

Σw=D，Σm w=24,189,744，Σm²w=47,537,994；μ=24,189,744/D=43,822/25,333≈1.7298385505072436，Var(M)=24,039,506,739/59,042,001,788。尾权重M≥3/4/5/6分别为1,299,120 /69,020 /1,295 /5（均除D）。

只用固定整数多项式/计数DP或经独立证明的等价整数实现，不用蒙特卡洛近似或随机种子挑结果。已存在独立审查验证的是这份闭式数学；未来实现仍须有自己的合成oracle验收。

同池对照给定q：`c(q,m)=[z^q]A_m(z)^5−[z^q]A_(m−1)(z)^5`，m=0的第二项按0，q=0时c(0,0)=1。分母C(30,q)，μ_q=Σm c(q,m)/C(30,q)。

| q | 分母 | c(q,0)..c(q,6) | μ_q |
|---:|---:|---|---|
| 0 | 1 | 1,0,0,0,0,0,0 | 0 |
| 1 | 30 | 0,30,0,0,0,0,0 | 1 |
| 2 | 435 | 0,360,75,0,0,0,0 | 34/29 |
| 3 | 4060 | 0,2160,1800,100,0,0,0 | 303/203 |
| 4 | 27405 | 0,6480,18450,2400,75,0,0 | 3392/1827 |
| 5 | 142506 | 0,7776,105300,27600,1800,30,0 | 51421/23751 |
| 6 | 593775 | 0,0,373950,198400,20700,720,5 | 95302/39585 |

按公平q权重混合可还原w。d_t=M_t−float(μ_q)只作同池描述；不能把整段观察q序列当外生固定条件后相乘，构造第二个显著性检验，因为后续池/q可含先前开奖信息。

## 10. 唯一固定期末检验及精确效应

只有完整、无capture、无故障、通过完整审计的627期才进入固定期末统计。对每个固定n∈{627,314,313}，T=ΣM，整数卷积D_(0,0)=1，`D_(r+1,k)=Σ_(m=0)^6 w_m D_(r,k−m)`。记A=Σ_(k=T)^(6n)D_(n,k)，B=D^n，包含等号的单侧p=A/B。

保存完整非负整数 `numerator_hex=hex(A)`、`denominator_hex=hex(B)` 和Python整数除法产生的显示float。主要阈值是整数比较20A<=B。不得用正态、mid-p、双侧、模拟、显示舍入或更换尾部代替。

效应精确分子E=T×D−n×24,189,744，分母nD；正效应用E>0。显示 `mean_M=T/n`、公平μ=24,189,744/D，差按 `mean_M−μ` 固定顺序。主要条件仅aggregate的E>0且p<=1/20；两半p均显示但无独立通过权，不能救回aggregate失败。

已独立核对的数学边界：627期最小总分1112（p≈0.04660501177286907）；314期563（≈0.04424919636379458）；313期561（≈0.04624510329011062）。这些是零分布算术，不是候选成绩。

局部p只在该固定诊断的公平H0下成立。它不是整个跨版本、自适应Goal的多重比较校正；本稿没有编造全局校正p或把它填成局部值。完整尝试目录必须记录所有版本、时间、已见数据范围、候选/规则依据、关闭/失败/负结果、重复日期关系、主次终点及任何调整；同一历史不能因新名字成为新的独立机会。任何整体研究错误率或选择后主张都必须有另行适用的预先方案，不能凭本局部p声称解决。

## 11. 三scope汇总、年度描述和恰好12个区间

每个scope固定按目标日期升序汇总：预定/冻结/揭晓/完成/缺失/故障期数；每个G的平均H和0..6直方图；M均值及0..6直方图；≥3/4/5/6次数/率；q均值与0..6直方图；每q观察数和M条件直方图；d均值；Top-6/12/18平均命中及0..6直方图；平均实际排名；B、L及公平值和逐期配对差的均值；10箱校准。均值除M主要显示的既定T/n外，均对日期序列使用math.fsum/n，n=0时null，计数不伪造为观察。

完整最佳合法组命中须报所有并列目标日期及对应全部固定G身份/号码/分数，同时报告每个G自己的全部并列最佳日期。Top-K最佳也保存全部并列日期并标为排名诊断。绝不只挑最佳日期代替627期全记录。各年2020..2025只按相同公式给点估计、计数/直方图/校准和完整并列描述，不给年度p/CI/通过结论，不因年度表现删期。

仅当完整627期无capture/故障并通过审计时生成下列**恰好12个描述CI**：

| CI ID | scope | 固定逐期配对向量 |
|---|---|---|
| aggregate_M_fair | aggregate | float(M)−(24189744/13983816) |
| aggregate_M_same_pool | aggregate | float(M)−float(μ_q) |
| aggregate_Brier_fair | aggregate | B−B0 |
| aggregate_LogLoss_fair | aggregate | L−L0 |
| first_half_M_fair | first_half | float(M)−(24189744/13983816) |
| first_half_M_same_pool | first_half | float(M)−float(μ_q) |
| first_half_Brier_fair | first_half | B−B0 |
| first_half_LogLoss_fair | first_half | L−L0 |
| second_half_M_fair | second_half | float(M)−(24189744/13983816) |
| second_half_M_same_pool | second_half | float(M)−float(μ_q) |
| second_half_Brier_fair | second_half | B−B0 |
| second_half_LogLoss_fair | second_half | L−L0 |

每行都单独新建 `numpy.random.default_rng(649)`，10,000次、抽样单位整期且有放回，`indices=rng.integers(0,n,size=(10000,n))` 使用默认dtype与endpoint=False。对每个sample按生成索引顺序 `math.fsum(v[int(i)] for i in sample)/n`，形成np.float64数组；`np.quantile(means,[0.025,0.975],method='linear')`，端点存为Pythonfloat并保留hex及seed/resamples/method/scope/向量ID。每行重新seed是合同，不共用一个持续推进的generator。

CI只是配对逐期重抽样描述，不保证未知时间相关备择下的稳健覆盖，不是额外门槛。Brier/LogLoss较低较好，M差较高较好；不能在12个区间中挑正面者替换主要检验。没有年度/单组/Top-K/校准额外区间。完整case的Reject也照常报告全部预定统计和12CI。

## 12. 互斥停止分支、状态及 null 规则

每个本候选的正式开始只有一次；重试、补期、改组、换目标、续跑、删除/更新lease或覆盖已有输出都禁止。具体一次性启动/lease/不可变发布规则须新操作登记，本文不创建或复用旧对象。

下表只适用于**已进入注册 one-shot attempt** 的事件。普通源码设计、纯合成测试和不创建 canonical state 的只读 readiness 核查不属于正式 attempt，不因工程失败而被冒充已消费的启动失败。新操作合同必须固定正式 attempt-entry 的精确持久化事件，并在调用第一次模型生成之前写入及 fsync `first_forecast_generation_intent`。该首次生成意图是阶段边界，不是一个已经存在的记录或已生成预测的声明；后续每期的顺序也必须有同等明确的不可重试记录。

状态从已验证的持久化事件和实际过程观察导出，绝不能只用“已完成评分期数=0”推断尚未生成/揭晓。正式 attempt 已进入但阶段证据不够时，使用独立的 unknown 状态并冻结，而非猜测一个较早失败阶段。

| 条件 | 科学/运行状态 | 可报告内容 | 固定期末p/CI/通过 |
|---|---|---|---|
| 正式 attempt 已进入，在首次生成意图之前故障，且有积极证据证明模型生成从未开始 | startup_failed_unscored_no_retry；永久停止，科学分类null | 真实持久化阶段、权限/源事实、错误边界；无科学分数 | 全部null，不是Reject |
| 首次生成意图已经持久化后发生任意非capture故障，包括源/输入/runtime/概率/分组/冻结/揭晓/评分/统计/发布审计失败 | execution_failed_archive_no_retry；科学分类Archive，reason为incomplete或invalid | 原始不可变记录、真实合法完成前缀和失败当前期；即使0个完整目标也不归入启动失败 | aggregate及两半p、12CI、主要通过全部null，即便前半已完整 |
| 正式 attempt 已进入，但不能可靠判定首次生成阶段或真实过程状态 | frozen_failure_phase_unknown_no_retry；科学分类null，不猜测早期阶段 | 已存证据、已知事实和不确定范围；不把0个完成评分说成没有生成或揭晓 | 全部推断与通过字段null；没有Goal完成资格 |
| 完整冻结后首次G1..G5之一精确6/6，且当前完整科学评分有效 | capture_pending_independent_audit；停止下一forecast | 完成当期全部五组和概率评分，冻结全前缀及capture身份；只给描述 | 全部null，包括capture发生在第627期 |
| capture随后独立审计失败 | Archive；capture_unqualified，永久停止 | 保留观察与失败原因，不称合法6/6；证据不覆盖 | 全部null，Goal未完成 |
| capture独立审计通过但冻结/最终报告/通知任一未完成 | capture_audit_passed_pending_completion | 合法历史五组之一6/6及未完成事项 | 固定期末推断仍null，Goal未完成 |
| capture独立审计通过、证据冻结、最终报告及唯一默认中文通知均完成 | audited_historical_five_group_capture_completed | 完整审计/最终证据，按明确多组Goal范围报告 | 固定期末推断仍null；仅这条可进入Goal完成核验 |
| 完整627、无capture/故障、完整审计；E<=0或局部主p>.05 | Reject | 全部627、三scope统计、年度描述、全部12CI及负结果 | 合法固定期末结果；无优势/无推广 |
| 完整627、无capture/故障、完整审计；E>0且局部主p<=.05 | complete_historical_diagnostic_conditionpass_unpromoted | 全部627和完整统计，限定历史诊断条件满足 | 无live推广、无盲确认、无Goal完成 |

表中的Archive是科学解释类别，不删除/归档掉证据。没有“排除一条坏记录之后仍627期完整”的分支。任何已观察完整前缀不能加上后来修好的后缀拼为一次合法完成。若异常已知，优先记录异常/无效，不把同一失败目标的可疑6/6升级为合法capture。已知首次生成意图后的完整性失败进入 Archive；阶段本身不确定则进入上述 unknown 状态。无论零完成评分还是已有前缀，都没有补跑授权。

capture当期的五组评分必须全部完成；若当期评分本身失败，保留已冻结预测与已揭晓事实，转Archive/incomplete或invalid并标明潜在未核验capture，不能编造剩余评分。完整前缀n=0时均值null；没有合法五组就没有该期M，不补0，不以四组的最大值替代。

只有完整无capture分支才产生固定期末推断，仍使用原无条件公平零分布；不因观察到“没有6/6”事后改成条件分布。若已计算但未完整认证的中间统计存在于故障证据，应标为未认证中间值，最终通过字段仍null，禁止覆盖旧文件伪装成功。

capture审计必须独立验证目标/未来/预处理/特征/模型选择无泄漏，逐期 chronology、不可变快照、Git图、单次lease、运行闭包、完整组数和先冻结后揭晓均成立。完成需真实证据冻结、最终报告及已审默认SMTP路线的一次中文通知；不改收件人/服务器，不重复尝试同小时进度邮件，不读/显示Secret。通知失败不伪称已通知或Goal完成；具体可靠通知操作必须事前另行闭合，不能自动重跑worker来补邮件。

## 13. 104期前瞻与理论6/6量级

原备忘的104期只是未激活的未来规划，不进入当前历史主合同，不启动live/canary/排期。其零分布数学边界T=192、p≈0.038308164627511965只是参考，不授予前瞻运行权限。未来若有独立完整注册，只能从首个合法预先提交快照之后的新队列开始，不把历史或旧V1/V13票改组为前瞻。

公平固定五组的单期精确6/6为5/13,983,816，五个事件互斥。固定完整627期的期数期望95/423752，至少一次概率 `1−(1−5/13983816)^627`≈0.00022416264432631753；这不是模型实测成绩、未来等待时间推断或全Goal的p。历史一次全中不会证明未来1000期、10期或每期三/五组的等待时间。

## 14. 必须完成的后续验收边界

本稿对输入审查的三个缺项及整合审查指出的阶段重叠给出明确条款，但仍需新鲜独立审查 v2 文本、限定基准修订及其后操作协议。不得把先前数学PASS当作完整登记、完整数值实现或运行PASS。

新实现获准之前，至少需要独立纯合成/math验收：原长期频率浮点路径及strength250；N<300拒绝；严格prior/target隔离；49键类型/finite/open区间及1e-12质量边界；等值排名/标签置换与固定五列；缺组/重复组/Top6非capture/G1别名；全部小样本Brier/未截断fsum LogLoss、10箱每个边界/空箱；精确w及q表、整数卷积/包含等号/α；恰好12CI的固定generator/索引/quantile行为；所有失败/capture/第627capture的null规则；全group/全ties输出；每个运行源/runtime边界的fail-closed。

这里列的是未来验收要求，尚未编写/运行本候选测试、没有实际预测或评分。完整尝试目录、协议基准协调、版本/路径/源码封印、双轴审查、Git/权限/唯一运行链与通知路线要在真实下一阶段另行完成。任何未通过都不能靠看到成绩后修改本候选或重跑来规避。

v1 实际新增写入时间（UTC）：2026-09-13T19:46:38.957808+00:00
v2 实际排他新增写入时间（UTC）：2026-09-13T19:55:08.932150+00:00
