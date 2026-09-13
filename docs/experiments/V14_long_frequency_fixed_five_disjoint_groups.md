# V14 固定五组历史实验：操作登记

本文件、[完整科学依据](../research/V14_long_frequency_fixed_five_disjoint_groups_basis.md)与[机器封印](../../evidence/research_registrations/v14-long-frequency-fixed-five-disjoint-groups-v1.json)共同定义本次 R14 登记。登记检查点状态为 **REGISTERED / NOT IMPLEMENTED / NOT AUTHORIZED / NOT SCORED**。登记本身不授予历史读取、正式尝试、lease、工作流、实时预测或邮件权限。

操作对象的 schema_contracts、identity、path_sets、startup、scientific_ledger 及 normative_sections 是完整规范；机器封印绑定科学和操作对象的实际摘要，以及本文件与全部登记路径的准确字节。下列 A–P 节保持已准备操作源 v3 的规范内容，未根据任何 V14 结果修改。

原操作稿作者为 `/root/v13_auth_helper_readiness_review`，贡献 session 为 `v14-operational-registration-authoring-20260913`；`/root` 负责登记整合，通知设计另有两次已标明的贡献 session。机器封印的 preparation_provenance 与源提交的作者记录列出全部实际科学、操作、测试及继承准备作者。操作对象内部的局部作者表不能代替完整作者集，也不是独立审查结论。尚未发生的实现、授权、部署和运行检查点均不得从本登记推定。

## A. 科学身份、输入与尚不存在的 Git 检查点

固定 experiment_id=`V14_long_frequency_fixed_five_disjoint_groups`，model_id=`v14_long_frequency_fixed_five_disjoint_groups`，model_version=`v14.0.0`，selector_id=`fixed_snake_top30_v1`，seed=649。probability_source_name=`long_frequency`，probability_source_version=`v1.0.0`（既有config标签，不是假称模型类有version属性），probability_adapter_version=`v14.0.0`，feature_set_id=`v14_long_frequency_full_prefix_strength250_inherited_features_v1`。这些字段与最终科学对象一致，说明既有概率来源及新适配/选组身份，不伪称独立V1对照。 最终科学对象采用`experiment`键，本操作合同的`experiment_id`是该值的固定等价字段；其余预测科学身份使用科学对象原键名。最终科学JSON作者源SHA为`eea3c0e7e4c5ba93859757e4e994d9d8be1a3a5f7f8b071a89d9bf57e28e60f1`，当前仅只读核对，不赋予运行权。

本稿以科学v2外部源 SHA-256 `92c8b07dcd0b02b7998ce9d0f092292a25040b6f429d7e7de833e61da25f6fac` 为输入，并纳入父代理本轮在任何V14结果之前明确接受的分阶段审计解释：运行内完整审计通过后可冻结暂定三scope p与12CI；只有外部独立审计通过后才确认最终Reject/conditionpass。外部失败另写不可变审计终态，原暂定数值保留为未验证值，不重跑或覆盖。这一解释必须同时写入最终R14科学对象，不修改概率、250强度、五组、目标、指标、阈值或停止规则。

固定历史身份/日期摘要完全采用科学对象中明确的4444期权威 `4a617f2c1575a165b42878600753a01ddf2ced03`；目标为2020–2025的627期与314/313固定两半。此时只允许读取该登记元数据，不读取历史/结果载荷。历史仍为consumed diagnostic，所有2026数据不进入目标前缀或评分。

R14 base 固定为PR56真实普通合并 `b1c99b02d9e18ca66b806b00c41a739daeae6740`（有序父05986709848b08e069ba14eea832143f14a075f6、924a19b59c220e339d899750eb81ca4d79e6bdec）；最终整合必须以真实Git对象再次核验，不能改成后来任意main。I14、K_H14、A_H_s14、M_A_H14、L_H14、W14等仅是将来从真实Git图解析的符号，不得猜测或预埋不存在的OID。R14中pure_core首次冻结策略明确为I14，不能填V13core或任意占位SHA；R时core/implementation/closure状态为not_implemented，而auth源必须包含真实I后非null摘要。R本身不能启动。

前置来源固定M为 `182a4245bbaf0c444ef1e16c1b5beb120eec327f`，旧V13 registration SHA `36543acd288418c0cfbf561024b2ca60fa483b8aae6a6988026b76dde861e759`。仅借鉴源码/数学元数据与精确API结构；旧auth、lease、评审PASS、canary、worker和通知权限不继承。

## B. 精确路径、阶段与源码来源

R14固定新增：

- `docs/experiments/V14_long_frequency_fixed_five_disjoint_groups.md`
- `docs/research/V14_long_frequency_fixed_five_disjoint_groups_basis.md`
- `config/research-v14-long-frequency-fixed-five-disjoint-groups.yaml`
- `tests/test_v14_registration.py`
- `evidence/research_registrations/v14-long-frequency-fixed-five-disjoint-groups-v1.json`

R14固定修改且仅这三个既有状态/协议文档：`docs/CODEX_HANDOFF.md`、`docs/MODEL_PROTOCOL.md`、`docs/RESEARCH_ROADMAP.md`。ARCHITECTURE、OPERATIONS、现有config/workflows/生产代码不改。解析置换基准限定例外、单一概率源和仅G1–G5的Goal capture衔接须在这次科学登记中明确，不沿用V13十gates或暗中加入经验票。

预登记来源档案固定为18个ADD，根 `evidence/research_preparation/v14-fixed-five-20260913/`，详见下方精确清单。来源copy-plan SHA-256为 `a53b8e23eb51f597d646310ec9813c09b4c400dfcb77e03c2055ff6ff026f662`。实际R差集精确26路径：五固定ADD、三固定MOD、18档案ADD。每项path/git_blob/bytes/sha256精确四键进入最终registered_files；ADD/M状态另由唯一source-parent Git diff与固定path_sets逐项核验，不写入record，seal自身排除所以该表25项；不得用目录通配符或运行时发现补项。这些是源码/数学/合成/审查材料，不是canonical真实预测。


固定18个准备档案（共同根见上方）为：

| 文件名 | 来源SHA-256 |
|---|---|
| `pre-outcome-concept.md` | `687889c948d9351c012a4e291c905ee4d469d87a5d8e25f2ea34cc7d5edb4e89` |
| `source-map.md` | `986b238a6d7424ff02089a8a8576bf00ca0887fd5f9eafc09f805747f95a2fda` |
| `science-v2-original.md` | `92c8b07dcd0b02b7998ce9d0f092292a25040b6f429d7e7de833e61da25f6fac` |
| `math-contract.md` | `65144487d26e4f889759e9b8d61304a8983b04361ff005b3524f9b09a8ac3c8c` |
| `math-oracle.py.txt` | `6c84f5827b45ddb8384945f7463456fbcdd10d8c75686beaaea9c347f5fe87e3` |
| `math-oracle-result.json` | `26848efeb56618195b0da11ca3dac8ea2171b60d7f09ffcc2d12a6a81bc09a8d` |
| `independent-math-review.md` | `ee622a61a5a5cbfbf7733a369905e26ccb960307cd8f3b54f62765a3864c0176` |
| `independent-science-v2-review.md` | `2b80b084e3fe03d81175d17e8a686d9d2a7b13236f1e34f69203c5bc12043884` |
| `synthetic-validator-v1.py.txt` | `b0a4edd72108b92f8912d5b168d0ca4351a41730185e0c4c5c9dbaf150074d26` |
| `synthetic-v1-failure.json` | `995a4138ca6d08a2c161d1b420ab977fd3437638e94c87e8df2dbaeb4a5612ac` |
| `synthetic-validator-v2.py.txt` | `b049983864a89b1f29f67cc26bdb01f7e82396707055f02b08e63af2d979b701` |
| `synthetic-v2-result.json` | `e1617d6d22f43b1f6abe11fff647e4664037025a2a8e164464375a3651e9d3e4` |
| `synthetic-v2.log` | `44e9467611513d577320e3da31646a3919629e920e0b33272f669b80e609f414` |
| `synthetic-static-review.md` | `46c445f8367faa6612e3cbd5acb33affbc4384217baaef620c51fc14660ba969` |
| `synthetic-v2-static-delta-review.json` | `fa4aa0446b63e0cbda3c6d8583de43bc5ddab38707df44dfd4cdba23b6cce9f1` |
| `original-operational-map.md` | `7bb87c8b945c1c233d298ee5c31f99fecfabfb924db391045d41bdf6c26d70c4` |
| `README.md` | R14整合时真实J以外的Markdown字节摘要；无future自身OID |
| `manifest.json` | 已准备原件SHA `cc1f7e91d891c79c17e0b37ec5c223e1882b6e3c73cd29041260df668b07df0a`；绑定16个原件，不含README或自身 |

已准备manifest精确为PreparationArchive五键 `{schema_version,scope,registered_or_runtime_authority,archive_prepared_at_utc,files}`，schema_version=`lotto649-v14-preparation-original-byte-archive-v1`，registered_or_runtime_authority=false。files是16个PreparationArchiveFile，精确四键 `{path,source_path_at_preparation,bytes,sha256}`，path为本档案目录内文件名，保持真实manifest原顺序；source_path_at_preparation只记录当时来源，不能作为运行时动态读路径。实际时间保留原`2026-09-13T20:33:08.641658+00:00`，本历史元数据对象不受新运行UTC字符串格式改写。README和manifest本身由R registered_files单独绑定。README只说明真实来源/先前失败/合成范围与作者，不添加新结果；16原件和已准备manifest字节均不改写。准备synthetic v2 PASS来源SHA `e1617d6d22f43b1f6abe11fff647e4664037025a2a8e164464375a3651e9d3e4`仅覆盖7个假fixture、15个畸形输入、29个概率箱边界；不代表完整runtime协调、注册/运行或真实预测通过。

seal用完整ls-tree mode/type/oid/path保留R base除上述精确差集外的一切对象。registered_files不含seal自身，防自指；每项验证唯一ordinary source父提交及ADD/M状态，来源作者trailer与seal贡献者一致。R时未来I九路径、auth、六canonical输出、capture/通知namespace均必须不存在；这项缺席测试针对真实R源tree，不能在I或授权后错误要求它们仍缺席。origin从唯一不可变ADD解析；删除/重加/变更再恢复均不允许。

I14 base-to-head严格九个新增路径如下；没有其他src/test/workflow变化。若实现需要第十个路径，先关闭未运行设计并重新登记相应源规范，不能在I静默扩项。

| I14路径 | 职责 |
| --- | --- |
| src/lotto649/models/v14_long_frequency.py | 一次调用固定LongFrequencyModel的窄适配及严格输入/49概率验收 |
| src/lotto649/v14_five_group_selection.py | 纯选择core：实际float排序、Top30、固定蛇形G1–G5，不接收答案或IO |
| src/lotto649/v14_evidence.py | 闭合快照/评分/新精确整数null/12CI/摘要/渲染 |
| src/lotto649/v14_registered_attempt.py | 新历史权威/entry/lease/ledger/worker/capture身份；通知仅引用独立N部署封印，不在历史进程启动SMTP |
| tools/run_v14_historical.py | 固定隔离入口，无任意参数或单独授权 |
| tests/test_v14_probability_selection.py | 纯合成概率/选组/类型/前缀合同 |
| tests/test_v14_evidence.py | 纯合成科学算术、全部输出与null终态 |
| tests/test_v14_registered_attempt.py | 纯合成Git/HTTP/阶段/所有权/失败/一次通知 |
| tests/fixtures/v14_git_commit_projection.json | 固定Git投影的合成fixture，不含开奖答案 |

pure_core_path=`src/lotto649/v14_five_group_selection.py`，其SHA首次在真实I14冻结。九文件manifest和完整closure同时硬绑定概率适配、旧LongFrequencyModel及新证据算术，不能以selector core未变为理由更改概率/统计行为。概率与选择是两个真正分离接口；factory、four_forecasts、V13core、旧Top12单组select_combination均不调用。

继承的旧概率源码仍使用M固定LongFrequencyModel.predict的mean*N/250/normalize流水线，feature_frame额外列计算也不删。旧源码SHA：baselines `76f9050a13bde44d51584397ecd6acb358f320e1617ef329b70bd6a22d23e28a`；base `e2f0c90c376ea6063b906bcca042e8903b351a1ed4b76e9d83e17be3bcf166ec`；features `b7bc67b9038b2e3d78230c3087c3ac4e3f17751aeab678574f3601af00671979`；domain `fbcb22747ae361767df070c6e50af49fda1aa190b72fd39894afa1c879a50b7a`。旧optimizer源码可仅因实际静态依赖进入closure，不允许调用其选组API。

auth唯一新路径为 `evidence/research_authorizations/v14-long-frequency-fixed-five-disjoint-groups-v1-historical.json`。

唯一正式 child 命令（现在禁止执行）：`python3.12 tools/run_v14_historical.py --consume-v14-once`。注册的独立 supervisor 入口为同一个文件的 `supervise_v14_once()`，精确调用 `python3.12 -I -S -B tools/run_v14_historical.py --supervise-v14-once`；它负责先审启动环境、独占持久化entry及一次Popen，不是第二个历史worker。这个监督入口也只有实际M授权后可用，不授予登记前真实探针/正式启动权。historical ref固定 `refs/heads/v14-consumption-v14.0.0`。两个入口分别只接受本段各自完整固定argv；除此没有flag、目标区间、模型/seed/root/clock/收件人覆盖或继续/重试命令。直接运行normal child且缺少当前受审supervisor的一次内核FD交接必须拒绝，不能自建entry。

正常worker最终六角色共用前缀 `reports/v14_long_frequency_fixed_five_disjoint_groups_v14.0.0_historical`：startup `.startup.jsonl`；claim `.claim`；ledger `.ledger.jsonl`；JSON `.json`；Markdown `.md`；manifest `.commit-manifest.json`。entry在startup，generation-intent在ledger，不增第七canonical文件。staging精确为JSON/Markdown各自终路径加`.staging`；Git构树index精确为manifest终路径加`.index`，仅当前owner创建；成功仅删除已认证自身staging/index，不覆盖终文件。失败或未知保留残留，不清理、领养或换名重试。六角色是完整成功/可完整封存attempt的集合，startup失败不得伪造其余五文件凑数。

capture后固定新增三文件：`reports/historical-five-group-6of6-candidate__{target_date}__v14.0.0.json`；`evidence/research_audits/v14.0.0/historical-five-group-6of6__{target_date}.json`与同stem`.md`。无capture的外部closure audit固定为 `evidence/research_audits/v14.0.0/historical-terminal-audit.json`及`.md`；均在worker已退出后新建，不属于worker六文件，也无启动权。

notification ref固定 `refs/heads/v14-notification-v14.0.0`；文件为 `evidence/research_notifications/v14.0.0/historical-five-group-6of6__{target_date}.intent.json`、`.journal.jsonl`、`.result.json`。一版本只允许首次已审capture的这一组路径；不能另开目标、组ID或失败文件名来获得第二次发送机会。


独立通知部署的强制顺序为 `R14 < R_N14 < I_N14 < K_N14 < I14 < K_H14 < A_H_s14 < M_A_H14 < L_H14 < run_H14`。R_N14是独立通知操作登记，不改变R14科学公式/五组/统计；其新增路径在R14缺席的base之外，旧preserved对象不动。I_N14只实现该精确通知deployment，普通合并K_N14完成准确CI与双轴0B/M；I14唯一base必须K_N14，保持历史九路径与A仅一个auth新增。N阶段本身无历史读取/预测权，也不能先发送一封真实capture邮件作canary。

Auth新增notification_deployment对象（18键）：`registration_commit,registration_sha256,implementation_base,implementation_commit,implementation_merge,implementation_files,implementation_files_sha256,runtime_contract,runtime_contract_sha256,runtime_dependency_closure,runtime_dependency_closure_sha256,workflow_path,workflow_sha256,entry_path,entry_sha256,review_records,readiness_records,protection_reader`。它的registration/source/merge均为真实完整OID，files/closure分别ImplementationEntry/ClosureEntry，review_records为R_N14所规定的实际两轴部署评审；runtime_contract是R_N14封印的闭合最小通知runtime对象，不是历史Runtime别名。全部J摘要作为StartupIdentity.notification_deployment_sha256及外部ClosureAudit同字段。R_N14未来才能有真实SHA，R14只冻结必需类型/关系；历史Auth中任何未解析/null/占位一律拒绝。

N部署与历史实现分别冻结：K_N14/I14/K_H14/A/M/capture publication每个检查点N所有静态源码/blob/closure/运行契约与保护reader身份均相同（真实阶段readiness证明按本节先后生成，不把未来证明预埋进I）；历史core/closure仍从I14首次冻结。通知验证器核对原科学CPython3.12.11/macOS的**已冻结执行身份与证据**，不能要求SMTP任务的实际平台也是macOS，也不得在Ubuntu邮件任务中import/fit/执行科学模型。通知自己的Python/stdlib/依赖/launcher/workflow及GitHub runner身份由R_N14独立严格冻结，未知/漂移仍fail closed。默认sender源码可以同一`notification.py`，它只依赖stdlib；但安全验证/发信进程只能使用N已审最小closure。

通知CI只能验证source、合成artifact/audit/HTTP/SMTP stub、Secrets名称/权限映射与workflow绑定，不读取Secret值、不真实send、不读取V14真结果。正常历史worker只携带GitHub凭据及本规范内部一次交接的非Secret元数据；真实SMTPSecret只在符合N部署当前main/审计/一次标记前提的job环境注入。R_N14部署具体路径/runtime/权限和闭合schema的独立合同仍须在最终历史I/K/A前完成，不能借此条文视为已经实现。


R_N14/I_N14的路径已明确固定，必须在R14源tree全部缺席；只允许下列介入路径，不能当作任意新增后继代码许可：

- R_N14 exact2ADD：`docs/experiments/V14_capture_notification_delivery.md`；`evidence/research_registrations/v14-capture-notification-v1.json`。
- I_N14 exact6ADD：`.github/workflows/v14-audited-capture-email.yml`；`.github/workflows/v14-notification-readiness.yml`；`src/lotto649/v14_capture_notification.py`；`tools/notify_v14_audited_capture.py`；`tests/test_v14_capture_notification.py`；`tests/fixtures/v14_notification_git_projection.json`。

R_N14源绑定已实际存在的R14科学/操作/capture-schema摘要，经普通注册merge M_R_N14；I_N14唯一parent为M_R_N14，K_N14有序父为M_R_N14/I_N14且tree等I_N14。R14本身的唯一源ADD原点和普通发布merge由Git解析，不能把source和merge混为一个OID。N代码不得嵌入未来I14/M_A_H14 SHA；它以后从真实Auth解析并核对图，Auth反过来绑定已经存在的K_N14，无digest环。

源设计输入 `/private/tmp/v14-default-notification-route-map-20260913.md` SHA `137ad00dbed48c4f8330b8eb244d2ff0a89dda95051f6b7a394c68e92732e7cf`，作者 `/root/v14_default_notification_route_map`、session `v14-default-notification-route-map-20260913`，应列为R14操作实质贡献而非独立审查；只作为作者输入引用，不增加26路径中的第19档案。

生产通知入口固定 `python3.12 -I -S -B tools/notify_v14_audited_capture.py`，无参数；readiness仅追加一个精确字面量 `--verify-deployment-readiness`，验证器自身GET-only、无SMTPSecret/仓库状态写入/canonical通知文件或生产capability；独立App token生命周期允许下述R_N明确封印的mint POST/revoke DELETE，不能把完整workflow称作端到端GET-only。拒绝其他argv。两个workflow都仅无输入workflow_dispatch、固定repo/refs/heads/main/path、run_attempt=1、cancel-in-progress=false，所有action固定完整commit SHA、full-history checkout且persist-credentials=false；不能用concurrency代替远端唯一标记。

R_N14须先冻结Linux/amd64不可变OCI平台manifest digest、CPython3.12.11可执行文件/stdlib、Git/OpenSSL/CA、source/import closure与action SHA，以及准确GitHub API/权限矩阵。这里没有已验证image/action SHA，不能编造；它们只能在R_N14真实源封印后作为NotificationDeployment.runtime_contract的严格闭合内容进入Auth。生产无network pip/install，无科学第三方包；实际host内核/GitHub执行信任边界单列，不称OCI冻结全部host。

K_N14后、I14源提交前必须真实完成无SMTP的readiness workflow qualification；其NotificationReadiness（12键）由已审N协议产生，初次head_sha必须K_N14、A前新记录head_sha必须K_H14，run_attempt=1/result=pass，workflow/path/SHA/run/check/artifact来源全验证。required_gets是R_N14固定权限矩阵顺序的ReadinessGET（3键）列表，须实际验证repo/main/protection/commit/ref/CI/PR/comment等所需GET，403/未知不可用旧归档值或宽松接口绕过。mutation_permitted_by_service=true还需credential_permission_basis_sha256绑定已登记服务权限依据，不能把GET成功伪造成实际createRef测试成功；不能为readiness创建消费/通知ref。凭据有不足时先以最小权限明确部署并重新R_N验收，不读取token/SMTP值。

GitHub公开权限合同已说明，普通Actions GITHUB_TOKEN没有Administration权限项，无法据已公布合同执行所需GET /branches/main/protection或/protection/enforce_admins；read-all/write-all也不增加这个权限。不能登记一个已知不可满足的默认GITHUB_TOKEN-only保护核验。默认GITHUB_TOKEN仍只负责它支持的仓库读取及已授权通知claim操作；保护读取另有repository-only、Administration:read的短期GitHub App installation token，App只安装到Jasper-Shi/lottopred，不能授予settings写权限、读取别的仓库或改变邮件路线。

NotificationDeployment.protection_reader为NotificationProtectionReader（13键）：kind固定github_app_installation_read_only_protection；repository固定Jasper-Shi/lottopred，repository_id/app_id/installation_id必须在未来R_N按真实服务身份封印；permissions精确ProtectionPermissions={administration:"read"}。credential_slots精确记录未来R_N选定的App私钥Secret名称及App/installation ID变量名称，不含其值。helper_files只有已登记I_N六路径内实际承担token注入/核验的文件引用，SHA和独立通知runtime绑定；R14不捏造这些ID、Secret槽、helper/action或image摘要，也不宣称已有配置可用。无法真实部署该独立能力时是历史授权的真实blocker；不读Secret、不跳过保护、不用旧截图/缓存或宽松endpoint作替代。

该App token仅送入专用固定-origin GET-only保护adapter，read_paths精确为`/repos/Jasper-Shi/lottopred/branches/main/protection`与`/repos/Jasper-Shi/lottopred/branches/main/protection/enforce_admins`，拒绝其他host/repo/branch/redirect/HTTP方法，不共享给通知claim writer。默认GITHUB_TOKEN不能作为这两个GET失败后的自动替代；App token也不能拿去写claim/修改保护。两种GitHub凭据与SMTP_USERNAME/PASSWORD隔离，任何adapter都不记录Authorization/token/private-key值。

token_lifecycle为ProtectionTokenLifecycle：mint_method=POST、mint_path=`/app/installations/{真实已封installation_id}/access_tokens`，mint_body精确ProtectionTokenMintBody={repository_ids:[真实固定repo_id],permissions:{administration:"read"}}；JWT来自唯一App私钥槽的受审运行时处理。max_lifetime_seconds=3600，记录服务实际expires_at且过期/范围不符拒绝；revoke_method=DELETE、revoke_path=/installation/token。helper_action_sha须在独立R_N固定完整不可变action/helper SHA并在I_N核验。本生命周期API与历史/通知claim的POST槽完全分离，只能在固定no-SMTP readiness或实际capture通知job中，由已封helper执行；禁止任意token权限/安装/仓库参数。完整readiness可mint/revoke凭据，仍不得创建消费/通知ref、改仓库/branch保护或发送SMTP，不能标成端到端GET-only或无外部状态动作。

初次N qualification在K_N14、I14源提交前；A_H_s14前还需当前K_H14上的新无SMTP保护权限/部署readiness记录。Auth的NotificationDeployment.readiness_records按此顺序恰两条NotificationReadiness，第一head_sha=K_N14，第二head_sha=K_H14，均run_attempt=1、实际completed/pass，且workflow/runtime/static N源码相同。I14入口门只要求第一条真实记录；完整Auth需要两条，不能在I时预填未来run。N静态源码/运行契约/保护reader身份在K_N/I/K/A/M完全不变；readiness记录是各真实阶段新产生的安全证明，不错误要求尚未存在的完整Auth证据对象在I时就字节相同。每个记录credential_permission_basis_sha256必须绑定R_N固定的保护reader与默认GITHUB_TOKEN各自职责，并有实际新鲜GET成功；安装未授权/权限不够/403/未知均阻断后续I或A，不能仅凭配置声明可用。实际捕获通知发送前仍以新的短期token再次执行两个GET，不能用预授权记录代替当前保护状态。

这一权限差距及方案是新操作来源贡献：`/private/tmp/v14-github-protection-token-capability-20260913.md`，SHA-256=`0be5387835290e41bc1dc8d3673d73be227e66dde6f4186c09e1b0ede00dcece`；作者`/root/v14_default_notification_route_map`，任务内session=`v14-github-protection-token-capability-research-20260913`。来源为GitHub官方branch-protection REST权限说明与Actions GITHUB_TOKEN permissions语法；不把这次source-only调查说成已配置App、已取得token或已运行readiness。该新贡献进入R14实际完整作者集，不扩张26个R路径或9个历史I路径，SMTP默认Secrets/服务器/收件人规则不变。

生产流程先有无SMTP/source/runtime/evidence检查，再仅在固定send step由默认GitHub Secrets映射注入SMTP_USERNAME/PASSWORD；每步重复必要核验，不能把早期step输出当可转移capability。R_N14同时冻结allowlisted Actions run/workflow/attempt/source/container元数据，将真实run_id与run_attempt绑定通知identity/receipt的外部执行证明：本R14 notification身份通过新字段notification_execution绑定它，字段定义见下；不能从可伪造环境单独信任job身份。上传步骤在always且有文件时保留原intent/journal/result/manifest，固定run-id artifact名、固定upload action、无SMTP环境；upload失败不重发，ephemeral runner丢失明确记unknown/证据丢失，不能仅凭远端claim宣称Goal完成。

## C. 序列化、类型与完整闭合schema目录

C(x)=UTF8 JSON、ensure_ascii=false、keys按字典序、separators(',',':')、finite only；J(x)=C(x)+恰好一个LF。拒绝重复/未知/缺失键、非finite、非UTF8、CR/多余LF、bool冒充整数、字符串/float强转整数。所有声明对象无optional键，除明确的Git POST响应例外。键顺序由C决定，数组按下文固定顺序，不能排序掉科学顺序。

OID为小写40hex、SHA为小写64hex；整数为原生int且域内（JSON反序列化须排除bool）；float为原生有限binary64，概率另须0<p<1且math.fsum49项距六≤1e−12。所有UTC内部生成，格式YYYY-MM-DDTHH:MM:SS[.ffffff]Z，按实际时间非递减；Git identity为整秒Z，raw +0000。日期是严格ISO且目标固定登记表内。路径是注册的POSIX相对路径，无空片段、..、反斜杠、绝对路径或symlink。

下面count由实际列表长度推导，不继承V13数目；嵌套值只能取本目录对象、明确固定键映射或规范科学对象，不能塞任意extension。含schema_version键的新运行对象默认使用`lotto649-v14.0.0-<schema-name-kebab>-v1`，名称经CamelCase转kebab（如StartupEvent→startup-event、CI→ci）。明确例外：Seal=`lotto649-v14-registration-v1`；Config=`lotto649-v14-inert-config-v1`；PreparationArchive保留`lotto649-v14-preparation-original-byte-archive-v1`。ReviewComment另按R14/I14/A_H_s14/CAPTURE_PUBLICATION14给对应阶段前缀，防跨阶段使用。不存在schema_version键的嵌套记录不添加该键。

| 对象 | 键数 | 精确required keys |
| --- | --- | --- |
| ContributorIdentity | 2 | `agent_id, session_id` |
| Contributor | 3 | `agent_id, session_id, role` |
| SourceAuthor | 3 | `schema_version, phase, contributors` |
| RegisteredFile | 4 | `path, git_blob, bytes, sha256` |
| PreservedEntry | 4 | `mode, type, oid, path` |
| ImplementationEntry | 4 | `path, git_blob, bytes, sha256` |
| ClosureEntry | 3 | `path, git_blob, sha256` |
| Config | 10 | `schema_version, experiment_id, model_version, registration_path, statistical_fingerprint_sha256, operational_contract_sha256, historical_enabled, live_enabled, dispatch_enabled, default_model_activation` |
| Seal | 13 | `schema_version, experiment_id, model_version, status, registration_base, scientific_contract, statistical_fingerprint_sha256, operational_contract, operational_contract_sha256, registered_files, preserved_tree_manifest, preserved_tree_manifest_sha256, preparation_provenance` |
| PreparationProvenance | 2 | `contributors, scope` |
| PreparationArchive | 5 | `schema_version, scope, registered_or_runtime_authority, archive_prepared_at_utc, files` |
| PreparationArchiveFile | 4 | `path, source_path_at_preparation, bytes, sha256` |
| Runtime | 7 | `implementation, python_version, platform, machine, byteorder, dependency_manifest_sha256, installed_distributions` |
| ReviewRecord | 8 | `axis, check_id, comment_body_sha256, comment_id, pr_number, publisher_login, review_session_id, reviewer_agent_id` |
| ReviewComment | 16 | `schema_version, axis, base_sha, head_sha, closure_sha256, pure_core_sha256, scientific_contract_sha256, operational_contract_sha256, verdict, blocker_count, major_count, reviewer_kind, reviewer_agent_id, review_session_id, publisher_login, initial_bootstrap_sha256` |
| Authorization | 28 | `schema_version, experiment_id, model_version, selector_id, repository, branch, registration_commit, registration_sha256, scientific_contract_sha256, operational_contract_sha256, config_sha256, pure_core_sha256, implementation_commit, implementation_base, implementation_merge, authorization_base, canonical_command, governed_history_authority, governed_history_identity, runtime, implementation_files, implementation_files_sha256, runtime_dependency_closure, runtime_dependency_closure_sha256, review_records, notification_deployment, initial_bootstrap, initial_bootstrap_sha256` |
| Facts | 6 | `repository, execution_commit, source_commit, payload, authorization_sha256, authorization_review_records` |
| StartupIdentity | 22 | `repository, branch, experiment_id, model_version, selector_id, registration_commit, implementation_commit, implementation_merge, authorization_source, execution_commit, registration_sha256, config_sha256, authorization_sha256, scientific_contract_sha256, operational_contract_sha256, pure_core_sha256, runtime_identity_sha256, runtime_dependency_closure_sha256, requirements_sha256, verified_facts_sha256, notification_deployment_sha256, initial_bootstrap_sha256` |
| StartupEvent | 6 | `schema_version, sequence, generated_at, previous_event_sha256, kind, payload` |
| FileRef | 3 | `path, bytes, sha256` |
| Checkpoint | 4 | `path, sequence, bytes, sha256` |
| Binding | 12 | `authorization, execution_commit, authorization_source, authorization_sha256, authorization_review_records, verified_facts_sha256, startup_checkpoint, lease_ref, lease_commit, nonce_hex, classification, attempt_id` |
| Claim | 4 | `schema_version, claimed_at, verified_authorization_facts, bindings` |
| LeaseBody | 5 | `schema_version, authorization_seal_sha256, canonical_command, execution_authority_M_A, nonce_hex` |
| GitIdentity | 3 | `name, email, date` |
| CommitPOST | 5 | `tree, parents, author, committer, message` |
| CommitGET | 10 | `sha, node_id, url, html_url, author, committer, tree, message, parents, verification` |
| GitTree | 2 | `sha, url` |
| GitParent | 3 | `sha, url, html_url` |
| GitVerification | 5 | `verified, reason, signature, payload, verified_at` |
| RefPOST | 2 | `ref, sha` |
| RefGET | 4 | `ref, node_id, url, object` |
| RefObject | 3 | `sha, type, url` |
| LedgerEvent | 7 | `schema_version, sequence, recorded_at, previous_event_sha256, kind, payload, event_sha256` |
| PriorDrawRow | 3 | `draw_date, numbers, bonus` |
| GenerationIntent | 8 | `target_ordinal, target_draw_date, training_cutoff_date, visible_prefix_draw_count, visible_prefix_sha256, bindings_sha256, probability_source_version, selector_id` |
| Probability | 3 | `number, probability, probability_hex` |
| Group | 2 | `group_id, numbers` |
| Forecast | 26 | `schema_version, experiment_id, model_id, model_version, selector_id, probability_source_name, probability_source_version, probability_adapter_version, feature_set_id, target_ordinal, target_draw_date, history_through, training_cutoff_date, visible_prefix_draw_count, visible_prefix_sha256, generated_at, probabilities, ranking, top6, top12, top18, top30, groups, final_combination, capture_eligible_group_ids, bindings` |
| FrozenPayload | 3 | `snapshot, snapshot_sha256, snapshot_bytes` |
| SnapshotRef | 4 | `path, event_sequence, snapshot_bytes, snapshot_sha256` |
| RevealIntent | 3 | `target_ordinal, target_draw_date, snapshot_ref` |
| Revealed | 5 | `target_ordinal, target_draw_date, snapshot_ref, actual, bonus` |
| GroupScore | 3 | `group_id, hits, matched` |
| TopKScore | 3 | `k, hits, matched` |
| CalibrationBin | 8 | `lower, upper, count, probability_sum, actual_sum, mean_probability, observed_frequency, gap` |
| Scored | 23 | `target_ordinal, target_draw_date, snapshot_ref, reveal_event_sequence, reveal_event_sha256, group_scores, M, q, d, top_k_scores, mean_actual_rank, brier, brier_fair, brier_delta, log_loss, log_loss_fair, log_loss_delta, calibration, calibration_fair, capture_group_ids, final_6_hits, score_completed_at, audit_warning_codes` |
| TargetBundle | 5 | `generation_intent_event, frozen_event, reveal_intent_event, revealed_event, scored_event` |
| CaptureDetected | 8 | `target_ordinal, target_draw_date, snapshot_ref, group_ids, sorted_sixes, audit_status, eligible_evidence, global_stop_search` |
| Failure | 7 | `stage, target_ordinal, target_draw_date, reason, last_confirmed_sequence, last_confirmed_event_sha256, retry_allowed` |
| Completed | 4 | `completed_target_count, target_dates_sha256, first_generation_intent_sha256, last_scored_event_sha256` |
| ExactTail | 14 | `scope, n, total_M, numerator_hex, denominator_hex, value, value_hex, effect_numerator_hex, effect_denominator_hex, mean_M, fair_mean, lift, positive_effect, alpha_pass` |
| CI | 11 | `id, scope, n, vector_id, seed, resamples, method, lower, upper, lower_hex, upper_hex` |
| Inference | 5 | `aggregate, first_half, second_half, intervals, primary_pass` |
| BestGroupTie | 4 | `target_draw_date, group_id, numbers, hits` |
| BestTopKTie | 4 | `target_draw_date, k, numbers, hits` |
| GroupSummary | 5 | `group_id, mean_hits, histogram, best_hits, best_ties` |
| TopKSummary | 5 | `k, mean_hits, histogram, best_hits, best_ties` |
| ConditionalM | 3 | `q, count, M_histogram` |
| Summary | 22 | `n, mean_M, M_histogram, M_tail_counts, M_tail_rates, mean_q, q_histogram, conditional_M, mean_d, groups, top_k, mean_actual_rank, brier, brier_fair, brier_delta, log_loss, log_loss_fair, log_loss_delta, calibration, calibration_fair, best_group_hits, best_group_ties` |
| ScopeSummary | 11 | `scope, expected_count, frozen_count, revealed_count, completed_count, missing_count, failed_count, first_target, last_target, target_dates_sha256, summary` |
| RuntimeAudit | 5 | `complete, warning_codes, checked_source_sha256, checked_runtime_sha256, checked_ledger_head_sha256` |
| Report | 24 | `schema_version, experiment_id, model_version, selector_id, classification, bindings, expected_target_count, frozen_target_count, revealed_target_count, completed_target_count, failure_phase, stop_reason, runtime_state, provisional_scientific_disposition, independent_audit_status, audit_publication, internal_audit, ledger, targets, partial_scopes, annual_descriptive, provisional_inference, exclusions, opportunity_accounting` |
| LedgerSummary | 7 | `path, bytes, sha256, event_count, head_sha256, pending_generation, pending_frozen_target` |
| Exclusions | 3 | `burn_in_scored, known_2026_scored, unprocessed_target_count` |
| OpportunityAccounting | 5 | `group_count_per_frozen_target, unique_target_sorted_group_count, Goal_global_independent_opportunities, nominal_fair_only, exact6_probability_per_complete_target` |
| ArtifactEntry | 5 | `role, path, bytes, sha256, git_blob` |
| Manifest | 8 | `schema_version, experiment_id, model_version, execution_commit, authorization_sha256, startup_checkpoint, sealed_startup, files` |
| AuditDimension | 2 | `verdict, evidence` |
| AuditEvidence | 4 | `kind, commit, path, sha256` |
| ClosureAudit | 32 | `schema_version, experiment_id, model_version, selector_id, target_draw_date, capture_group_ids, capture_sorted_sixes, worker_artifact_commit, execution_commit, registration_commit, scientific_contract_sha256, operational_contract_sha256, pure_core_sha256, runtime_dependency_closure_sha256, claim_sha256, ledger_sha256, report_sha256, forecast_snapshot_sha256, source_contributors, reviewer_agent_id, review_session_id, audited_at, verdict, blocker_count, major_count, dimensions, limitations, authoritative_state, authoritative_scientific_disposition, authoritative_inference, notification_deployment_sha256, initial_bootstrap_sha256` |
| CaptureBundle | 19 | `schema_version, experiment_id, model_version, selector_id, target_draw_date, capture_group_ids, capture_sorted_sixes, worker_artifact_commit, execution_commit, claim_sha256, ledger_sha256, report_sha256, forecast_snapshot_sha256, audit_json_path, audit_json_sha256, audit_markdown_path, audit_markdown_sha256, audit_verdict, classification` |
| NotificationIdentity | 17 | `experiment_id, model_version, selector_id, target_draw_date, capture_group_ids, capture_sorted_sixes, notification_kind, candidate_bundle_path, candidate_bundle_sha256, audit_json_path, audit_json_sha256, audited_publication_commit, publication_tree_oid, scientific_contract_sha256, operational_contract_sha256, nonce_hex, notification_execution` |
| NotificationIntent | 12 | `schema_version, identity, identity_sha256, expected_claim_oid, raw_commit_sha256, commit_request_bytes, commit_request_sha256, ref_request_bytes, ref_request_sha256, started_at, state, retry_allowed` |
| NotificationBody | 13 | `schema_version, experiment_id, model_version, selector_id, target_draw_date, capture_group_ids, notification_kind, audited_publication_commit, audit_json_sha256, candidate_bundle_sha256, intent_identity_sha256, operational_contract_sha256, nonce_hex` |
| NotificationResult | 13 | `schema_version, experiment_id, model_version, selector_id, target_draw_date, capture_group_ids, notification_kind, intent_sha256, claim_commit, sealed_journal, completed_at, result, retry_allowed` |
| TerminalObservation | 11 | `schema_version, phase_enum, result_enum, attempt_entry_confirmed, generation_intent_confirmed, process_exit_observed, retry_allowed, process_role, normal_child_spawn_intent_confirmed, popen_attempted, child_pid` |
| NotificationDeployment | 18 | `registration_commit, registration_sha256, implementation_base, implementation_commit, implementation_merge, implementation_files, implementation_files_sha256, runtime_contract, runtime_contract_sha256, runtime_dependency_closure, runtime_dependency_closure_sha256, workflow_path, workflow_sha256, entry_path, entry_sha256, review_records, readiness_records, protection_reader` |
| NotificationReadiness | 12 | `workflow_path, workflow_sha256, run_id, run_attempt, head_sha, check_id, artifact_sha256, completed_at, credential_permission_basis_sha256, required_gets, mutation_permitted_by_service, result` |
| ReadinessGET | 3 | `route, status, verified_identity_sha256` |
| NotificationExecution | 8 | `deployment_sha256, workflow_path, workflow_sha256, run_id, run_attempt, event_sha, runtime_identity_sha256, execution_metadata_sha256` |
| InitialBootstrap | 17 | `schema_version, python_version, normal_executable, executable_aliases, launcher_path, launcher_git_blob, launcher_sha256, supervisor_function, isolated_supervisor_command, normal_child_command, isolated_child_command, environment_policy, runtime_inventory, runtime_inventory_sha256, active_startup_paths, sterile_probe, credential_provider` |
| BootstrapEntry | 8 | `path, kind, mode, uid, gid, bytes, sha256, link_target` |
| BootstrapDirectoryChild | 2 | `name, kind` |
| BootstrapEnvironment | 3 | `fixed_variables, credential_variable, handoff_variables` |
| BootstrapFixedEnvironment | 7 | `PATH, LANG, LC_ALL, TZ, PYTHONNOUSERSITE, PYTHONSAFEPATH, PYTHONDONTWRITEBYTECODE` |
| BootstrapProbe | 4 | `argv, code, code_sha256, response_schema` |
| BootstrapProbeResult | 19 | `schema_version, executable, real_executable, prefix, base_prefix, sys_path, module_origins, exec_prefix, base_exec_prefix, site_prefixes, enable_user_site, safe_path, no_user_site, no_site, dont_write_bytecode, sitecustomize_file, sitecustomize_cached, usercustomize_loaded, project_loaded` |
| BootstrapModuleOrigin | 2 | `name, origin` |
| BootstrapCredentialProvider | 5 | `executable, executable_sha256, argv, allowed_configuration_environment_names, fixed_environment` |
| PrelaunchProof | 14 | `schema_version, verified_at, execution_commit, implementation_commit, source_root, source_manifest_sha256, runtime_identity_sha256, bootstrap_contract_sha256, bootstrap_inventory_sha256, sterile_probe_sha256, environment_policy_sha256, supervisor_pid, supervisor_source_sha256, sterile_probe` |
| SupervisorHandoff | 7 | `schema_version, supervisor_pid, child_pid, spawn_nonce_hex, startup_prefix, bootstrap_contract_sha256, environment_policy_sha256` |
| NotificationProtectionReader | 13 | `schema_version, kind, repository, repository_id, app_id, installation_id, permissions, credential_slots, token_lifecycle, read_paths, helper_files, helper_files_sha256, runtime_contract_sha256` |
| ProtectionPermissions | 1 | `administration` |
| ProtectionCredentialSlots | 3 | `app_private_key_secret_name, app_id_variable_name, installation_id_variable_name` |
| ProtectionTokenLifecycle | 7 | `mint_method, mint_path, mint_body, revoke_method, revoke_path, max_lifetime_seconds, helper_action_sha` |
| ProtectionTokenMintBody | 2 | `repository_ids, permissions` |

类型域与嵌套合同：

- Seal.status恰为顺序固定四字符串数组`["REGISTERED","NOT IMPLEMENTED","NOT AUTHORIZED","NOT SCORED"]`；scientific_contract/operational_contract为R冻结的闭合对象；preparation_provenance为PreparationProvenance。Config的historical_enabled/live_enabled/dispatch_enabled/default_model_activation四项必须literal false；它是J格式JSON（同时有效YAML），只含固定标识、两项digest与四个禁用开关，不能被live/CLI读取。Seal/Config的statistical_fingerprint_sha256等于SHA256(J(scientific_contract))；后续运行记录中scientific_contract_sha256是同一摘要的明确别名，不是另一份科学合同。所有future Git身份只在后续auth取得，不放入R seal自身形成环。
- ContributorIdentity为真实agent/session身份对，1..256 UTF8bytes、无边缘空格/控制字符，列表按UTF8(agent,session)排序且去重，1..64项；SourceAuthor.contributors只用该二键记录。PreparationProvenance.contributors只用三键Contributor，增加真实role，不增加隐藏scope键；scope为非空安全文字，完整披露source/math/synthetic范围、旧已消费结果暴露与非全局blind性质。来源材料SHA/路线图作者详述在规范正文及固定archive，不扩张Seal顶层或PreparationProvenance键集。root实际session_id=`01a07e02-2cf6-77f2-92ad-125229fa0a95`，role注明逻辑阶段`root-v14-registration-integration-20260913`；本作者和通知路线图作者使用已明确声明的任务内贡献session标签，不宣称它们是平台CODEX_SESSION_ID。不同阶段/新标签不使作者恢复独立审查资格。
- Runtime.installed_distributions的完整键/版本恰与最终科学合同的27项相同；不允许额外或重复归一化名称。各FileRef/ArtifactEntry字节数为非负int、SHA为真实J/原始文件字节摘要，ArtifactEntry.git_blob是实际Git blob OID。
- Auth各digest/OID非null、scope固定，review_records恰两个I14 ReviewRecord按standards/spec顺序。Facts.payload为Auth，authorization_review_records恰两个A_H_s14记录。Binding.authorization是完整Auth，分类为`consumed_historical_diagnostic_only`，attempt_id等于startup首个完整J行SHA，不能先填自身循环值。Claim.bindings为Binding，verified_authorization_facts为Facts，其J摘要精确等于绑定值。
- StartupIdentity中全部身份来自已认证Facts/本地runtime，不能由调用者参数提供。Checkpoint绑定startup序列0..12完整前缀的实际bytes/SHA，sequence必须12；FileRef sealed_startup绑定0..15全部字节。SupervisorHandoff内的startup_prefix是专门的早期Checkpoint，sequence必须2，不能当claim checkpoint。seal、runtime manifest等摘要编码见D。
- Probability列表恰49项，number为1..49升序原生int，probability_hex必须float.hex值精确匹配；输入dict在转数组前仍必须原生int键恰1..49。ranking恰49号排列；Top6/12/18/30为其对应前缀。Group列表恰按G1..G5，每组numbers为升序六个不同int，组间交集空、并集Top30；final_combination等于G1；capture_eligible_group_ids恰[G1,G2,G3,G4,G5]。固定蛇形排名位置完全按科学合同，不能按概率和/命中重排。
- Forecast.generated_at是概率与选组完成后的真实UTC；冻结UTC为外层LedgerEvent.recorded_at，生成时间≤冻结时间。Forecast.bindings完整Binding；FrozenPayload.snapshot为Forecast，其J字节长度/摘要等于snapshot_bytes/sha。SnapshotRef引用固定ledger路径及唯一prediction_frozen事件序号，标识该事件内J(snapshot)的bytes/SHA；它不声称存在另一个文件。逻辑快照由ledger原字节固定且可独立提取重建，不增第七文件。
- Revealed.actual升序六不同int，bonus按已验证权威保留合法原生int且不计主号；不允许因缺失随便补null。GroupScore列表G1..G5与每组匹配号升序；TopKScore列表k=6,12,18；hits等于matched长度。M=max五H，q=Top30命中=ΣH，d及B/L等严格采用科学合同算术。final_6_hits仅H1。capture_group_ids恰为实际H=6的固定ID列表，至多一项；空是[]，不是null。
- CalibrationBin每组恰10行固定边界，count/actual_sum原生非负整数；空桶count/和0，mean/frequency/gap为null，其余值按科学合同fsum顺序。calibration与calibration_fair都完整。Scored不复制/改变快照，仅引用原冻结/揭晓事件；score_completed_at≤外层评分event时间。audit_warning_codes只有登记enum，正常为空。
- TargetBundle保存同一ordinal的五个完整LedgerEvent；其中snapshot为冻结的原完整对象、actual在revealed_event中。所有sequence/digest/日期/前缀/类型相互吻合，不按后验表现过滤。未完成当前期只在ledger与failure上下文中保留，不造TargetBundle或M=0。
- 计数直方图使用固定字符串键0..6；尾count/rate固定键3,4,5,6。GroupSummary恰5，TopKSummary恰3，ConditionalM恰q=0..6。每种best_ties按date再固定group/k顺序保留全并列；n=0均值/best_hits为null、ties空、计数0。Summary全部数值/年度/并列按科学合同，无额外p/CI。
- partial_scopes恰aggregate/first_half/second_half三个ScopeSummary；annual_descriptive恰字符串2020..2025映射同Summary，只有描述。各scope首末/date digest是固定预期范围，n由有效完成前缀真实计数；missing/failed不补数。Report.targets包含所有完整TargetBundle，不含重新预测。
- ExactTail使用完整非负整数hex分子/分母和值hex；效应分子可带负号hex，分母正；判定使用整数，不比较显示小数。Inference恰三个ExactTail或全null，intervals恰科学合同固定ID順序12个CI或null，primary_pass为bool或null。每个CI固定seed649/resamples10000/method linear，n、vector_id及端点hex精确吻合。不得只null失败scope保留已完成半区间推断。
- OpportunityAccounting不是Goal全局显著性：group_count_per_frozen_target=5；unique_target_sorted_group_count按实际完整冻结5组去重；Goal_global_independent_opportunities=null；nominal_fair_only=true；exact6_probability_per_complete_target为精确字符串`5/13983816`。没有独立V1/random实选组。
- ClosureAudit.dimensions恰chronology,target_exclusion,future_exclusion,preprocessing,feature_selection,model_selection,immutability,git_provenance,runtime_closure,one_shot_lease,full_five_group_capture,initial_bootstrap_before_credentials共12项AuditDimension；verdict为pass/fail/inconclusive，evidence非空精确AuditEvidence列表；commit/path取注册源、原W六文件、引用的不可变审查/执行元数据；不得凭无来源文字判pass。limitations必填非空安全字符串列表。
- ClosureAudit无capture时target_draw_date/forecast_snapshot_sha256=null、group/sixes为空；有capture时精确绑定唯一目标和同顺序group/six列表。verdict pass需两个count为0、每个dimension pass、完整source_contributors（ContributorIdentity列表）与独立作者排除；initial_bootstrap_sha256与I评论/Auth/原entry及两次prelaunch proof一致。authoritative_inference按K规定；CaptureBundle只允许audit pass、classification固定consumed，且所有SHA指向该唯一audit/原W。
- NotificationIdentity的group/sixes必须与bundle/audit/原冻结五组一致；notification_kind固定`audited_historical_five_group_exact6`，路径为B的唯一目标模板。NotificationIdentity.notification_execution为NotificationExecution，deployment摘要精确Auth.N、workflow固定生产路径与N源码SHA、run_id正整数/run_attempt=1、event_sha=N_A14，runtime_identity_sha256为R_N14冻结的实际Linux身份，execution_metadata_sha256绑定API认证的run/workflow/source/actor安全字段证据；这些不是SMTP凭据。NotificationIntent.identity为该对象、state=started/retry_allowed=false；NotificationBody绑定identity的J摘要，不绑定整个intent以避免自指。
- NotificationResult.sealed_journal为FileRef；result为sent/failed/unknown/not_sent，claim_commit仅在本调用own createRef201+确认后为OID否则null；retry_allowed=false。TerminalObservation是安全stdout/stderr观察，不是第七文件，boolean/unknown状态用true/false/null，仅保留有限enum，不含异常原文、payload或环境。

前缀行对象 `PriorDrawRow` 只用于先前历史的身份投影，精确三键 `{draw_date,numbers,bonus}`。原领域源是被冻结的 `Draw(draw_date: date, numbers: tuple[int,int,int,int,int,int], bonus: int|None)`，不是 date/main 字段替代类；读取固定字段，不用 dataclasses.asdict 或不受控反射枚举。`type(draw) is Draw`，`type(draw.draw_date) is datetime.date`（拒绝 datetime 子类）；日期转严格 `YYYY-MM-DD`。numbers 必须原生 tuple、恰六个原生 int、1..49、升序且互异，投影为同顺序 JSON list；bool 不作 int。bonus 为原生 int 且1..49、不在主号中，或原生 None 投影为 JSON null；None 只有固定 governed authority 明确允许该行缺 bonus 时才可用于正式身份，不能补造、推断、忽略或将缺失替成0。该投影保留 bonus 作为审计身份，现有概率/特征计算仍仅采用科学对象原流水线，不新引入 bonus 特征。

## D. 摘要编码、时间和不可变写入

`visible_prefix_sha256` 只采用这一个编码，禁止复用日期摘要或历史全表摘要。按严格升序 draw_date 的完整目标前缀 P 投影为 PriorDrawRow 数组 R，保持行序，定义 `PREFIX_DOMAIN = b"lotto649-v14-visible-prior-draw-prefix-v1\n"`、`prefix_bytes = PREFIX_DOMAIN + J(R)`、`visible_prefix_sha256 = SHA256(prefix_bytes).hexdigest()`。域标签以一个 LF 结束，J(R) 也恰一个 LF；无 BOM、CR、额外空格、数值字符串、目标/未来行或概率/答案字段。C/J 的键排序适用于每行，数组从不重排。摘要输入只含严格早于目标的完整 draw_date/numbers/bonus 行及固定域；目标日期和期号独立在 Intent/Forecast 核对，不将目标答案读入摘要。

唯一实现位于已登记 `src/lotto649/v14_evidence.py`：`visible_prefix_sha256(history, target_draw_date, expected_cutoff, expected_count) -> str`，纯读取传入先前 Draw 序列，不打开文件、加载其它历史、调用模型或修改行。它先验证非空、原生日期/Draw/号码/bonus类型、日期严格递增无重复、所有日期 < target_draw_date、len==expected_count、最后日期==expected_cutoff且cutoff<target；生产协调器额外验证expected_count>=300、完整权威前缀从登记history_start开始、相邻行身份与已验证权威顺序完全一致。expected_count/cutoff来自已认证权威的当期 prior-prefix 选择，不由CLI参数或预测输出反推。数学序列化小fixture可少于300，只验证此纯编码；它不满足正式 worker 的训练门槛。不可预先计算包含全部627答案的逐期摘要表；逐期只有上一期已评分且未停止后，才对当前合法prior prefix计算。

GenerationIntent 与同一期 Forecast 使用同一次合法前缀的该摘要，冻结前重新核对所传前缀未变化；内部/外部审计用相同纯函数和已经合法揭晓的证据进行身份等价校验，不产生新概率。改变一行日期、主号或bonus必须改变字节/摘要；与冻结绑定不相等即完整性失败。仅比较日期或抽样若干行不是等价方案。

固定合成闭式编码 oracle：两行分别为`{draw_date:"2001-01-03",numbers:[1,2,3,4,5,6],bonus:7}`与`{draw_date:"2001-01-06",numbers:[8,9,10,11,12,13],bonus:null}`。C/J 后域+数组字节长173，SHA-256=`2652aac7383ec4ceeb0a438e256edc25a61ebcb6d5843cc0b37d0f7295982ae2`。该虚构fixture只校验序列化，第二行null不声称任何真实历史bonus缺失。测试必须另覆盖300期纯合成合法前缀的正式门。

所有seal/config/auth/claim/forecast/report/audit/bundle/通知intent/result均J；科学合同、操作合同、preserved-tree以及facts摘要均SHA256(J)。implementation_files/runtime_dependency_closure按路径升序，摘要为SHA256(C)；runtime identity摘要SHA256(C)。registered_files各SHA为实际文件bytes。Markdown为确定UTF8/LF渲染原始JSON事实，按实际字节hash，不能当JSON再次编码。

startup与notification journal的previous hash为前一完整J行SHA，无event自hash字段；初始previous=null。科学ledger event_sha256为SHA256(C(去掉event_sha256的其余6键))，完整行是J(7键事件)，previous引用前一event_sha256，首previous=null。每次追加保留FD/dev/inode/nlink=1/父链身份和完整已写bytes/hash；任何长度、内容或所有权漂移终止，不接受“路径在allowlist”代替当前创建证明。

创建必须0600、O_EXCL/O_NOFOLLOW、固定非symlink目录链，首次flush/file fsync/parent fsync成功后才允许后续副作用；每个intent/receipt再次flush/fsync。禁止overwrite/truncate、覆盖既有prediction/evaluation/ledger/report、任何后来进程领养续写、吞掉不完整末行、修复尾换行或删失败残留。唯一跨进程例外是G节同一活跃supervisor到其唯一新child的内核FD交接；它不是从已有路径重开或恢复。生成时间、冻结时间、历史目标日期、训练截止分别保存，不把目标日午夜伪造成真实生成时间。可信UTC回退或格式异常终止；操作系统fsync和时钟信任边界必须在审计说明中披露。

## E. 精确运行时与Git/read-only认证

CPython3.12.11，little-endian、arm64、IEEE binary64（radix2,mantissa53,maxexp1024），科学合同精确平台与27个发行包；requirements/v12-historical.txt SHA `a0dfeac17ad7e1c41dffe4b41b4810156fb028f879d312430bfc517672a570c6`。科学Runtime七键保持不变，另有InitialBootstrap启动合同；普通解释器的site处理在launcher正文前，因此不得用稍后-I-S-B重启代替之前的核验。关键验证不用assert。正式运行时不得安装/修包、修改venv、追加任意用户路径或动态选择环境。


InitialBootstrap 在I14以真实静态运行环境/源码盘点首次冻结，I/K/A/M逐项一致；R14只冻结本节闭合结构和拒绝规则，不填虚构可执行文件、启动路径或缺席证明。Auth新增initial_bootstrap完整17键对象及SHA256(J(initial_bootstrap))；I14真实独立源评论也绑定同一摘要，K/A/M及capture/closure审计再次硬绑定。R阶段评论此字段可null；I及其后必须非null真实值。任何值尚未确定、hooks未核对、unregistered startup inventory、缺失proof或变化均关闭启动，不能靠“normal child后来通过”追认。

InitialBootstrap 的 normal_executable 是实际绝对venv入口路径的BootstrapEntry，若该入口是symlink，只能在完整aliases链已认证时使用，不能用realpath入口替换导致丢失venv身份；executable_aliases为解析 python3.12/venv链接的完整有序BootstrapEntry链，最终必须到同一已封字节，拒绝PATH别名/命令函数/未知symlink跳转。launcher是已登记同一tools文件，git_blob/SHA精确I源码，在I/K/A/M不变；对象包含自身源码OID是运行外Auth/评论的派生绑定，不把含自身摘要的对象写回launcher常量。isolated_supervisor_command/normal_child_command/isolated_child_command分别为固定argv，child隔离形式只是在python3.12之后加入-I,-S,-B，原consume flag不变。supervisor_function恰supervise_v14_once；没有用户传入callback、模块名、源码路径或代码字符串。

runtime_inventory_sha256=SHA256(J(runtime_inventory))；runtime_inventory 是绝对运行环境路径的BootstrapEntry按UTF8 path排序：绑定启动解释器及全部别名、pyvenv.cfg、对应base解释器与libpython/固定平台加载库、encodings/importlib/site/sysconfig等实际stdlib、stdlib/lib-dynload、允许的site-packages和完整包文件、所有可能启动search根、固定credential-provider可执行文件，以及Python实际会查询但当前不存在的zip/hook路径。实际启动入口和所有允许导入根的目录做完整递归名录，包含忽略文件、pyc与symlink，不允许仅抽样或只核对已知文件而忽略新增。已有pyc必须绑定真实字节并确认对应源身份；PYTHONDONTWRITEBYTECODE不等于禁止读取旧pyc。

BootstrapEntry.kind只准regular/directory/symlink/absent。regular记录真实权限mode、uid/gid、bytes和SHA；link_target=null。directory记录真实mode/uid/gid，bytes=null，sha256=SHA256(J(按UTF8 name排序的全部直接子项BootstrapDirectoryChild列表))。symlink记录链接本身mode/uid/gid及UTF8链接文字bytes/SHA/link_target，并登记真实目标完整链；不存在的路径其mode/uid/gid/bytes/sha256/link_target全null。source root/.git不能是symlink；运行时链接只准固定完整链，不允许逃向未登记对象。目录不得有不受信任的可写者；操作审计保留操作系统/当前用户/管理权限与并发修改信任边界，文件哈希检查不宣称创造了OS沙箱。

active_startup_paths为该normal解释器在精确环境下的完整有序sys.path；不得含空串、CWD、repository根/tools、用户site、未登记目录、网络路径或任何实际zip归档。本版本要求所有会查询的startup zip路径不存在，不能临时展开/替换。venv include-system-site-packages必须false。唯一允许的customize入口是下文已经逐字读取的Homebrew sitecustomize.py及其唯一固定cache；所有其他活跃启动目录中的.pth（包括只有数据路径的.pth）、sitecustomize/usercustomize源文件、cache、包目录、扩展模块或其他可加载形式全部拒绝。逐目录完整枚举，不只检查一个.py名字；PYTHONNOUSERSITE=1不代替盘点。不得删除已有Homebrew hook/更改venv，也不得在R之后临时扩大这个唯一例外。

本次源码只读核实的唯一hook：`/opt/homebrew/Cellar/python@3.12/3.12.11/Frameworks/Python.framework/Versions/3.12/lib/python3.12/sitecustomize.py`，3769 bytes、mode0644、SHA-256=`8f53bbf5e6a5679f47dbdabf680e30dd6159220d11c601786d95bf2ae72c1b38`。唯一对应cache为同目录`__pycache__/sitecustomize.cpython-312.pyc`，4050 bytes、mode0644、SHA-256=`0f4e9870b6206583d72f74d0a34b7c6bafc8c6617450739dcf6b5308d5e012ad`。静态header为`cb0d0d0a000000009dae8668b90e0000`：magic cb0d0d0a、flags0、source timestamp1753656989、source size3769；源码mtime整秒同1753656989。上述当前字节/metadata已读取，不代表已经执行hook、验证cache代码等价或通过未来I审查；本稿没有运行/解码该cache。旧V13外部launcher仅提供源检查线索，其授权、动态结果和review不能继承。

该hook精确直接import `re,os,site,sys`；I须固定其真实stdlib依赖和全部可达导入/平台库，并对这份确定源码的属性/正则/路径操作做窄范围审查。版本分支要求3.12；错版本分支可能读取PYTHONPATH并调用exit，正常启动前固定解释器版本与禁止PYTHONPATH保证它不可达。正常venv分支中`sys.prefix != sys.base_prefix`，因此不会执行改写sys.executable/sys._base_executable的非venv分支；PYTHONEXECUTABLE、PYTHONHOME、PYTHONPATH、__PYVENV_LAUNCHER__在构造输入环境中均禁止。允许源码检查这些固定名称的存在性，不将它扩展成任意环境/凭据读取权限。

本版本固定venv prefix为`/Users/jaspershi/CodexResearch/venvs/lottopred-v12-frozen`（下称F）、real base为`/opt/homebrew/Cellar/python@3.12/3.12.11/Frameworks/Python.framework/Versions/3.12`（R）、opt base为`/opt/homebrew/opt/python@3.12/Frameworks/Python.framework/Versions/3.12`（O）。这些是新V14要求值，I须重新确认实际完整alias/pyvenv/源码身份，不能用旧V13证明填PASS。正常预期为sys.executable=F/bin/python3.12、real_executable=R/bin/python3.12、sys.prefix=sys.exec_prefix=F、sys.base_prefix=sys.base_exec_prefix=O、site.PREFIXES=[F]。hook的Cellar→opt base改写明确允许；不得把这项受审改写误判为运行环境任意漂移。source固定的/Library site重排与长Cellar site路径替换在本venv四项sys.path中都不新增路径。

normal probe的完整sys.path必须精确为[R/lib/python312.zip,R/lib/python3.12,R/lib/python3.12/lib-dynload,F/lib/python3.12/site-packages]；第一项作为搜索路径存在但文件必须lexists=false。F的pyvenv.cfg须include-system-site-packages=false；site.PREFIXES只有F，所以hook的`site.addsitedir('/opt/homebrew/lib/python3.12/site-packages')`分支不可达，任何全局site加入均拒绝。`/opt/homebrew/opt/python-tk@3.12/libexec`与`/opt/homebrew/opt/python-gdbm@3.12/libexec`必须lexists=false；否则hook会追加split roots，必须在probe前拒绝，不依赖probe后补救。本次只读metadata确认这两个路径与zip不存在，I/K/A/M和临近spawn还须重新验证。

BootstrapProbeResult因此精确扩为19键：原七键加exec_prefix/base_exec_prefix/site_prefixes/enable_user_site/safe_path/no_user_site/no_site/dont_write_bytecode/sitecustomize_file/sitecustomize_cached/usercustomize_loaded/project_loaded。normal阶段enable_user_site=false、safe_path=true、no_user_site=1、no_site=0、dont_write_bytecode=1、usercustomize_loaded=false、project_loaded=false；sitecustomize_file/cached为上方两个唯一路径，module_origins中site为已封frozen实现、sitecustomize为唯一源码，所有其他来源仍必须在冻结闭包。反射仅允许已审probe字面程序访问这些精确sys/site/module元数据，不能把getattr、sys.modules或整模块放行。

cache在任何credential provider或normal启动之前严格核验：先拒绝缺失/大小/mode/SHA/header或对应source bytes/mtime变化，再在已封CPython3.12.11的-I-S-B环境用已审stdlib checker进行纯内存code-object等价验证。输入仅上述精确已校验source/cache；compile使用完整上述source filename、mode='exec'、dont_inherit=True、optimize=0。若使用marshal.loads，只能在完整pinned SHA及4050 bytes/header校验后解析这一个固定cache payload，检查结果type为CodeType、co_filename精确、与新compile对象结构完全相等；严禁exec/eval/调用/执行代码对象或解码任意输入。compile/marshal/CodeType这些反射仅在登记checker源码SHA和固定用途内允许，所有相关stdlib依赖也进入I闭包。无法证明等价就拒绝，不重建/删cache、不退回另一代码入口；-B防写不能替代此验证。cache等价的实际新验收及I/K/A/M硬绑定仍是未来门槛，本源码调查只证明现有字节和条件分支。

BootstrapEnvironment.fixed_variables精确七键：PATH为已封python目录加:/usr/bin:/bin、LANG=LC_ALL=C.UTF-8、TZ=UTC、PYTHONNOUSERSITE=1、PYTHONSAFEPATH=1、PYTHONDONTWRITEBYTECODE=1。绝不复制整份os.environ；不保留HOME、用户配置、PYTHONPATH/PYTHONHOME、PYTHONSTARTUP/PYTHONINSPECT、VIRTUAL_ENV、DYLD*/LD_*、proxy、GIT_*、GH_TOKEN、SMTP_*或任意未知变量。Darwin可能由平台增加一个`__CF_USER_TEXT_ENCODING`；精确构造并交给Popen/execve的dict绝不包含它，也不能从调用环境复制。进程内实际os.environ键集只在darwin允许这一个平台新增名称，值不读取/记录/转发，其他额外名称仍拒绝；后续子调用重新按固定dict构造，不继承该平台项。这个例外不允许PYTHON*/DYLD*/proxy/SMTP/GH等未知输入，也不改变hook读取环境名称的固定范围。supervisor/sterile probe开始均无凭据；正式child环境仅另加内部获得的GH_TOKEN及四个内部FD交接变量V14_STARTUP_FD、V14_HANDOFF_FD、V14_SUPERVISOR_PID、V14_SPAWN_NONCE。这四项不是调用参数，必须由当前supervisor新建的内核FD/进程/随机nonce推导；caller提供的同名值被拒绝。固定Git子调用另使用本节安全Git环境；不把child的GH_TOKEN带入Git。

监督程序初层只用已固定解释器的-I-S-B隔离stdlib读取Git/登记源码/Bootstrap inventory和AST，先核对launcher及整个允许runtime/import closure，才导入受审项目read-only认证与固定数学oracle函数。该受限调用图在I14冻结，只可生成inert Facts、验证数学/合成fixture和source/runtime，不可读取历史/真实结果、实例化模型预测、发capability、创建claim/lease或通知。source根/stdlib加载源/normal启动全部本地核验通过之后，才执行已封credential_provider。它是固定绝对gh可执行文件及其真实SHA，argv恰[auth,token,--hostname,github.com]，shell=false；allowed_configuration_environment_names只准HOME/GH_CONFIG_DIR/XDG_CONFIG_HOME/TMPDIR的实际存在项，顺序按此固定列表；仅独立传递这些已记录配置位置。fixed_environment精确五键PATH/LANG/LC_ALL/GH_HOST/GH_PROMPT_DISABLED，PATH为已封gh目录:/usr/bin:/bin、LANG=LC_ALL=C.UTF-8、GH_HOST=github.com、GH_PROMPT_DISABLED=1。不继承已有GH_TOKEN/代理/SMTP，不输出、持久化、哈希或显示返回token及凭据配置正文；捕获token仅在内存使用。这里准许程序使用既有GitHub凭据，不是让研究agent读取Secret值。

仅实际历史授权M及本地source/bootstrap静态核验通过后，允许一次无凭据normal sterile probe：同一绝对normal_executable、shell=false、同一固定环境但无GH_TOKEN/交接变量，argv=[python3.12,-c,已登记字面probe代码]。探针code和SHA在I冻结，code只读取解释器身份、sys.path与已载模块来源，输出J(BootstrapProbeResult)，不import项目/模型、读历史、获取凭据或写状态；响应精确19键，其module_origins是按name排序BootstrapModuleOrigin列表，origin只能已登记源码绝对路径或明确builtin/frozen/null。code本身可使用的反射恰为此已审literal与源码范围。此probe用于发现static盘点遗漏，不能先执行未知site代码再拿结果宣称安全；任何执行前hook/zip/路径盘点不满足直接拒绝，不启动probe。probe timeout/退出非0/响应不闭合/路径或来源不符均拒绝。登记前与I工程测试仅用fake subprocess/临时合成树，不运行此真实监督入口或真实normal probe。

PrelaunchProof 是仅source/runtime/安全metadata的14键闭合记录：execution_commit=M、implementation_commit=I、source_root为由已认证launcher导出的实际完整clone根，source_manifest/runtime/bootstrap/inventory/环境摘要全相等，supervisor_pid为当前真实PID，sterile_probe保存完整BootstrapProbeResult安全响应，sterile_probe_sha256为其J摘要；source_manifest_sha256等于Auth.implementation_files_sha256，完整closure仍由Facts/Auth/StartupIdentity绑定，不能只验证九文件就跳过依赖。初次proof在本地核验后形成，随后remote只读认证须完整得到当前M/main保护、CI/评论/Auth及N readiness；该inert Facts既不启动worker也不跨越entry。获得GH_TOKEN以后不放松之前的无凭据核验；严禁普通Python先继承凭据再尝试自检。

在取得startup独占FD后写phase0 entry，并在phase1前再次完整核对源/可执行文件/启动目录名录、唯一hook/source-cache等价及其他钩子缺席、runtime、精确环境和当前授权；将临近spawn的PrelaunchProof完整冻结到phase1。phase1及目录fsync完成后只能一次Popen，无任何可执行环境修改、shell调用或额外代码加载插在最终核验与Popen之间。Popen必须shell=false、executable=固定normal_executable绝对路径、argv=唯一normal child命令、cwd=已认证source_root、close_fds=true、pass_fds仅当前两条已认证FD、env为上述精确字典；不用PATH重新找解释器。调用槽在进入Popen前标记已消费，异常/timeout/结果不明均不得再次Popen或换clone/argv/身份启动。任何已有startup（包括空文件/部分首行）均拒绝新supervisor。

normal child 的最小launcher正文在任何项目导入或GH_TOKEN读取前，核对固定consume argv、内部交接描述符形状，然后用同一固定可执行文件execve一次到-I-S-B，保留同一个PID和两条明确FD；这是同一子进程的受审隔离过渡，不是第二个Popen/worker。已经-I-S-B的child不得再次execve。之后才读取活跃父进程的一次hand-off，重新本地source/bootstrap/runtime和完整native Facts验证，再取得唯一scientific capability；直接启动/未知FD/父进程已死/身份不符只终止。这个后续检查补强父级pre-spawn检查，不能追认为此前未核验的普通启动合法。

初始源根为launcher、lotto649/__init__、v14_registered_attempt；本地字节/Git config安全先验证，再导入包。完整closure根为launcher、九路径内五个运行模块、operational_history与不变notification及静态依赖/包初始化/固定requirements/登记静态资产。只允许科学v2明确的第三方包和必要stdlib根，AST逐模块检查import/反射能力，拒绝动态import字符串、getattr/eval/exec/未注册importlib/sys.modules或属性绕过。允许的系统反射只在已登记函数/源码SHA/目的范围，不能为方便把整个模块放行。

纯数学/合成oracle覆盖旧长期频率实际浮点链、新严格49键/概率门槛、蛇形组、精确M/q整数分布与尾部、fsum评分/校准/12CI、所有null分支；不以V13 beta/libm测试当V14科学验收。I/K/A/M与每次forecast前、冻结前、最终artifact前、post-audit通知前重新核对core/实现manifest/closure、实际loaded module origins、发行包与本地目录状态。

Git固定 `/usr/bin/git -c core.hooksPath=/dev/null -c core.fsmonitor=false -C exactroot`，timeout120s，环境仅固定PATH/locale及GIT_CONFIG_COUNT=0、CONFIG_GLOBAL/SYSTEM=/dev/null、NOSYSTEM=1、GRAFT_FILE=/dev/null、NO_REPLACE_OBJECTS/NO_LAZY_FETCH/OPTIONAL_LOCKS0/TERMINAL_PROMPT0/ATTR_NOSYSTEM1。绝不继承Git别名、credentials-command、proxy、过滤器或外部index；artifact构树仅当前owner的注册临时index。拒绝shallow/partial/promisor/alternates/grafts/replace、symlink root/.git、dirty tracked/index、非本人ignored/untracked；origin固定GitHub repository。完整SHA1 immutable blobs/tree/parents从本地完整Git对象验证，不用缩写或当前worktree文本替代。

R14 < I14 < K_H14 < A_H_s14 < M_A_H14必须是实际图：I14普通单父base=K_N14且exact九ADD；K_H14是K_N14/I14普通双父merge；A单父K且仅auth一ADD；M有序父K/A且tree==A。core在I首次冻结并在I/K/A/M完全相同；九文件manifest和closure同样逐点相同。R注册源码/旧preserved对象在所有检查点不可变化。远端保护管理员有效、禁止force push/删除；当前远端main必须精确M，当前clean HEAD必须M。source A、旧M或任意后继head不能启动。

只读认证成功返回内部构造、完整性绑定的Facts，不可用户new/传dict。认证包含注册origin、精确auth J、source/core/closure/runtime/numerics、历史元数据（不读payload）、真实远端main/保护、I与A准确源CI与实际独立评论。Facts不发capability、不创建entry/claim/lease、不载历史；不能把普通preflight叫作正式attempt。

作者trailer固定 `Research-Author-Provenance: <C(SourceAuthor)>`，最后唯一非空行后恰一LF；schema版本为本表，phase是R14/I14/A_H_s14/CAPTURE_PUBLICATION14，contributors为所有实际实质贡献pair，无futureOID。拒绝重复/折行/未知键/额外suffix。各历史阶段两名不同非作者agent和不同session，独立排除所有该源内容作者agent及session；新session不洗掉同agent作者身份。继承来源与合作记录如实披露。

ReviewComment schemas分别为lotto649-v14-r14/i14/ah14/capture-publication-independent-review-v1；R时core/closure/initial_bootstrap允许null，仅因为尚未I冻结，I及之后不得null。每个评论为C+LF，绑定准确base/head/science/op/core/closure/initial_bootstrap（适用时），pass/0 blocker/0 major/independent_agent，真实publisher_login、reviewer/session。ReviewRecord指向真实未编辑created_at==updated_at评论，精确正文SHA/ID/PR/检查ID。两轴可由同一真实publisher贴出，不伪造另一个GitHub人；source PR必须固定仓库main且实际普通合并。准许本地draft review先于测试，但不能在CI未成功时声明最终验收。

CI须github-actions在准确源head产生唯一name=test且completed/success；push check名称push-test，不与test重名，歧义/重复test阻断。完整collections<=100且无next分页/缺项；检查ID/PR/head/base/merge/timestamp均相互绑定，审查和成功CI先于普通merge；所有源变动重新CI/双轴。

## F. 固定GitHub transport与永久单次lease

固定HTTPS api.github.com，prefix=/repos/Jasper-Shi/lottopred，repo node=R_kgDOT41pdQ，branch=main，hash=sha1。GET仅repo根、hash-algorithm、branches/main/protection、literal git/ref/heads/main、literal V14消费或通知ref、git/commits/{fullSHA}、commits/{fullSHA}/pulls与check-runs?per_page=100、pulls/{id}、issues/{id}/comments?per_page=100、issues/comments/{id}、check-runs/{id}。禁止GraphQL/listRefs/其他repo/host/redirect。review/check API只抽取固定验证字段，不把显示metadata持久存为授权。本节该GET集合约束历史transport；独立N的专用保护adapter只使用本节上方固定两个保护GET。独立N transport还必须按R_N14封印的精确Actions run/workflow/job/必要artifact元数据GET allowlist认证其run和readiness，不继承任意其他API权限。R_N14必须事前完整规定这些新增固定路由及artifact验证/来源链，不允许I_N14或发送时临时发现新URL/redirect。

历史与通知claim transport的POST仅/git/commits与/git/refs；独立N token生命周期的特定POST/DELETE仅由其单独已封helper执行，不从claim或历史adapter放行。claim用途capability区分historical和notification：实例只能向自身固定ref/闭合body用各一次POST槽，GET-only facts永远不能POST。环境trust_env=false、TLS on、redirect false、HTTPAdapter retries0、固定Accept/vnd.github+json、Accept-Encoding identity、Content-Type application/json、API version2022-11-28、User-Agent lotto649-v14.0.0，connect10/read30秒，一次仅一个请求。异常/未知状态poison，禁止任何自动或人工重试。

凭据仅受控内存/Authorization header，先本地source/runtime/math验证才构造带token transport；禁止日志/异常正文/完整响应/环境显示、持久化或读取Secret值。历史进程的唯一凭据变量为GH_TOKEN；其余只准E节固定安全环境与内部四项交接元数据，不复制SMTP、proxy、PYTHONPATH或用户配置；token取得路径本身不能新增网络路由或在本地检查前导入未验证包。

lease前再查精确M/main/保护/owner。只有literal `/git/ref/heads/v14-consumption-v14.0.0`从固定origin直接得到精确HTTP404才允许一次commitPOST和一次createRef；空list、403/401/429/timeout/JSON异常都不是不存在。存在或后来404均不能领养、恢复或重试。

LeaseBody恰本表5键，schema本表lease-body、execution_authority_M_A=M、authorization_seal_sha256=auth J SHA、canonical_command固定、nonce_hex=系统新32随机bytes小写64hex。nonce只是唯一性非选号seed。raw Git commit固定tree=Mtree、唯一parent=M、author/committer为`LOTTO649 V14 Consumption Lease <lotto649-v14-lease@users.noreply.github.com>`，时间固定M committer整秒，raw头顺序tree,parent,author,committer，无签名/额外头，message=J(LeaseBody)。本地计算SHA1(commit+空格+十进制长度+NUL+raw)及raw SHA256。

commit POST请求为CommitPOST，message=J(body)字符串、parents=[M]；HTTP201需返回sha==本地OID。POST response唯一required sha，optional仅node_id,url,html_url,author,committer,tree,message,parents,verification；出现者按CommitGET对应闭合嵌套和值验证，message只检查字符串类型、不作身份依据也不记录。必须再GET完整CommitGET，message严格=C(body)无LF，author/committer name/email/date与预期完全一致，tree/soleparent和全部URL绑定预期OID，verification恰{verified:false,reason:unsigned,signature:null,payload:null,verified_at:null}。拒绝任何未知nested key或宽松strip。

RefPOST恰ref/sha；HTTP201与后续literal GET均为RefGET，object为RefObject且type=commit/sha本地OID，所有API/HTML URL严格固定repository/expectedSHA/ref。node_id非空非权威。随后再次main=M/保护确认。此精确API投影延续固定R13 seal中的lease.projection_contract结构政策，但所有V13身份/路径/时间绑定均由上述V14值代换；不继承旧body、权限或状态。测试fixture只验证这一固定投影，不得因真实响应不符而放宽schema。

commit POST和ref POST各先durable intent，成功receipt、commit GET、ref GET逐步durable。收到失败/格式不符/不确定即终止，已消耗槽永不重置；原远端lease永久保留，禁止update/delete/领养、并发赢家采用、换clone重来或重跑worker。

## G. durable entry、唯一普通child与16阶段startup

普通source/read-only readiness未创建任何startup，可以报告未进入attempt。只有实际M、完整本地prelaunch和远端只读Facts全部通过后，当前supervisor才可独占创建注册startup（0600、O_RDWR|O_APPEND|O_EXCL|O_NOFOLLOW、认证父链）；无既有文件时也不能跳过这一独占取得。phase0 kind=attempt_entered，payload={identity:StartupIdentity,verified_facts_sha256:SHA256(J(Facts)),prelaunch_proof:PrelaunchProof}。首完整J行file+parent fsync成功是确认entry，attempt_id=该首行SHA；写入已尝试但失败/部分/未知即永久冻结，不能重归类普通preflight。

以下正常完整顺序精确16项，supervisor仅写0..2；child只在唯一交接后写3..15。

| 序列 | kind | payload required keys | 数量 |
| --- | --- | --- | --- |
| 0 | attempt_entered | `identity, verified_facts_sha256, prelaunch_proof` | 3 |
| 1 | normal_child_spawn_intent | `prelaunch_proof, normal_command, normal_executable, environment_policy_sha256, spawn_nonce_hex` | 5 |
| 2 | normal_child_spawn_receipt | `supervisor_pid, child_pid, spawn_nonce_hex, spawn_intent_sha256` | 4 |
| 3 | child_isolated_attached | `supervisor_pid, child_pid, spawn_nonce_hex, verified_facts_sha256, handoff_sha256` | 5 |
| 4 | capability_issued | `{}` | 0 |
| 5 | lease_absence_confirmed | `http_status` | 1 |
| 6 | lease_commit_POST_intent | `phase_enum, nonce_hex, expected_lease_oid, raw_commit_sha256, request_body_bytes, request_body_sha256` | 6 |
| 7 | lease_commit_POST_receipt | `phase_enum, result_enum, http_status, validated_oid` | 4 |
| 8 | lease_commit_GET_verified | `validated_oid` | 1 |
| 9 | lease_ref_POST_intent | `phase_enum, nonce_hex, expected_lease_oid, raw_commit_sha256, request_body_bytes, request_body_sha256` | 6 |
| 10 | lease_ref_POST_receipt | `phase_enum, result_enum, http_status, validated_oid` | 4 |
| 11 | lease_ref_reread_verified | `validated_oid` | 1 |
| 12 | startup_checkpoint | `{}` | 0 |
| 13 | claim_created | `claim_sha256` | 1 |
| 14 | scientific_ledger_started | `first_event_sha256` | 1 |
| 15 | history_load_intent | `{}` | 0 |

phase1包含重复pre-spawn本地/授权核验的完整新PrelaunchProof，并绑定精确normal argv、绝对executable及环境policy摘要。其nonce为supervisor内部系统新32bytes的64小写hex，只用于启动身份，不是科学seed；与稍后lease的nonce不混用。phase0和phase1必须在唯一Popen之前全部fsync。Popen返回真实进程handle/PID后，supervisor写phase2并fsync，spawn_intent_sha256等于phase1完整J行SHA。若Popen失败/是否创建子进程不明/phase2写失败，无第二次启动，也不伪造receipt或child身份。

同一进程的两条pass_fds为已独占startup FD与新匿名管道的child只读端；不能从路径、argv、用户传入FD或后来进程接管。supervisor把J(SupervisorHandoff)一次发送管道：supervisor_pid当前PID、child_pid真实返回值、同spawn_nonce、startup_prefix为Checkpoint（sequence=2、bytes/SHA覆盖0..2完整J行）、bootstrap/env摘要与phase1一致。发送后关闭其startup FD和管道写端、永久撤销父写权限；父仍保持存活并观察唯一child，不再写startup/claim/ledger；child在lease/history、每次generation/freeze和最终artifact前重验父仍为同一活跃getppid，父失联立即停止并依已确认阶段分类。若交接发送/关闭状态未知则冻结，禁止后续重新发管道或领养文件。

隔离child阻塞等待该一次hand-off，必须接收恰一个闭合J对象后EOF；拒绝部分、多对象、超限、超时、未关闭写端、未知非pipe FD、父PID/实际getppid不符、child PID不符、父已退出、nonce不符或startup FD不是原dev/inode/nlink=1和精确0..2完整字节。父子使用pread核验、O_APPEND追加，不共享seek位置造成重读/覆盖。normal->isolated同PID execve仅保留这两FD，其他FD全关闭；child在确认后关闭hand-off端并将startup FD设为不可再继承。角色切换在同一活跃启动链发生一次，不允许进程重启、自动恢复或从文件生成新capability。

child完成本地boot/source/runtime与native Facts重新核验，J(Facts)必须等于phase0值，StartupIdentity和Bootstrap摘要相同，才写phase3。handoff_sha256=SHA256(J(收到的完整SupervisorHandoff))；phase3完整fsync后才在child内部发capability并写phase4。此capability绑定实际attempt_id/childPID/原FD/完整startup前缀；supervisor没有科学capability，inert Facts或handoff对象本身不是可重新利用的授权。

lease阶段5的http_status仅404；6/9的phase_enum分别lease_commit/lease_ref。成功receipt result_enum=success、status201、validated_oid本地OID；失败枚举http_rejected/transport_failed/malformed_response/identity_mismatch/io_failed/authority_failed，status实际100..599或null，任何失败结束且不进入下一成功phase。GET/ref reread OID均自身expected。

phase12后Checkpoint覆盖0..12，sequence=12；child独占Claim并在13记录SHA。ledger首attempt_claimed绑定同Claim及Checkpoint，phase14记录其event SHA；phase15 fsync后startup永久封闭，才允许固定历史reader。完整manifest同时绑定13行checkpoint前缀与全部16行sealed_startup。claim/ledger/report等只能由该唯一child创建，supervisor不补写。

startup失败可能仅留startup/部分首行，不能凑齐六角色。TerminalObservation新增process_role=supervisor/child、normal_child_spawn_intent_confirmed/popen_attempted（三值true/false/null）、child_pid（真实正int或null）；只写安全stdout/stderr并由操作者原样保留，不增第七canonical文件。没有durable phase1并不足以证明从未有未观察的执行；认定startup_failed_unscored_no_retry须正面证明模型未开始。phase1存在而Popen结果/交接/child状态未知则frozen_failure_phase_unknown_no_retry；一旦first generation intent已durable，任何后续非capture错误即Archive，即使评分数0。父进程失联、已有文件或任何未知FD来源都永久停止，不重试。

## H. 历史读取与每期科学ledger事件

仅唯一child内部active claimed capability、正确L、已sealed16阶段允许调用固定operational_history.load_published_history(root,H)。验证science.scope中全部Git对象/来源/count4444/起末/连续日期和627/314/313摘要；不fallback工作树CSV、networkrefresh或追加新期。返回模型的只能是完整prior prefix，前缀N>=300；目标/未来/bonus不能进入概率计算。一次LongFrequencyModel调用后严格49概率验收，再一次纯固定selector，不枚举候选版本或另生经验producer。

ledger首事件attempt_claimed的payload恰{claim_sha256,startup_checkpoint}（2）；之后每个ordinal按日期严格固定如下。

| 每期事件 | payload schema | 时序 |
| --- | --- | --- |
| first_forecast_generation_intent（仅ordinal1）或 forecast_generation_intent（ordinal2..627） | GenerationIntent | 在任何模型/特征计算前fsync；绑定当期完整prior prefix与同Binding摘要 |
| prediction_frozen | FrozenPayload | 模型/49p/5G全部成功后冻结；不得仅保存已选赢家 |
| target_reveal_intent | RevealIntent | 冻结已成功，当前真值读取前fsync；没有当前答案 |
| target_revealed | Revealed | 实际reveal返回且权威类型/目标匹配后追加；不得提前读取 |
| target_scored | Scored | 同一冻结bytes的五组/排名/概率评分全部完成，再追加成功记录 |

每次intent成功即消耗该target的一次生成/揭晓槽。prefix检验在generation intent之前，但所有模型和特征调用都在intent之后；runtime/source检查在调用前和冻结前再次进行。首次intent是正式“生成可能已经开始”的不可重试边界，不证明预测成功；完整intent后出错即Archive，即使无完整快照或无一条评分。

event时间单调，generation intent≤Forecast.generated_at≤freeze≤reveal intent≤reveal receipt≤score_completed_at≤score receipt。每个事件均精确绑定相同ordinal/date/snapshot ref/前事件。snapshot_ref.event_sequence是prediction_frozen序号；不得引用另一次预测。完整TargetBundle不得跳过中间意图/揭晓记录。后续目标仅在上一完整评分且无capture/故障后开始。

当Scored.capture_group_ids非空，先完整保留当前全部五组/概率评分，再追加`historical_five_group_6of6_detected` payload=CaptureDetected，eligible_evidence=false、audit_status=pending_independent_audit、global_stop_search=true，立刻停止下一forecast。Top6/12/18全中不产生capture或通知；它们仅排名描述。首次capture在第627期也必须走capture分支，不能产生固定期末推断。

完整627且无capture/fault则追加`attempt_completed` payload=Completed；正常完整负/conditionpass路径科学ledger共有1+5×627+1=3137行，前提是不额外制造TopK事件；不得从行数替代内容核验。任意故障若仍持有完整所有权且能durable写入，追加一次`attempt_failed` payload=Failure并封闭；stage枚举entry/spawn/handoff/startup/lease/history/prefix/generation/probability/selection/freeze/reveal/score/statistics/artifact/publication_audit，reason枚举authority_drift/runtime_drift/input_invalid/probability_invalid/group_invalid/io_failed/transport_failed/clock_invalid/score_invalid/statistics_invalid/ownership_lost/process_interrupted/phase_unknown。只存安全enum，不存异常/答案/Secret正文。目标未知时ordinal/date=null；last_confirmed引用最后durable event。写失败不补写、不吞末行、不用替代日志。

## I. 内部审计、暂定统计与不可变六文件artifact

原ledger audit必须验证完整schema/hash-chain/时间/16阶段与一次父子交接绑定/claim/L/R/I/K/A/M/runtime/prefix身份/49概率与hex/全部五组、每期freeze-before-reveal、固定评分一致性、无缺目标/重复/未消费intent。运行内计算仅重用原冻结值的等价性/算术，不重拟合/新概率/替代组。未知/有warning/capture不能进入期末统计。

仅完整627且无capture/无故障、运行内完整审计pass时，worker计算科学合同规定的三scope整数精确p与恰12CI，冻结为Report.provisional_inference；runtime_state=`complete_internal_audit_passed_external_audit_pending`，independent_audit_status=pending，provisional_scientific_disposition依原整数条件为Reject或complete_historical_diagnostic_conditionpass_unpromoted。这些是待独立认证数值，不是最终研究结论，不应称新盲确认或未来优势。

其他分支Report.provisional_inference为Inference全部null。capture的provisional_scientific_disposition=null；startup-before-generation/null-phase科学null；已知generation后故障为Archive。partial_scopes/annual只给真实完成前缀描述，n=0均值null，不把未认证中间数字放进权威推断。必要不完整原bytes保留，即使无法形成合法Report也不能重启来补报告。

Report.internal_audit为RuntimeAudit（complete bool、warnings登记enum列表、checked_source_sha256=SHA256(C(implementation_files))、checked_runtime_sha256=SHA256(C(科学Runtime))、checked_ledger_head_sha256=最后已审科学event_sha256）；ledger为LedgerSummary；targets全完整TargetBundle；stop_reason只允许null/first_registered_group_exact6/incomplete/invalid/phase_unknown；audit_publication固定`pending_git_integration`。上述原始字段不会在后续审计或合并时更新。

合法Report和Markdown以J及确定UTF8/LF渲染分别经独占staging→无覆盖发布到注册终路径。Manifest.files恰五个ArtifactEntry按role固定startup,claim,ledger,json,markdown，不含manifest自身；sealed_startup包含16行FileRef、startup_checkpoint绑定早期前缀，execution_commit=M。Manifest J写好后六文件blob进入独立owner index，构建exact六ADD tree，raw普通commit唯一parent=M；身份`LOTTO649 V14 Historical Evidence <lotto649-v14-evidence@users.noreply.github.com>`、时间内部真实UTC、消息`Record immutable V14.0.0 consumed historical diagnostic artifacts`末一LF；不得把未来W写入自身manifest/report。

W创建后不改ref/HEAD/主index、不自动push/merge。保留原W，以普通证据PR发布精确六ADD，准确head CI与独立Standards/Spec0B/M后普通合并且原W为祖先；不能squash/rebase/forcepush。构树/发布失败保留partial/staging/index；不能重新跑worker或覆盖已有artifact来获取更好的出口状态。

## J. 外部独立audit与最终结论

worker确实退出后，外部审计在独立完整clone以冻结source/runtime只读核验原W六ADD/各byte hash、startup/claim/ledger/manifest/原lease/Git/API收据、实际固定历史的每个prior prefix和actual、完整五组capture资格、原概率/排序/评分/全部描述/三scope精确p与12CI（适用时）。只可从冻结p和已揭晓actual重算算术/equality oracle，不重拟合/产生新p/重排G/再runworker。审计作者必须独立于科学、probability/selection、implementation以及该capture证据实质贡献者；审查评论代贴者可相同真实账号。

审计完成后排他创建ClosureAudit J和精确render Markdown；它是追加的权威解释，原六文件不改。审核过程中需要保存安全外部诊断可在非canonical独立owned临时目录，但这些不能自动变成已注册证据；正式audit只引用明确不可变源/原W/已注册元数据及真实执行观察，不伪造OS可信执行证明。

无capture的audit/Markdown在固定historical-terminal-audit路径发布，原W为祖先。pass确认完整性后authoritative_state精确为科学终态Reject或complete_historical_diagnostic_conditionpass_unpromoted，authoritative_scientific_disposition精确复制原provisional科学结论，authoritative_inference逐字段复制原经过核验的Inference（不能重选端点/范围）。完整运行但audit fail/inconclusive：authoritative_state=execution_failed_archive_no_retry，科学Archive，authoritative_inference所有字段null，原provisional数字作为未验证中间值保留；不删除/改写原报告。阶段本身无法认证时按K的unknown/null，不假装较早失败。

有capture：ClosureAudit及CaptureBundle严格绑定原target/GID/sorted6/整个五组snapshot和原W/M，全部12维（含initial_bootstrap_before_credentials）pass/0B/M才允许生成pass bundle。audit失败或不明确也可发布真实失败JSON/MD，但不能创建pass bundle、发送通知或完成Goal。失败记录不需要先有成功audit/marker/bundle，避免前提循环。

capture三文件publication源普通单父实际base，其中base已含原W且新R baseline/runtime仍完整；source exact三ADD，包含真实CAPTURE_PUBLICATION14 authors。实际protected-main普通merge N_A14有序父base/source且tree等source，通过新准确head CI、两名非科学/源/capture作者独立双轴后才是通知权威。源branch、旧head或未合并audit不是通知权威。N_A14由实际图解析，不嵌入其自身文件形成未来OID循环。

## K. 互斥终态、null与Goal

以下区分科学分类、运行状态、独立审计状态；原Report与追加ClosureAudit/NotificationResult各报告其实际时点，不覆盖。

| 条件 | 运行状态 | 科学分类 | 推断/权限 |
| --- | --- | --- | --- |
| 普通read-only readiness未进入entry失败 | 未进入正式attempt | null | 所有p/CI/pass null；可修工程源再作read-only检查，不是worker重试 |
| entry已进入、首次generation-intent前失败，且积极证据证明模型未开始 | startup_failed_unscored_no_retry | null | 所有推断null，永久停止 |
| generation-intent已durable后任意非capture错误，包括0完成评分 | execution_failed_archive_no_retry | Archive | 三scope p、12CI、primary全部null；先前半段完整也不例外 |
| 已entry但生成阶段/过程状态不能认证 | frozen_failure_phase_unknown_no_retry | null | 全部null，保留未知，不猜测没生成或没揭晓 |
| 首次G有效6且当前五组完整评分成功 | capture_pending_independent_audit | null | 固定期末推断全null，含第627期capture |
| capture audit失败/不明确 | capture_unqualified | Archive | 全部null，无通知/Goal |
| capture audit通过但报告/发布/一次通知未全完成 | capture_audit_passed_pending_completion | null | 期末推断仍null，Goal未完成 |
| capture audit、冻结/最终报告、真实普通发布与唯一默认通知sent都完成 | audited_historical_five_group_capture_completed | audited_historical_five_group_capture | 期末推断仍null；仅此可作多组Goal完成核验 |
| 完整627无capture/fault+内部auditpass，外部audit尚未完成 | complete_internal_audit_passed_external_audit_pending | null（provisional单列） | 暂定p/12CI仅原Report；无最终结论 |
| 完整627且外部auditpass，E<=0或20A>B | Reject | Reject | 完整经过验证Inference，无优势/推广 |
| 完整627且外部auditpass，E>0且20A<=B | complete_historical_diagnostic_conditionpass_unpromoted | complete_historical_diagnostic_conditionpass_unpromoted | 仅已消费历史局部条件满足，无live/Goal完成 |

已知invalid错误优先于潜在未经确认6/6；当期五组评分中断保留已freeze/已reveal事实，不编造剩余H/M；没有五完整组就没有该期M。capture相同目标最多一个组可6，但列表仍保持固定ID、保留所有五组记录。正常complete无capture分支仍使用原无条件公平零分布，不因观察到没有6/6改变null。

原初单Final-6 Goal的限定更新必须在R14科学/协议文字显式记录为本实验五组中的预冻结G；G1兼容字段不能冒充其他获胜G。局部显著、最佳5/6、测试通过、普通合并或负结果都不能完成Goal。没有6则冻结关闭V14，后续只能先登记另一窄假设，不能对本已揭晓627期调参再跑。

## L. 一次默认中文通知：完整独立状态机

仅独立capture通过且N_A14真实普通发布后，由另行R_N14/I_N14登记实现的最小通知runtime中固定无参数`notify_audited_capture()`进行独立post-audit procedure；它不调用historical verifier/startup/worker，不接受target/root/path/model/clock/receiver/server/text覆盖。普通history launcher没有notification flag、不会自动dispatch。正式history进程不含SMTP凭据。

通知准备只读核验当前clean clone/source==N_A14==新鲜受保护remote main，完整R/I/K/A/M/L/W原图、九文件/core/科学closure及原始科学runtime证据、另行封印的通知source/closure/runtime、三capture文件唯一不可变ADD原点、准确source CI/两个真实非作者评论、audit全部12维（含initial_bootstrap_before_credentials）/0B/M、全部五组冻结身份、原startup/ledger先后及正确GID。核验全部通过前不创建notification intent或POST。调用notification-purpose transport不能访问历史lease POST用途。

全局标记为固定V14 notification ref，只有该ref新鲜直接精确404才可开始一次意图。身份fresh OS32bytes nonce；NotificationIntent.identity_sha256=SHA256(J(identity))，remote NotificationBody绑定它。通知commit的tree=N_A14 tree、soleparent=N_A14、author/committer为`LOTTO649 V14 Notification Claim <lotto649-v14-notification@users.noreply.github.com>`，时间N_A14 committer整秒，message=J(NotificationBody)。raw OID、POST/GET/C无LF投影、ref闭合验证和失败不重试规则全部按F，替换固定通知ref/body/parent/identity；历史lease不能代替。

完整NotificationIntent先0600排他创建、file+parent fsync；字段包括预序列化commit/ref请求长度/SHA和本地expectedOID/rawSHA、started_at真实UTC。其本身不包含未来journal/result hash。再独占notification journal，使用StartupEvent同形6键但独立schema与以下九阶段。

| seq | kind | payload keys | count |
| --- | --- | --- | --- |
| 0 | notification_intent_frozen | `intent_sha256, intent_identity_sha256, expected_claim_oid, audited_publication_commit, absence_http_status` | 5 |
| 1 | notification_commit_POST_intent | `phase_enum, nonce_hex, expected_claim_oid, raw_commit_sha256, request_body_bytes, request_body_sha256` | 6 |
| 2 | notification_commit_POST_receipt | `phase_enum, result_enum, http_status, validated_oid` | 4 |
| 3 | notification_commit_GET_verified | `validated_oid` | 1 |
| 4 | notification_ref_POST_intent | `phase_enum, nonce_hex, expected_claim_oid, raw_commit_sha256, request_body_bytes, request_body_sha256` | 6 |
| 5 | notification_ref_POST_receipt | `phase_enum, result_enum, http_status, validated_oid` | 4 |
| 6 | notification_ref_reread_verified | `validated_oid, remote_main_oid` | 2 |
| 7 | notification_send_intent | `validated_oid, intent_sha256, audited_publication_commit, notification_kind` | 4 |
| 8 | notification_send_result | `result_enum` | 1 |

phase0 absence=404；phase1/4分别notification_commit/notification_ref请求；phase2/5成功须HTTP201与本调用expectedOID，其他失败枚举同startup并终止；phase3完整commitGET；phase6原ref reread+main=N_A14；全部intent/receipt file fsync后下一副作用。只有本调用own createRef201并reread成功才是winner，不能采用已存在赢家ref。phase7在再次source/runtime/fileFD/immutableaudit/main/保护/ownref核验和默认路由核验后durable写入，随后在调用send前原子consume唯一内存send槽；crash也不重发。phase8结果sent/failed/unknown，均封闭journal。

NotificationResult在journal封闭后独占J写入并绑定完整已存在FileRef；result=sent仅默认sender返回literal True，failed仅literal False或确定失败，unknown是send-intent后结果不明，not_sent只在send-intent前失败。claim_commit只在ownref验证后填自身OID，否则null。partial或ownership不确定则保持所有原bytes，仅安全TerminalObservation，不能新fallback路径或修末行。通知ref一经创建永久不删改，winner/loser/timeout/后来404都无retry/resume/adoption权。

默认sender只使用不变`src/lotto649/notification.py`（M blob `0cdd076cbf027df08422e0f4a7060f2f9b738b1e`，SHA `881c44b87e8e9044d4bbc0e6cb68713d2138671dd8c79363f65dc4a6d1cfccb8`）的`send_email(subject,body)`。只能由仓库已审默认Secrets执行环境在授权发送进程内存注入SMTP_USERNAME/SMTP_PASSWORD；不得读取/回显/记录Secret值或通过参数改服务器/收件人。虽然底层sender支持环境override，新上层在准备及发送前均拒绝SMTP_HOST/SMTP_PORT/EMAIL_FROM/EMAIL_TO。消息只从已认证audit事实生成，必须中文明确“预先冻结五组之一的历史6/6”、真实GID/日期/训练截止/完整证据/W/N_A14/独立审计身份，并说明是已消费严格历史回测、不是下一期预测或稳定中奖能力。

实际默认Secrets注入渠道必须经独立R_N14→I_N14/K_N14完成于I14源冻结之前，再在A/M前重验，不能仅列readiness愿望。不得试发capture邮件或读取Secret值来证明；没有该路径不能假定可用、不能临时加任意workflow/借旧进度邮件/用户.env作为替代。通知部署可用性与完整本地synthetic通知测试分开；其缺口是尚待实现/审查的普通工程工作，不是当前需要用户重新授权的blocker。repo小时进度邮件独立：本小时任何成功或失败尝试都不能再dispatch，邮件只报告已提交状态，不代替capture通知。

通知后只能将同nonce/ownclaim的原intent、sealed journal和实际result经独立普通PR作为注册路径新增，N_A14与原W仍为祖先；这一证据发布不提供新send权。失败/不确定赢家保留原本地记录和永久ref，不覆盖路径；其他loser不能发布自己的不同bytes覆盖赢家。无法发布也不重发。只有sent并完成规定最终证据/审计/报告才可核验Goal完成，unknown不是sent。

## M. current-head preservation与关闭顺序

新注册在真实R14 base建立完整preservation，不能复用旧R13 base。旧V13 native `_registered_authorities`同时检查origin和当前head的ARCH/OPER等baseline；已关闭旧negative后的状态文档变化不撤销旧历史证据，但使旧current-head入口不能拿来当V14服务。禁止调用旧auth/lease/notifier。

V14从I/K/A/M到capture ordinary W发布、三文件audit发布N_A14和一次通知完成期间，所有新R preserved baseline及runtime必须不变；尤其不能为写状态摘要先修改ARCH/OPER/config/package或改变main，使冻结通知前提失效。只允许合同注册的新ADD及实际普通Git图。发送前remote main移动立即终止不重试，不能看到capture后修改verifier放宽。

无capture且原worker/外部audit已闭合后，可单独普通PR更新状态/附负结果；有capture则先完成或永久终止通知再做状态文档闭合。未来live/CLI/workflow/scheduler接线完全独立未授权，不设104期自动运行、不恢复V12/V13旧日期或canary。通知workflow/最小sender是独立R_N14与I_N14范围，必须先真实登记/审查/合并K_N14，然后才能以K_N14为base形成仅九ADD的I14；所有新增N源码/运行闭包/权限在K_N14独立冻结并由历史auth硬绑定，不能在capture出现后临时补路线。

## N. 精确、前瞻的legacy regression工程例外

最终R14明示继承E13的有限测试用途，而不是声称旧E13自动授权V14。范围仅新R base已存在、源字节不变的3162项既有测试与其已固定依赖，包括旧legacy fixtures和V13的source/math/synthetic测试；这些旧测试可按原代码读取仅R base已有的历史/data/完成实验材料，复制到owned disposable fixtures并做原有合成变换。不得改旧reader/加入新路径读取当前V14真实目标，不将输出用于V14模型/组/阈值选择。

允许路径包括本机完整回归与R/I/A准确源CI，含R14 PR第一次自动CI，但在首次这类运行前必须封存本例外草案并取得实际非作者Standards/Spec双轴0B/M。用户此前明确授权继续工程工作的范围由新登记如实引用；不得追认先前越界，也不改旧E13不可变记录。R14新增registration测试与九I测试严格source/math/synthetic-only，不加载V14 governed answers、初始化正式facts/capability/entry/claim/lease、运行正式historical worker或发邮件。

本地full suite使用独立可丢弃完整clone、检查Git配置、无SMTP/GH/publication/proxy/PYTHONPATH、无自动第三方pytest plugins，测试只许可本地Git transport；依赖预安装独立dev环境，冻结历史venv不改。沿用报告抑制：不输出traceback/captured payload/warnings/localvars，只保留真实test count、exit、剥离fixture参数的失败node ID。不要宣称这些是针对任意恶意代码的OS网络沙箱。

CI checkout/依赖安装可联网，旧workflow持有的checkout token不冒称不存在，但unit body不得用它做任何remote操作；SMTP/publication Secrets不注入测试，原test/push-test名称保持。临时fixtures不覆盖canonical，缓存残留只属于工程环境事实，不能伪称正式runtime clean pass；新正式授权必须另用精确clean完整clone。失败测试、wrapper退出与pytest真实退出分别保留，不改写receipt或重复worker。

## O. 实现与验收必须覆盖的失败面

R/I源码与math阶段只用注册、固定Git元数据、合成fixture和闭式oracle。测试覆盖：N<300/非prior/错类型bool/49键/finite/open interval/1e−12质量门；旧数值链源码等价；浮点tie/固定五组/少组/重复/Top6非capture/G1alias；全score/校准边界与空桶、精确整数w/q/null/阈值/12CI的每行seed与fsum顺序；全部ties/年度/partial/null；first-intent前/后0分失败、冻结后reveal失败、评分中断、第627capture、internal/independent audit差异。

完整操作故障矩阵须含entry O_EXCL失败/partial fsync/clockback/FD替换/目录symlink/foreignignored、capability伪造/复用/并发、source/core/closure在I/K/A/M或每期漂移、动态import/reflection逃逸、假404/403/redirect/分页/未知key/不符GETmessage、commit成功响应丢失/ref创建不确定/存在ref/第二POST、claim/ledger/manifest自指/不完整末行、preservation变化、普通PR父/tree/CI/comment不符、fake reviewer author、单次SMTPintent前后crash/override/returnedFalse/unknown/赢家领养。所有失败为fail closed、保留事实、无额外历史读取或自动重试。

验收要求真实新源完整pytest、相关Ruff/format/diff、registration-path/sourcepin检查、独立Standards/Spec0B/M以及准确head CI；旧V13本地/远端PASS只能作排错来源。本草案不宣称这些测试已执行。只有R/I/K/A/M真实完成、fresh remote/main/runtime/protection/history元数据/通知部署前提一致，才可进入唯一entry；本文件没有自行实现或授予任何一步。

N权限合成验收还必须证明默认GITHUB_TOKEN不被当作Administration:read；两个固定保护GET只走App读取adapter；跨repo/branch/redirect/写方法/权限扩项/错安装ID/过期token拒绝；mint/revoke只有独立helper路由，不占用或绕过claim单次槽；任何失败不得SMTP或用旧readiness/其他凭据降级。所有实际服务qualification在单独R_N/I_N后执行，这里不运行token/protection探针。

启动专门验收（全为合成树、fake subprocess/transport/fds，登记前不执行真实normal probe）：新增任意.pth/额外customize/cache、改变唯一已封Homebrew source/cache或其等价关系、startup zip、sys.path空项/CWD/tools/user-site、pyvenv系统site开关、旧pyc或stdlib/base/libpython/executable/alias链接变化必须在credential provider之前拒绝；固定env之外包括预置GH_TOKEN/SMTP/PYTHONPATH/DYLD/proxy任一变量不得流入child。验证normal child凭据可见之前完整盘点与sterile probe次序；probe异常/非法来源拒绝且不Popen正式child；probe后/取token后/entry后/最终spawn前的源或boot变化再次拒绝。I/K/A/M/comment/Auth/bootstrap digest不一致拒绝；fake provider只允许本地完整检查以后调用，不能由token内容修复校验。合成补充覆盖sole hook正确source/cache可通过静态门；cache错magic/flags/timestamp/size/filename/code-object、任一额外customize或split root、错误venv/site.PREFIXES导致addsitedir分支、版本错误/预置PYTHONEXECUTABLE/PYTHONHOME均在token前拒绝；验证受审Cellar→opt效果和19键probe。构造环境含__CF_USER_TEXT_ENCODING必须拒绝；仅Darwin进程内额外此名称可存在且绝不读取/转发其值，其他额外键拒绝。

验证startup独占失败/部分phase0/phase1 fsync失败均无Popen；精确phase0/1持久化后一次Popen，shell/executable/argv/env/cwd/pass_fds逐项固定；Popen抛错、启动结果不明、phase2写失败、父死亡、FD错inode/来源/类型、nonce/PID/前缀hash不符、pipe多对象/未EOF/超时、重复hand-off、直接normal child、再次execve均终止且不能claim/lease/history/forecast。确认只有同一活跃父子一次FD交接可从phase2到3；父交接后不能追加、child不能重开领养；old13阶段/错checkpoint9/少阶段必须拒绝；正常16阶段以及checkpoint12/sealed15全部字节绑定一致。fake进程报告0评分不得推导未生成，first-intent已出现则Archive；未知Popen/child态全null/no retry。所有新测试放入现有九I中的registered_attempt测试及固定Git投影fixture，不扩大I路径。

前缀专门验收：冻结字面字节/oracle SHA；改变合法主号、bonus或日期导致摘要不同并拒绝旧绑定；交换行/重复日期/目标行/未来行/缺中间行/错误count或cutoff拒绝；bool、datetime子类、主号字符串/float/unsorted/重复、越界或重复主号bonus拒绝；null bonus在允许的小fixture可编码、在禁止缺失的权威行拒绝；不得因为排序/类型强转/补值而通过。额外字段、日期只摘要、全历史摘要、不同域/CR/LF/BOM/不同数组顺序均不等于登记编码。生成intent、冻结快照、内部审计、独立审计必须复用同一个函数；任何一步输入不一致永久停止，不生成第二组概率。

## P. 当前整合状态

本文已作出完整操作选择：V14固定身份、九I路径、五R新增/三MOD、六worker角色、明确16startup与五事件每期ledger、独立五组capture与九阶段一次通知、分阶段暂定/最终推断、R前legacy工程例外。真实R base已固定b1c99b02d9e18ca66b806b00c41a739daeae6740，18个来源档案已逐项列明；整合者计算实际blob/bytes/SHA后填入最终seal，不在I/授权阶段留运行时placeholder。纯core/closure摘要则依法只在I首次实际冻结，R不伪造。

后续仍需完成独立N部署合同与实现：R_N14/I_N14/K_N14的准确新路径、最小runtime、workflow权限/defaultSecrets注入和源审查。当前没有可运行V14默认capture环境；小时进度workflow只发进度，email-test支持任意文本/路由override，均不是可直接沿用的capture路线。该工作是下一项有界工程交付，不是当前用户权限澄清；未完成则I14/K/A不得宣称前置条件通过。不能以合成PASS替代。本文作者不能作为最终R14/I14操作贡献的独立审查者；全部原map/科学草案和V13证据保持不变。
