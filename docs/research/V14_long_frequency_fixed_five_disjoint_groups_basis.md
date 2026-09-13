# V14 长期频率与固定五个不相交六数组：完整科学登记依据

**R14 登记检查点：REGISTERED / NOT IMPLEMENTED / NOT AUTHORIZED / NOT SCORED。**

本文定义R14的规范性科学合同。登记检查点必须由真实R14源提交和经核验的受保护main普通合并证明；未提交或未合并的准备副本不自行生效。登记本身不授予实现完成、历史读取、启动、通知或live权限，NOT IMPLEMENTED / NOT AUTHORIZED / NOT SCORED须保持到各自真实阶段完成。

## 0. 固定身份、作者及来源

| 字段 | 固定值 |
|---|---|
| experiment | V14_long_frequency_fixed_five_disjoint_groups |
| model_id | v14_long_frequency_fixed_five_disjoint_groups |
| whole model version | v14.0.0 |
| probability source | 既有V1 LongFrequencyModel，name=long_frequency，全部严格可见历史，strength=250.0 |
| probability_source_version | v1.0.0（固定旧config.yaml项目标签；类自身无内置版本字段，以源码SHA为权威） |
| probability_adapter_version | v14.0.0（本次明确赋予的新适配身份） |
| selector | fixed_snake_top30_v1 |
| feature_set_id | v14_long_frequency_full_prefix_strength250_inherited_features_v1 |
| seed | 649；仅使用于预定描述bootstrap，不引入随机实选组 |
| evidence lane | consumed_historical_diagnostic_only |
| formal historical attempt limit | 1 |
| live / prospective activation | none |
| 登记基点 | b1c99b02d9e18ca66b806b00c41a739daeae6740（父代理已核实PR56普通合并） |
| 科学依据仓库路径 | docs/research/V14_long_frequency_fixed_five_disjoint_groups_basis.md |
| 配套操作注册仓库路径 | docs/experiments/V14_long_frequency_fixed_five_disjoint_groups.md |
| 机器登记路径 | evidence/research_registrations/v14-long-frequency-fixed-five-disjoint-groups-v1.json |

上述路径、身份与未来操作阶段由本次登记固定。R14不创建任何预测、评分、attempt、claim、lease、通知标记或历史运行权限。最终仓库整合由/root完成；下述作者及准备记录保留其实际阶段和范围。

实际规范化作者：`/root/v13_test_exception_contract_map`，贡献会话标识 `v14-complete-scientific-registration-basis-authoring-20260913`。实质共同贡献者：`/root`，负责固定身份、用户多组Goal衔接、数值/评分合同、分阶段审计以及N通知部署决定。既有基础材料作者包括 `/root/multi_group_research_design_check`（概念）、`/root/v13_test_exception_contract_map`（源码与整合）、`/root/v13_exception_spec_review`（数学）；这些实际贡献须在R14作者记录中如实体现，不能作为独立作者之外的审查身份使用。

本稿规范化的直接输入是冻结的完整science v2，SHA-256 `92c8b07dcd0b02b7998ce9d0f092292a25040b6f429d7e7de833e61da25f6fac`。v2由/root在原v1 `dc3e0c8d2510d982e06544d57d5a975acc37d441657365bdc2ff30b06ce53153` 上只明确限定解析基准协议及互斥阶段状态；原件都保留。本稿保留概率算法、250强度、627/314/313、五组、全部评分/零分布/主要阈值及12CI，新增规范化身份和明确的内部/外部审计时序，不进行结果驱动的改选。

| 既有准备材料 | SHA-256 |
|---|---|
| 原概念备忘 | 687889c948d9351c012a4e291c905ee4d469d87a5d8e25f2ea34cc7d5edb4e89 |
| 精确概率/选择源码映射 | 986b238a6d7424ff02089a8a8576bf00ca0887fd5f9eafc09f805747f95a2fda |
| 完整数学合同 | 65144487d26e4f889759e9b8d61304a8983b04361ff005b3524f9b09a8ac3c8c |
| 初次独立数学/科学审查 | ee622a61a5a5cbfbf7733a369905e26ccb960307cd8f3b54f62765a3864c0176 |
| 固定science v2的最终独立数学/科学PASS | 2b80b084e3fe03d81175d17e8a686d9d2a7b13236f1e34f69203c5bc12043884 |

完整规范性公式、身份和测试oracle均在本文，不依赖外部/tmp文件才能定义行为。以上摘要只是可审计准备溯源，不成为新授权对象。

时间与暴露必须如实表述：原概念备忘记载写入时间2026-09-13T17:41:40.240104Z，在V13揭晓之前；这是外部准备记录的时间，不是事前Git公证或完整预注册。完整v1为19:46:38.957808Z、science v2为19:55:08.932150Z，后者已经在V13结果之后。本R14依据亦在V13结果之后，不能追溯称为当时已经完整注册。源码映射作者此前从MODEL_PROTOCOL前200行接触旧V1/V12摘要，数学作者也披露其先前结果审查角色；无全局盲态声明。这些暴露不改变此处预先固定的唯一概率源、规则或阈值。未产生或读取V14历史结果。

本次规范化只读取固定science v2文本，接收父代理给出的实际提交、既有审查和合成运行元数据；没有读取历史/答案/历史报告、执行项目import、模型、测试、网络或凭据操作，没有创建canonical state。第16节的运行是父代理已完成的有限合成校验，不是本文作者再次执行，也不是V14历史回测。

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

精确既有入口：`src/lotto649/models/baselines.py:30–41` 的 `LongFrequencyModel.predict`，不调用包含其他模型的 factory 来生成额外 producer。下列源字节身份继承于固定旧源码检查点 `182a4245bbaf0c444ef1e16c1b5beb120eec327f`；R14 的登记基点为 `b1c99b02d9e18ca66b806b00c41a739daeae6740`。注册与后续 I14 必须验证继承源身份保持相等，不能把旧检查点的授权移给 V14。核心相关文件身份如下。

| 源码 | SHA-256 |
|---|---|
| models/baselines.py | 76f9050a13bde44d51584397ecd6acb358f320e1617ef329b70bd6a22d23e28a |
| models/base.py | e2f0c90c376ea6063b906bcca042e8903b351a1ed4b76e9d83e17be3bcf166ec |
| features.py | b7bc67b9038b2e3d78230c3087c3ac4e3f17751aeab678574f3601af00671979 |
| domain.py | fbcb22747ae361767df070c6e50af49fda1aa190b72fd39894afa1c879a50b7a |
| optimizer.py | f5bda2a8ee8cd19c7b719a8f3344a7e4ca76def75971d5e8fe49489189abd1a4 |

这些路径以 `src/lotto649/` 为共同前缀；本依据的第15节补齐固定 Git blob、初始化模块及最少依赖源码身份。上述表不是 I14 完整 runtime closure 的替代品。I14 的九个路径仅以配套操作注册文件 `docs/experiments/V14_long_frequency_fixed_five_disjoint_groups.md` 的分配表为权威；本科学依据不复制另一份分配表。

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

既有归一化 cap 后不会重新归一化，所以不能先假定以上门槛对所有输入天然成立。此精确 `1e-12` 门槛在 V14 结果之前固定，来自源码/数学设计。已完成的七个虚构历史 fixture 检查在其有限输入内通过此门槛；其适用范围和真实证据列于第16节。这不证明任意输入、V14 协调层、全新状态机或完整实现已经通过。I14 必须重新完成其自己的独立合成/数学边界验收。

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

本文不伪造未来 I14 核心、闭包或执行提交 SHA；这些只能在真实实现和独立审查后产生。第16节的有限合成运行不是 I14 的完整环境与闭包验收；本次规范化作者没有导入项目或执行环境探测。

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

任一固定G第一次精确命中六个主号时，在进入下一期预测之前停止。必须保留并完成当期已冻结的五组以及全部预定概率/排名评分，报告具体固定组ID。其最终表述只能是“预先冻结五组之一的历史6/6”，不冒充原单组Final-6证据。用户已明确授权多组研究目标，R14 将这项衔接限定为本实验预先固定的 G1–G5；仍须满足第12节完整审计、证据冻结、最终报告和已记录通知成功，才能核验整个 Goal 的完成。该授权绝不允许把获胜 G 重命名成旧单组 Final-6。

这里没有六元素集合上的联合概率；不得称任何G为联合最可能，不把Σp或∏p当作经过校准的全中概率。也不调用旧 `select_combination` 的Top-12单组枚举。

## 6. 两个解析置换对照与 V1/公平基准边界

1. **主对照：全球标签均匀置换。** 对固定五组施加同一个1..49均匀标签置换，保留五组大小、30号覆盖数和全部零重叠结构。使用其精确解析零分布，不实际生成随机票，不以多个随机种子的最佳值比较。
2. **次要对照：同一Top-30池内均匀置换。** 保留实际冻结的30号集合，再均匀重分为同样五组；使用给定q的解析条件分布。它只诊断同池安排，不选择新的分组。

公平常数p0=6.0/49.0用于Brier、binary Log Loss及校准参考；公平Top-K单期命中理论为Hypergeometric(49,K,6)，均值6K/49。每个固定G的公平平均命中36/49只作单组描述，不能取代五组主要公平均值。

既有V1长期频率就是本候选的概率来源，不能给它换名称后声称独立新V1对照。本文不重新生成V1 ensemble或 `RandomBaseline` 的经验票、不借用旧预测重组为新证据、不导入额外经验producer，也不把五组对一组的差称为预测优势。

**R14 必须在同一登记变更中生效的限定协议修订：** 对本唯一五组历史诊断，`docs/MODEL_PROTOCOL.md` 中保留随机模型的基准要求及 `docs/RESEARCH_ROADMAP.md` 中相应公平/V1/负对照文字，须在同一新注册变更中明确以下范围，并接受独立 Spec 审查：

- 随机比较采用上述两个均匀标签置换的**精确解析积分**及公平概率模型 p0=6/49。它保留固定组数、覆盖和全部重叠结构，没有抽取额外随机票或挑选随机种子。这是本实验明确登记的随机基准形式。
- 没有执行经验 `RandomBaseline`、独立 V1 ensemble 或端到端扰动历史的经验实验；不得把解析对照标成这些程序的实测运行或以此声称这些路径通过了经验负控检验。输入、冻结和评分管线另由完整合成故障测试及正式后审计验证，解析正确性不替代它们。
- V1 联系仅为原有 `LongFrequencyModel` 概率源及其固定源码/数值身份；既有 V1 源码等价检查不是独立对照。没有“优于未运行 V1 ensemble”的结论，也没有把五组和 V1 一组机会数不匹配的比较当优势。
- 仅在这项新登记内以此明确形式履行基准用途；不删除仓库通用基准要求，也不改变旧版本实验。新的协议文字、科学合同与全部报告须一致。若独立审查仍认为不足，必须在看新候选结果前关闭该设计缺口，不能运行后补规则或追加经验 producer。

上述条款是 R14 的规范性范围，必须在真实 R14 中连同对应协议文字一并审查和普通合并；当前外部依据草案不代表这些仓库文件已被修改或 R14 审查已经通过。

## 7. 每期评分与严格顺序

每期t必须按下列单向顺序：认证源/runtime/输入前缀 → 计算一次概率 → 验收全49号概率 → 完整排名和G1..G5 → 生成真实运行UTC时间及全部预测元数据 → 不可变冻结并认证摘要 → 揭晓当期固定权威的真实主号/特别号 → 完成当期全部评分 → 若capture或故障停止，否则进入下一期。

预测入口不接受当期答案。不能先揭晓再补写冻结时间。历史目标日期、模拟训练截止与真实生成/冻结UTC时间分别记录，不把目标当天午夜伪称为实际计算时间。冻结方案与 hash-chain/源核对属于新操作注册，本文不创建它们。

记主号集合Y，五组H_j=|G_j∩Y|，M=max(H1..H5)，q=|Top30∩Y|=ΣH_j，d=M−μ_q。对每个G保存H及匹配号码；对Top-K保存命中数和匹配号码。全部真实主号的平均排名为 `math.fsum(float(rank[i]) for i in sorted(Y))/6.0`。

**Brier：** 标签i升序，y_i=float(i in Y)，`B=math.fsum((p_i-y_i)**2 for i in 1..49)/49.0`。公平B0按同式使用p0计算，先形成每期B−B0，再按日期汇总。

**Binary Log Loss：** 严格有限(0,1)验收通过后，按标签升序计算 `loss_i=-(y_i*math.log(p_i)+(1.0-y_i)*math.log(1.0-p_i))`，`L=math.fsum(loss_i for i in 1..49)/49.0`。公平L0按完全同式用p0计算。没有eps截断、log1p替换、概率修补或联合六数组score。这是 V14 结果之前固定的评分算术，不声称与旧 `evaluation.binary_log_loss` 的截断/逐次累加逐位相同。第16节限定了现有合成校验的范围；V14 实现仍须独立验证本公式及其故障边界，不能把原模型或外部 oracle 的验证等同于 I14 验收。

**Calibration固定10箱：** 边界为Python float字面量 `[0.0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0]`。前9箱左闭右开，末箱[0.9,1.0]；有效p不含0或1。用明确区间比较，不按乘10后取整替代边界。每期及各描述scope分别列10行，保存箱内号码观察数、`math.fsum(p)`、实际主号指示和、平均p、实测频率及频率−平均p。合并scope时按日期然后号码升序扁平化49×n项，再用fsum；空箱计数/和为0，平均/频率/gap为null。所有49号贡献是同一期内相关观察，不能据箱样本量宣称独立检验。公平常数亦按同边界/公式列参考表。不合箱、不换边界、不拟合校准器，不添加校准显著性或额外通过门槛。

## 8. 每期不可省略的输出

预测快照须包含：目标ordinal/日期；历史权威及对象身份；严格训练截止日期、前缀期数和前缀摘要；原概率源身份；实验 `V14_long_frequency_fixed_five_disjoint_groups`、model_id `v14_long_frequency_fixed_five_disjoint_groups`、整体模型版本和probability_adapter_version均为 `v14.0.0`、原概率源名称 `long_frequency`及legacy probability_source_version `v1.0.0`、选择规则版本 `fixed_snake_top30_v1`、feature_set_id `v14_long_frequency_full_prefix_strength250_inherited_features_v1`，以及本节及第3节固定的特征/源码身份；完整源码/配置/Git commit/runtime身份；实际生成和冻结UTC时间；不可变快照路径/字节数/SHA及ledger关系。

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

只有完整627期、无capture或故障，并通过 worker 内部完整 chronology/identity/schema 审计，才计算以下暂定数值 p/CI 并产生暂定报告。随后外部独立审计才赋予 Reject 或 conditionpass 的正式科学资格。内部审计不替代外部审计；第12节明确两阶段状态和失败时如何保留原数字。这是结果之前明确的审计时序，不改变零分布、公式、阈值或停止规则。对每个固定n∈{627,314,313}，T=ΣM，整数卷积D_(0,0)=1，`D_(r+1,k)=Σ_(m=0)^6 w_m D_(r,k−m)`。记A=Σ_(k=T)^(6n)D_(n,k)，B=D^n，包含等号的单侧p=A/B。

保存完整非负整数 `numerator_hex=hex(A)`、`denominator_hex=hex(B)` 和Python整数除法产生的显示float。主要阈值是整数比较20A<=B。不得用正态、mid-p、双侧、模拟、显示舍入或更换尾部代替。

效应精确分子E=T×D−n×24,189,744，分母nD；正效应用E>0。显示 `mean_M=T/n`、公平μ=24,189,744/D，差按 `mean_M−μ` 固定顺序。主要条件仅aggregate的E>0且p<=1/20；两半p均显示但无独立通过权，不能救回aggregate失败。

已独立核对的离散数学边界如下；这些是零分布算术，不是 V14 成绩。

| 固定 n | 最小 T 使 p≤.05 | 此 T 的 p | T−1 的 p |
|---:|---:|---:|---:|
| 627（唯一主要检验） | 1112 | 0.04660501177286907 | 0.052980130521112334 |
| 314（次要描述） | 563 | 0.04424919636379458 | 0.05305461159190216 |
| 313（次要描述） | 561 | 0.04624510329011062 | 0.055376968274192355 |
| 104（未激活前瞻数学参考） | 192 | 0.038308164627511965 | 0.05262093069573685 |

局部p只在该固定诊断的公平H0下成立。它不是整个跨版本、自适应Goal的多重比较校正；本稿没有编造全局校正p或把它填成局部值。完整尝试目录必须记录所有版本、时间、已见数据范围、候选/规则依据、关闭/失败/负结果、重复日期关系、主次终点及任何调整；同一历史不能因新名字成为新的独立机会。任何整体研究错误率或选择后主张都必须有另行适用的预先方案，不能凭本局部p声称解决。

## 11. 三scope汇总、年度描述和恰好12个区间

每个scope固定按目标日期升序汇总：预定/冻结/揭晓/完成/缺失/故障期数；每个G的平均H和0..6直方图；M均值及0..6直方图；≥3/4/5/6次数/率；q均值与0..6直方图；每q观察数和M条件直方图；d均值；Top-6/12/18平均命中及0..6直方图；平均实际排名；B、L及公平值和逐期配对差的均值；10箱校准。均值除M主要显示的既定T/n外，均对日期序列使用math.fsum/n，n=0时null，计数不伪造为观察。

完整最佳合法组命中须报所有并列目标日期及对应全部固定G身份/号码/分数，同时报告每个G自己的全部并列最佳日期。Top-K最佳也保存全部并列日期并标为排名诊断。绝不只挑最佳日期代替627期全记录。各年2020..2025只按相同公式给点估计、计数/直方图/校准和完整并列描述，不给年度p/CI/通过结论，不因年度表现删期。

仅当完整627期无capture/故障并通过 worker 内部完整 chronology/identity/schema 审计时，生成下列**恰好12个暂定描述CI**。外部独立审计通过后它们才成为合格诊断结果；外部失败时按第12节以新不可变关闭记录将权威推断字段置null，原暂定数字保持原字节。

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

CI只是配对逐期重抽样描述，不保证未知时间相关备择下的稳健覆盖，不是额外门槛。Brier/LogLoss较低较好，M差较高较好；不能在12个区间中挑正面者替换主要检验。没有年度/单组/Top-K/校准额外区间。外部独立审计合格的完整case，无论最终为Reject或conditionpass，都报告全部预定统计和12CI；没有因为负结果删掉CI的例外。

## 12. 互斥停止分支、状态及 null 规则

V14 正式开始只有一次；重试、补期、改组、换目标、续跑、删除/更新lease或覆盖已有输出都禁止。具体一次性启动、lease、claim、ledger、固定路径、九个I14实现路径、源作者记账和不可变发布规则由配套操作登记 `docs/experiments/V14_long_frequency_fixed_five_disjoint_groups.md` 统一定义，必须与本科学依据一致。本文不创建或复用旧对象。

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
| 完整627、无capture/故障、内部 chronology/identity/schema 审计通过，外部独立审计仍未完成 | complete_internal_audit_passed_external_audit_pending；最终科学分类null | 原始627记录、暂定p/CI/报告；不得提前称为已审计Reject或conditionpass | 仅暂定数值；权威推断/通过尚无资格 |
| 完整627的外部独立审计失败 | execution_failed_archive_no_retry；科学分类Archive | 新增不可变关闭记录绑定原暂定证据和失败原因；原p/CI/报告数字与文件完全保留 | 关闭记录的权威p/CI/通过全部null，不改写原数字 |
| 完整627、无capture/故障、内部及外部独立审计均通过；E<=0或局部主p>.05 | Reject | 全部627、三scope统计、年度描述、全部12CI及负结果 | 合法固定期末结果；无优势/无推广 |
| 完整627、无capture/故障、内部及外部独立审计均通过；E>0且局部主p<=.05 | complete_historical_diagnostic_conditionpass_unpromoted | 全部627和完整统计，限定历史诊断条件满足 | 无live推广、无盲确认、无Goal完成 |

表中的Archive是科学解释类别，不删除/归档掉证据。没有“排除一条坏记录之后仍627期完整”的分支。任何已观察完整前缀不能加上后来修好的后缀拼为一次合法完成。若异常已知，优先记录异常/无效，不把同一失败目标的可疑6/6升级为合法capture。已知首次生成意图后的完整性失败进入 Archive；阶段本身不确定则进入上述 unknown 状态。无论零完成评分还是已有前缀，都没有补跑授权。

capture当期的五组评分必须全部完成；若当期评分本身失败，保留已冻结预测与已揭晓事实，转Archive/incomplete或invalid并标明潜在未核验capture，不能编造剩余评分。完整前缀n=0时均值null；没有合法五组就没有该期M，不补0，不以四组的最大值替代。

只有完整无capture分支经内部 chronology/identity/schema 审计通过后才产生暂定固定期末数值，仍使用原无条件公平零分布；不因观察到“没有6/6”事后改成条件分布。内部审计失败时不计算p/CI、只保留真实失败证据；外部独立审计在暂定报告存在之后进行，因此不能把其未完成误称为内部计算尚未获准。外部审计失败时必须新增独立不可变关闭记录，绑定原暂定文件SHA、实际审查和失败依据，明确Archive及权威推断p/CI/通过为null；原暂定数值、文件和ledger一字不改。不得通过重新拟合、重算或替换原暂定结果、恢复worker或拼接运行来谋求通过。外部审计对既定算术和冻结记录的独立只读核验不等于新预测；发现问题后的结论是记录失败，不能重新执行正式科学流程。

capture审计必须独立验证目标/未来/预处理/特征/模型选择无泄漏，逐期 chronology、不可变快照、Git图、单次lease、运行闭包、完整组数和先冻结后揭晓均成立。Goal完成需要真实证据冻结、最终报告及按独立N通知部署登记记录的一次中文通知成功。

**N通知部署是 I14/K/历史授权之前必须另行登记并满足的操作前置条件。** 不能声称本草案或任何旧路线已提供可运行的V14通知部署；R14科学登记本身不启用发送。N必须绑定仓库默认SMTP Secrets和默认收件人/服务器，不接受调用参数换路线，不读取/展示/落盘凭据，排除与已有通知/进度邮件的重复。仅在合格capture经过独立审计和证据冻结后才可进入已登记的通知流程。

对本V14合格capture，SMTP尝试至多一次。N必须在实际发送之前持久化不可重试意图，只有已记录的真实成功终态才满足通知完成；发送失败或结果未知都是不可自动重试的终态。可能已发送不等于已记录成功，不得因此完成Goal；不能重新运行worker或换路/换身份补发。独立N登记必须预先定义成功、失败、未知的验证及不可变证据，而不是事后临时解释。

## 13. 104期前瞻与理论6/6量级

原备忘的104期只是未激活的未来规划，不进入当前历史主合同，不启动live/canary/排期。其零分布数学边界T=192、p≈0.038308164627511965只是参考，不授予前瞻运行权限。未来若有独立完整注册，只能从首个合法预先提交快照之后的新队列开始，不把历史或旧V1/V13票改组为前瞻。

公平固定五组的单期精确6/6为5/13,983,816，五个事件互斥。固定完整627期的期数期望95/423752，至少一次概率 `1−(1−5/13983816)^627`≈0.00022416264432631753；这不是模型实测成绩、未来等待时间推断或全Goal的p。历史一次全中不会证明未来1000期、10期或每期三/五组的等待时间。

## 14. R14与I14的验收边界

固定外部science v2已有独立数学/科学PASS，范围和摘要见第16节；过时的“v2仍待该项审查”不再作为当前事实。该PASS不覆盖本规范化R14依据、新的分阶段审计澄清、N通知部署、配套操作规范、实际封印或I14实现。真实R14必须重新完成Standards与Spec两轴独立审查；作者贡献必须记账，作者不能冒充自己的独立审查者。

新实现获准之前，至少需要独立纯合成/math验收：原长期频率浮点路径及strength250；N<300拒绝；严格prior/target隔离；49键类型/finite/open区间及1e-12质量边界；等值排名/标签置换与固定五列；缺组/重复组/Top6非capture/G1别名；全部小样本Brier/未截断fsum LogLoss、10箱每个边界/空箱；精确w及q表、整数卷积/包含等号/α；恰好12CI的固定generator/索引/quantile行为；所有失败/capture/第627capture的null规则；全group/全ties输出；每个运行源/runtime边界的fail-closed。

上述是I14必须执行的完整验收要求；已有外部合成校验仅覆盖第16节明确的子集。当前没有V14实现测试、历史预测或评分。完整尝试目录、同批协议修订、实际R14封印、R14/I14新鲜双轴审查、九路径实现、Git/权限/唯一运行链及独立N部署须按配套操作规范逐项完成。任何未通过都不能靠看到V14成绩后修改本候选或重跑来规避。


## 15. 自包含源码身份与合成/闭式fixtures

源概率函数的实数说明与现有浮点实现必须区分。其输入主号指示矩阵以NumPy浮点零矩阵创建，每个号码出现时赋1.0，重复主号不允许；第i列的long_freq是float(x.mean())。number_feature_frame拒绝空历史，循环号码1..49并以Pandas DataFrame返回。LongFrequencyModel没有初始化参数、随机数调用或持久可训练状态；它保留全部传入历史。目标weekday虽传到特征帧，但不参与posterior的有效公式。正式V14协调层另行强制N>=300，不能从底层接受N=1推导正式运行许可。

固定核心Git blob及最少本地依赖（Git模式均100644；I14仍需认证完整实际传递闭包）：

| 路径 | Git blob SHA-1 | 文件SHA-256 |
|---|---|---|
| src/lotto649/models/baselines.py | 4f4817a5f7895e325c1adebbcd18d933117b53fd | 76f9050a13bde44d51584397ecd6acb358f320e1617ef329b70bd6a22d23e28a |
| src/lotto649/models/base.py | 31a01009c50bdeb3b73b7a9d9f289a23a6e1deb6 | e2f0c90c376ea6063b906bcca042e8903b351a1ed4b76e9d83e17be3bcf166ec |
| src/lotto649/features.py | a735fd3092a6a3de226823f0491b437e1e69cada | b7bc67b9038b2e3d78230c3087c3ac4e3f17751aeab678574f3601af00671979 |
| src/lotto649/domain.py | 7465f79ca3548ca9c61ba173220b04dadec5d6b9 | fbcb22747ae361767df070c6e50af49fda1aa190b72fd39894afa1c879a50b7a |
| src/lotto649/optimizer.py | 5a7dfeacd16e7f34e19ceda361ae5fc57d3873ac | f5bda2a8ee8cd19c7b719a8f3344a7e4ca76def75971d5e8fe49489189abd1a4 |
| src/lotto649/__init__.py | 3dc1f76bc69e3f559bee6253b24fc93acee9e1f9 | 91447944015cec709e8aa7655f7e9d64e1e4508e7023a57fe3746911c0fc6fed |
| src/lotto649/models/__init__.py | e69de29bb2d1d6434b8b29ae775ad8c2e48c5391 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| requirements/v12-historical.txt | bd577c57cbcabac1f4409665547ff36015f378c8 | a0dfeac17ad7e1c41dffe4b41b4810156fb028f879d312430bfc517672a570c6 |
| config.yaml（legacy项目版本标签与源配置身份） | 228297cb4253f4f05a85373a7672f36c2b1f739f | d53a9a9eed5ab434b021472135d6aed65c2c052339e0dfb88f8c00d46c0d8931 |

既有ProbabilityModel抽象接口及Draw身份包含在上述依赖。Draw类会排序主号，检查长度6、互异与1..49、bonus合法且不重复主号，但这不能替代V14的原生int/no-bool、数据完整性、日期和严格前缀验证。旧rank_numbers按(-p,i)排序；旧select_combination的Top-12单组搜索不属于V14行为。

### 15.1 固定概率、排序与组映射oracle

以下都是合成定义，不能用真实目标答案替换。I14测试必须把纯底层fixture与正式协调层准入分开。

1. 空history必须在底层特征入口被拒绝；协调层N=299拒绝，N=300仅通过长度条件，其他验证仍需通过。N=1只允许作为合成底层公式fixture。
2. 合成49期循环块：对k=0..48取六个主号1+((k+j) mod49)，j=0..5，每期为六个不同标签；每号在整个块出现6次。重复7块，N=343，每号计数42。采用完全虚构且严格递增的2040年以后日期，target在最后之后。实数posterior全部6/49；实际49个输出应彼此相等，排名1..49；数值与实数oracle的比较按事前浮点校验规则，不把实数等式当逐位身份。
3. 纯数学N=1、任意六元素集合A，A内q_i=1549/12299，其余1500/12299，总和6，A内严格较大。不得据此给正式N=1开例外。
4. 在第2条N=343均衡历史后添加一个合成集合A，N=344；A内c_i=43、其余42，对应理想q_i为3607/29106与3558/29106。新数据只影响后继目标；已冻结目标不得重新预测。
5. 选择器独立向量p_i=6(50-i)/1225，i=1..49，严格降序且和6；排名1..49，五组位置必须与第5节完全相同。这不是声称该向量由长期频率源产生。等概率向量单独验证升序并列；一ULP不同概率不得按“近似相同”处理。
6. 对第5条严格不同概率施加固定标签双射π，令π(i)继承p_i，排名为π(1)..π(49)，组为原排名位置的π映射。若有同值，实际按新标签数值升序；不得声称整个带标签tie-break的选择器对所有置换严格等变。
7. 缺失/额外键、bool或非原生int键、非Pythonfloat值、NaN/±inf、0/1/越界、超过固定质量容差必须拒绝。不使用scores.get来修补不合格输出。插入顺序不影响排序和列ID。G1别名、五组互异/六元素/零重叠/覆盖Top30同时核验；Top-6即使全中也不触发capture，除非确为固定G之一。
8. 极度集中的非模型原始scores可触发既有0.999999上限，cap后sum不为6。此fixture说明旧工具无再次归一化；不能因此修改模型计算。正式门槛拒绝不合格输出而不修复。

六行五列的完整排名位置矩阵是：[1,2,3,4,5]；[10,9,8,7,6]；[11,12,13,14,15]；[20,19,18,17,16]；[21,22,23,24,25]；[30,29,28,27,26]。所有1..30恰一次、每列位置和93；内部号码排序不会改变组身份。组内排序不得用来跨列重命名G1。

### 15.2 零分布与评分验收oracle

公平w的独立计数方法：枚举h1..h5各0..6且Σh<=6，以Π_j C(6,h_j)×C(19,6−Σh)加入max(h_j)的权重。第二种方法从多项式[1]开始，依次乘五次[C(6,0)..C(6,m)]，每次只保留0..6次项，再与[C(19,0)..C(19,6)]卷积取第6项；相邻m的累计权重差就是w。两种都是固定组合计数，不是号码/模型/参数暴力搜索。

每个q必须验证Σ_m c(q,m)=C(30,q)，并以Σ_q c(q,m)C(19,6−q)还原w。q=0或1时d=0。整体公平假设给定全部过去时M分布恒为w/D，迭代条件期望可证明固定n的整数卷积；不是忽略模型利用新可见历史的更新。不能将这一证明扩展为未知备择独立性。

检查D_(n,k)非负整数、Σ_k D_(n,k)=D^n、T=0时尾概率1、T=6n时尾分子5^n；α比较包含等号且使用20A<=B。第10节T与T−1八个参考p必须匹配预定数值解释；整数分子/分母才是决策权威。

对任何六个合成真实主号、公平p0=6.0/49.0，第7节新fsum流程的参考Brier为0.10745522698875466，binary Log Loss为0.37177617994345286。此为纯数学/合成参考，不引用V13另一评分流水线的值。候选恰为p0时B−B0=L−L0=0；各自描述bootstrap应返回0,0。允许I14独立计算比对，而不是拿旧历史指标充当oracle。

校准必须覆盖每个固定边界本身及两侧相邻浮点值、空箱、全公平概率箱、0/1/NaN/inf和非法类型；按精确比较归箱，不改边界。箱数量恒10，计数总和为49n，actual正例计数总和6n；p合计及均值用第7节规定的扁平顺序/算术。

12CI验证必须保证每个向量/scope新建seed649、整期有放回索引、10000×n矩阵、逐行fsum/n与linear分位数；没有额外年度/单组CI。缺失、capture（包括第627期）、内部失败禁止生成合格固定期末推断；外部失败保留已生成暂定数值，只追加权威null的关闭记录。故障测试必须包含在首生成意图之前、之后零评分、阶段未知和评分一半等不同持久化边界。

## 16. 已有审查与有限合成验证：真实证据范围

固定science v2的独立数学/科学最终审查已PASS，报告身份为 `five-group-independent-science-v2-final-review-20260913.md`，SHA-256 `2b80b084e3fe03d81175d17e8a686d9d2a7b13236f1e34f69203c5bc12043884`。其范围是该固定v2科学/数学文本；不能外推为R14新规范/操作/N部署/实现的双轴PASS。初次独立报告确认w、条件q表、卷积/阈值、数值公式及其限定解释，后来v2审查处理了明确解析基准与阶段状态的完整性。

父代理已报告真实合成helper v2于2026-09-13T20:28:15.570986Z开始、20:28:16.623465Z结束，session44485、exit0。结果文件身份 `v13-successor-probability-synthetic-validation-v2-20260913.result.json`，SHA-256 `e1617d6d22f43b1f6abe11fff647e4664037025a2a8e164464375a3651e9d3e4`；运行日志SHA-256 `44e9467611513d577320e3da31646a3919629e920e0b33272f669b80e609f414`。这两项是准备证据，正式登记时须妥善保存其原始身份；正文公式不以它们为未展开依赖。

该运行只验证既有概率源与外部oracle：7个人工2040年以后的fixture覆盖N=1、300、343、344、4444极端/常规及344镜像；最大对实数oracle误差1.1102230246251565e-16，最大质量误差8.881784197001252e-16，小于固定1e-12。15类非法selector输入、29个校准边界案例、8类非法校准输入、精确并列/ULP/G1别名/固定五ID通过；前后源字节相同且clone完整干净，仅载入七个项目模块。本文没有重新执行或扩大这些检查。

这些证据不覆盖尚不存在的V14实现、N>=300正式协调门、完整runtime/闭包或chronology/权限状态机，也不是预测能力或历史命中证据。初版helper在项目import前因Darwin环境键名检查失败，失败原件已保留；v2只修正系统键检查、说明及新输出路径，未修改科学算法。不得将初版失败删去或把其当作第一次正式worker。

R14之后必须继续逐项真实验收，而不是凭上述局部PASS放行I14/K/授权。整项Goal不因准备完成、合成通过或普通合并而完成；只有本依据限定的合法历史五组capture，经过完整审计、冻结、最终报告与已登记的一次中文通知成功，才可能满足用户授权的多组Goal完成条件。
