# Independent protocol opinion: prospective legacy-test exception

Reviewer: `/root/v13_i13_final_spec`. Actual session: `v13-legacy-test-exception-protocol-review-20260913`. Read-only protocol review; no tests, project imports, data/answer payloads, network or authority factories were run.

Reviewed the decision proposal SHA-256 `dbe517028109e26d9b8d06a606cb197ce8e591b19cfe0245adfc0cdf3be6e01e`, static audit SHA-256 `1bc6330ba80c41e733b0e6d1ddd855a4928fe2bfe916433ff4cb454cff7e2f88`, and the frozen R13 activation/immutability clauses.

**结论：没有明确覆盖这类真实历史 payload 读取的现成例外。应请求用户给予面向未来的窄权限，并另行冻结、独立审查相容的操作注册。** 一般性的完整 pytest 要求不能被默认为对已冻结 `preauthorization_prohibited` 的豁免；既有源码审查通过也不是完整 I13 验收。

拟询问的范围正确：仅允许固定旧回归测试为完整性/既有证据一致性校验读取已提交历史和已完成实验材料，离线运行，输出限测试自己的临时夹具；V13 测试仍只用合成输入，科学规则继续冻结，禁止提前运行真实 V13 预测、评分、worker、claim、lease、邮件或远端操作。此许可不追认已发生的读取，也不替代正式历史授权。

R13 的 `immutable_after_first_ADD` 禁止原地修补已注册 seal。新例外应进入另一个不可变操作注册，并保留原注册、源码及事件记录；具体新版本/命名空间由该注册确定，不能静默沿用旧约定。应明确例外是否涵盖新注册 PR 所需的首次 CI，避免把“先完成登记合并”误当成可先运行未获许可测试的理由。

此次记录只能写作中断的测试运行：230 passed、退出 2，非完整通过。真实读取链有静态证据；精确执行节点仍依赖默认顺序推断。现有材料不支持宣称 V13 已产生预测结果、已正式消耗一次实验或发生事后调参。源码在此前固定且未改变，是应保留的限制性事实，不使读取事件自动合规。整个 Goal 和 I13 验收均未完成。
