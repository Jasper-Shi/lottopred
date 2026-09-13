"""Keep real legacy integrity-test payloads out of normal pytest reports."""


def pytest_configure(config):
    # Change presentation only. Failures still fail the suite and retain counts.
    config.option.tbstyle = "no"
    config.option.showcapture = "no"
    config.option.showlocals = False
    config.option.fulltrace = False
    config.option.reportchars = "N"
    config.option.disable_warnings = True


def pytest_terminal_summary(terminalreporter):
    # Parametrized IDs can contain fixture values. Keep only the test identity.
    nodeids = {
        report.nodeid.partition("[")[0]
        for outcome in ("failed", "error")
        for report in terminalreporter.stats.get(outcome, ())
    }
    for nodeid in sorted(nodeids):
        safe = "".join(
            char
            for char in nodeid
            if char.isascii() and (char.isalnum() or char in "_./:-")
        )
        terminalreporter.write_line(f"FAILED {safe}")
