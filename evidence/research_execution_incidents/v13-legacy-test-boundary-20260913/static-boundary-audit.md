# I13 full-suite boundary audit — static source and progress metadata only

Audit agent: `/root/v13_i13_pr_proof_map` (read-only auditor, not I13 content author).
Repository: `/Users/jaspershi/CodexResearch/lottopred-v13-implementation-20260913`.
Observed HEAD: `900054719a4ac089d4c059830b5c7162f2543616`; exactly eight I13 paths remain staged additions. This audit changes no repository file, index, ref, model, test or registration.

## Observed execution record and its limits

The existing log `/private/tmp/v13-i13-final-complete-repository-tests-20260913.log` contains three 72-dot progress lines (2%, 4%, 6%), fourteen further dots, KeyboardInterrupt, and `230 passed in 668.11s (0:11:08)`. Root independently supplied exit code 2 for session 82522. Log SHA-256: `a563c5f3bfe614ef438a079fc2be00ead08bbd620003c18f53a7bf8d92983f08`.

This is an INTERRUPTED full-suite run, not a full-suite pass. The log contains no node IDs or per-test durations. Its interruption location, CPython 3.12.11 `shutil.py:698`, is `os.unlink(entry.name, dir_fd=topfd)` in recursive directory cleanup. It does not show a model fit or identify the active test.

Static reconstruction under default, unreordered pytest collection gives:

| Module | Reconstructed 1-based case interval | Boundary |
|---|---:|---|
| test_data.py | 1–3 | Source-embedded constructed input |
| test_data_integrity.py | 4–52 | Constructed Draw/evidence objects |
| test_data_integrity_incident.py | 53–73 | Temporary repository populated from source literals |
| test_data_integrity_incident_seal.py | 74–113 | Real registered CSV/artifact payloads reachable |
| test_evaluation.py | 114 | Constructed scoring input |
| test_execution_kill_switch.py | 115–168 | Guard tests; actual history/model paths mocked or blocked |
| test_historical_oos_tombstone.py | 169–183 | Real historical opportunity ledger payload |
| test_history_artifact_publication_github.py | 184–206 | Real operational history in fixtures |
| test_history_execution_handoff.py | 207–258 | Real operational history in most fixtures |
| test_history_publication.py | 259–282 | Real operational history in publication preparation |
| test_history_publication_cas.py | 283–332 | Mostly synthetic; final integration case loads real history |

The installed pytest source uses name-sorted directory entries (`_pytest/pathlib.py:950,978`, `_pytest/main.py:528`) and definition order within a module (`_pytest/python.py:400`). The reconstruction expanded the literal parametrizations in this prefix without importing pytest or the project. No repository collection-reordering hook was found. However, the existing log does not prove absence of external plugins/options or supply exact node IDs. Accordingly, the above intervals are conditional reconstruction, not a per-case execution trace. Under that default-order assumption, all four unsafe groups beginning at case 74 were entered before the 230-pass interruption; the 230th item reconstructs as `test_history_execution_handoff.py:1800`. Do not state that individual node ID as directly logged fact.

## Confirmed payload call chains (all references relative to repository)

### Earliest reconstructed unsafe group: registered incident seal

`tests/test_data_integrity_incident_seal.py:134` first test calls `create_data_integrity_incident_seal(repository=ROOT, policy=REGISTERED_SEAL_POLICY)` at lines 137–140. `ROOT` is the actual repository (line 15), not a synthetic root.

`tools/seal_data_integrity_incident.py:1179` calls `_build_seal_body` (744). Its loop at 750–753 reads every registered artifact through `_git_blob`; `_git_blob` first reads tree metadata (251) and then reads CONTENT with `git cat-file blob` (263). It then calls `_validate_registered_old` (759), which reads the old CSV and parses its draws (439–440), and parses both official and corrected CSVs (760–761). Manifest, adjudication and incident payloads are JSON-decoded at 773–779. These are not metadata-only hash/size checks.

Exact target paths are defined at tool lines 69–85 and policy lines 109–138:

- old commit `90177c80cfb070038d79508fb2e73305a297f516`: `data/processed/draws.csv`;
- artifact commit `b04393944ef12f78417dfb6151343c72d4c2a2ac`: `data/processed/epochs/DI-2026-08-20-registered-history/corrected_draws.csv`;
- same artifact commit: `evidence/data_integrity/DI-2026-08-20-registered-history/official_draws.csv`, `incident.json`, `reconciliation.manifest.json`, `reviewed-adjudication.json`, `source-index.json`.

The policy covers 1982-06-12 through 2026-08-15 (137–138), hence includes the governed 2020–2025 interval. No payload contents were opened by this auditor.

### Historical opportunity ledger

`tests/test_historical_oos_tombstone.py:105` calls `_append` (43); line 45 reads `ROOT/reports/historical_oos/global_opportunities.jsonl` (path bound at 21–22). It copies the real first 18,259 lines into a temporary file. Copying does not make the input synthetic. `append_data_integrity_tombstone` reads those bytes at `src/lotto649/historical_oos_tombstone.py:499` and parses/hashes the complete event chain via `_canonical_chain` (96–136; JSON decode 108). The test itself JSON-decodes the appended ledger at test line 111. This proves real historical ledger-payload access; this audit does not infer uninspected individual ledger fields or values.

### Artifact publisher and execution handoff fixtures

`tests/test_history_artifact_publication_github.py:348` calls `_artifact_fixture` at 351. The fixture obtains actual repository HEAD and directly calls `load_published_history(ROOT, head)` and again at the publication commit (76–80), before fake remote adapters are installed. A synthetic output marker at line 49 does not replace this real input.

`tests/test_history_execution_handoff.py:_candidate` (321) clones actual ROOT (332), loads its operational history (337), loads it again (408), prepares a history publication (697) and reloads it (719). Its helpers subsequently make synthetic appended draws/predictions but retain the real historical prefix. Many execution tests call this fixture. Later, `_legacy_2026_08_26_candidate` (746) reads the real legacy prediction-cohort manifest (763); test 1828 additionally reads the legacy CSV blob (1854–1858) and historical prediction blobs (1880 onward). Those later explicit legacy reads cannot be asserted to have completed from this log.

Common actual-history sink: `src/lotto649/operational_history.py:55` calls the registry reader (58) and `_load_verified_history_from_immutable_bytes` (59). The registry reader itself reads JSON/JSONL blobs (`history_registry.py:758–783`, `_git_blob` content read 311). The verified loader reads all artifact payloads while validating inventories (`verified_history.py:446–454`; raw `git show` at 442), reads/parses old CSV (`537–538`), and reads/parses corrected CSV (`1051–1056`). Immutable Git provenance does not turn these raw payload reads into metadata-only operations.

### Further already-existing runtime hazards beyond reconstructed case 230

- `tests/test_history_publication.py:166–175` clones actual ROOT and invokes `prepare_history_publication`; production `src/lotto649/history_publication.py:423` loads operational history before preparing the candidate, with another load at 513.
- `tests/test_history_publication_github.py:111–154` module fixture clones actual ROOT and loads real history (119). Most publisher behavior cases depend on it. Its later fake-HTTP transport tests are a different, narrower seam; the full module is mixed.
- `tests/test_history_publication_cas.py:135–164` uses constructed state and its `_bare_graph` (618–632) creates empty-tree temporary Git graphs. But final `test_prepare_and_local_cas_publish_one_reader_verified_history` (948) clones actual ROOT and calls real preparation (981). The whole module is therefore mixed, not entirely source-only.
- `tests/test_history_registry.py:233` invokes the real registry loader; helper lines 100 and 118 read actual cloned registry/suffix bytes. Suffix JSONL may carry draw values; this is operational payload, not the allowed `ls-tree` / `cat-file -t/-s` metadata seam.
- Confirmed later hazards from delegated static inspection include `test_live_orchestration.py:45–55`, `test_operational_history.py:30,86,99`, `test_official_source_collection.py:164–209`, `test_research_progress_email.py` report-building paths, `test_v12_registration.py:658–702`, and `test_verified_history.py:145–157`. These are reachable-source findings, not evidence that the interrupted run reached those later test cases.

## Collection/import boundary

The audit inspected all 36 test modules' executable module-level statements, function defaults and parametrization/fixture decorator expressions. Lambda bodies were explicitly excluded from immediate evaluation. Static scans of all `src/**/*.py`, the two incident tools dynamically imported by tests, and the delegated later-module import closure found no collection-time real history/report-payload read.

Nontrivial collection expressions were checked: old V12 `_draw` calls construct source-defined synthetic draws; `_gate_failures` constructs numeric cases; V13 `MainDraw` calls use literal synthetic anchors; three tool imports execute source under non-main names and do not invoke guarded CLI entry points. This is a static source conclusion, not an instrumented runtime trace or proof about arbitrary third-party pytest plugins.

The V13 test module's autouse protection is LOCAL to that module: `tests/test_v13_registered_attempt.py:1253–1265` blocks canonical worker/history/authority issuance and requests transport for its own fixtures. It does not protect the existing legacy suite.

## Source-only testing classification and completion status

Clearly constructed-source groups in the audited early prefix are `test_data.py`, `test_data_integrity.py`, `test_data_integrity_incident.py`, `test_evaluation.py`, and the `test_execution_kill_switch.py` guarded/mocked paths. For example, its enabled direct-backtest case replaces history with an empty constructed object and models with `{}` (339–368); it performs no genuine historical backtest.

The full modules containing the real paths listed above must not be treated as source-only. Some individual rejection/parser/transport tests in them are synthetic, but no exhaustive safe-node allowlist or replacement full-suite command is approved by this report. Later-module classification remains bounded to the delegated source inspection; its final addendum should accompany this report.

The R13 phase boundary allows source, registration, fixed Git metadata, synthetic fixtures and closed mathematical oracles. It prohibits preauthorization governed-history/target payload access. An ordinary mandatory `pytest -q` requirement cannot silently override that explicit phase restriction. Do not rerun the whole suite, silently skip tests, replace real fixtures with mocks merely to obtain green CI, or call a selected subset a full-suite pass. Any permitted testing split or real-data test execution needs explicit compatible operational treatment; historical run authorization does not automatically authorize arbitrary legacy payload rereads.

The current run is interrupted and I13 acceptance is incomplete. The earlier independent source-review findings and Ruff no-new-diagnostic result remain scoped evidence, not full I13 acceptance. No V13 historical model worker, startup, claim or lease was run by this auditor; root reports none was run by the interrupted test activity. This report neither grants authorization nor declares a statistical result, attempt consumption, retrospective evidence eligibility or automatic scientific-version change. Preserve the frozen source and seek the separately scoped protocol determination.

## Performance conclusion

The prior explanation that the first 230 cases were slow old-model tests is unsupported and should be corrected. `test_research_models.py` occurs later than the reconstructed prefix. Its V3 test is indeed potentially computationally expensive: source-generated 390-draw input at lines 47–50 reaches expanding feature construction and HistGradientBoosting fit (`src/lotto649/models/v3_boosting.py:32–65`), but the current log does not show that test executing.

The early suite instead repeatedly clones full repositories, reads/hashes/parses complete historical artifacts, traverses large ledger chains and creates/removes detached workspaces. These are source-supported plausible costs, not measured per-test timing attribution. The interrupt itself occurred during unlink-based directory cleanup.

No test, collect-only command, project import, model invocation, network request, credential access or payload inspection was performed to produce this static audit. Only source, fixed Git/status metadata, and the existing eight-line progress log were read. This report is the sole newly written artifact, outside the repository.

## Delegated final module inventory (static, no execution)

The independent child `/root/v13_i13_pr_proof_map/legacy_test_boundary` completed its bounded source inspection and returned the following classification. These are reachable-source findings, not actual-run node IDs. Source/registration/configuration/proof-file checks are not all synonymous with the narrower R13 fixed-metadata input permission; doubtful old operational proof files remain explicitly identified.

| Later existing module | Static boundary finding |
|---|---|
| test_live.py | Constructed Draw/Prediction and temporary artifacts; real sources replaced (25; 60–80; 125–145). |
| test_live_orchestration.py | Mixed; `_base_history` 45–55 directly loads ROOT. `_fixture_ports` 148 and numerous tests use it. Test 1051 imports the real-base `_candidate` audited above. |
| test_live_release_canary_plan.py | Reads actual plan and existing legacy prediction-cohort manifest (42,159–160); no direct CSV sink found, but not a bare Git-metadata-only module. |
| test_official_history.py | Source-embedded HTML, Draw and calendar/hash cases (17 onward); no payload-file or network reader found. |
| test_official_source_collection.py | Mixed; test 164 clones actual ROOT (167), loads history (177), prepares and reloads (203,209). Other HTTP tests use synthetic client/transport. |
| test_operational_history.py | Mixed; actual ROOT loader at 30,99; actual clone at 79 then loader86. Cases after104 mostly replace loader and construct input. |
| test_research_models.py | Synthetic history generator10–26; model tests35–58 use only it. |
| test_research_progress_email.py | Mixed; actual clone45–52; report-builder calls386–390,421–423 reach history/prediction/evaluation payloads. Source `research_progress_email.py:992`→history601; 996→artifact reads669–670→`_json_blob`631/641→git-show245/195. The850+ email-plan fixtures are synthetic, with explicit replacement954–1011. |
| test_research_progress_email_workflow.py | Python source reads workflow/config/docs and executes YAML-extracted script52–76. YAML body was outside this audit's permitted read scope; complete safety is NOT certified. |
| test_v12_0_1_parity_transition.py | Synthetic2032 draws31–33, source hash54–56, scientific registration809–813, constructed report rows1114–1117. |
| test_v12_0_1_registered_attempt.py | Synthetic authority/Git/API/temporary artifacts and source-byte binding416–417. Test999–1004 reaches a claimed-capability rejection before production history reader (`v12_0_1_registered_attempt.py:2736`, reader2745). |
| test_v12_0_2_evidence_equivalence.py | Source/registration reads158–179 and constructed prefixes192 onward. |
| test_v12_0_2_registered_attempt.py | Source and synthetic projection fixture1257–1261, whose classification is checked1282; autouse1264–1276 blocks canonical/history/network; source bytes2772–2773. Projection JSON body was not opened by auditor. |
| test_v12_r2_registration.py | Registration/config/source docs and frozen canary/closure proof files; fixed preservation list631–648. No actual draw/history/report reader found. Not every old proof-file read is independently certified as an R13-allowed source input. |
| test_v12_r3_registration.py | Real operational proof payloads are read through `git show` at215–229 over preservation manifest, including old authorization, existing-commit API representation, startup incident and closures. No CSV/score-report/scoring-ledger path in the inspected registered list; still not mere Git metadata. |
| test_v12_registration.py | Real seal/registry/suffix/base CSV read663,664,681,692 in `_authority_target_dates_from_git`658–702; projecting dates later697 does not erase payload access. Called966,1047. |
| test_v1_verified_history_diagnostic.py | Synthetic Draw fixtures23–29 and `run_synthetic`; tool imported14–19 under non-main name. Registered-route rejection tests410–435 stop at source-binding/existing-directory gates. |
| test_verified_history.py | Real old and corrected CSV read145–147,156 by `_sealed_repository`; deployed ROOT loaded1626–1634. Synthetic temporary repository is not synthetic history. |
| test_workflow_kill_switch.py | Reads workflow/config/docs and executes YAML-derived guard117/139,415; YAML body not expanded under permitted scope. No direct history read in inspected Python, but full transitive safety is NOT certified. |

The four V13 test modules remain the separately reviewed I13 synthetic/source test scope; this audit added no new execution and does not replace their reviews. No exhaustive node allowlist, mandatory-check exception or protocol amendment is issued. Unknown workflow script behavior remains unknown. Further scope expansion is stopped so an independently assigned Spec reviewer can assess the operational conflict.
