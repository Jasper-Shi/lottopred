# V12.0.2 完成运行的独立历史与结果审计

结论：在本次审计范围内通过；0 blocker / 0 major / 0 minor。科学结论为 Reject，未出现 Final-6 6/6，Goal 未完成。

审查者：`/root/i3_independent_output_audit`；会话：`v12-0-2-post-run-history-chronology-result-20260913-01`。
审计 JSON SHA-256：`f8d12147e065d869ea10e3ebc7ebcd7a3f8249996d9692f0394ab83a53545a31`。

执行提交：`b7fa81d6d5facc1730700cd527362df79f457cf8`；证据提交：`c9b483f6e89bf73eade28829188fbebe745e28c0`。
报告 SHA-256：`5582ce55fd1fbfece3f5402501bf0470d4e60b1f35c5f66aae02d928cfaa496a`。

核对全部 627 个真实开奖主号码与 bonus、每期完整可见前缀内容哈希/日期/数量、13 条启动记录、1255 条科学账本事件、六文件证据提交以及冻结源码和运行环境。仅对已冻结评分数组重算了全部 18 个置信区间和 12 个精确公平检验；没有重新预测或重新拟合。

| 模型 | Top-6 | Top-12 | Top-18 | Final-6 | Brier | Log Loss | 最佳 Final-6 |
|---|---:|---:|---:|---:|---:|---:|---:|
| ensemble_v1.0.0 | 0.720893141945773 | 1.39553429027113 | 2.07814992025518 | 0.720893141945773 | 0.107688295346222 | 0.372847306623458 | 4/6 |
| random_v1.0.0 | 0.779904306220096 | 1.47368421052632 | 2.22966507177033 | 0.779904306220096 | 0.107455226985175 | 0.371776179926797 | 3/6 |
| v12_post_rng_parity_composition_transition | 0.738437001594896 | 1.46092503987241 | 2.1658692185008 | 0.738437001594896 | 0.107466468074759 | 0.371828724496324 | 3/6 |
| v12_pseudo_parity_composition_transition_control | 0.76555023923445 | 1.47687400318979 | 2.20414673046252 | 0.76555023923445 | 0.107458582232232 | 0.371791863040575 | 4/6 |

候选模型所有最佳 3/6 日期：2020-04-15, 2020-09-09, 2021-07-24, 2021-10-23, 2021-10-30, 2021-12-22, 2022-02-02, 2022-06-15, 2022-12-31, 2023-03-22, 2024-09-25。

主指标 Top-12 lift：-0.0084627152296326；原始精确 p：0.5909687963172663；Holm p：1.0。
十项 gates 仅第 7、10 项通过。

审计边界：
- This is a completed negative-result audit, not a captured-6/6 independent leakage audit and not Goal completion.
- The registered loader holds the complete governed dataset in process memory; strict prefixes and the forecast/reveal boundary isolate predictor inputs. Future rows are not physically hidden from the whole process.
- No prediction or fitted beta was recomputed. Actual prefix/output consistency plus frozen source review supports chronology; direct execution memory/instruction tracing was not recorded.
- Hash chains, timestamps and reviewed fsync code do not independently prove historical OS durability or trusted wall-clock accuracy.
- History was authenticated to the fixed committed governed authority and reviewed validators, not newly authenticated against an independent external draw publisher.
- Fresh remote lease exclusivity, protected-main authority at execution and final Git publication are separate root-owned checks; this audit made no network requests.
- Recorded runtime matches the current frozen audit environment and source pins; this alone is not direct attestation of the historical process environment.
- The legacy V1 cache key is not content-addressed in isolation; V12 creates fresh models for each target. The prior V1 diagnostic also refit each distinct target because its cache key includes target_date. stride=4 selects historical training rows, not a four-target refit cadence.
- Bootstrap replay used frozen score arrays only, NumPy 2.3.5, seed 649, 10000 samples, math.fsum and linear quantiles. Float checks use relative/absolute tolerance 2e-12; exact p-value integer ratios and hashes were checked exactly.
