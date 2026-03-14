# 🚀 Telecom Test Toolkit

> **A plugin-based ecosystem for telecom and 5G test automation.**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Telecom Test Toolkit (`ttt`) is the **central orchestrator** of the [telecom-test-tools](https://github.com/telecom-test-tools) ecosystem. It provides a unified CLI, shared data models, and a plugin-based pipeline engine that connects 6 specialized tools.

**What it does:**
- 📡 Analyze telecom & gNodeB logs for protocol events
- 🔍 Scan test logs for quick pass/fail triage
- 🎯 Detect flaky tests using historical heatmaps
- 📑 Generate interactive HTML test reports
- 📊 Visualize results on a live Streamlit dashboard

---

## 🧩 Architecture

```
                    ┌─────────────────────────────┐
                    │    ttt CLI (Orchestrator)    │
                    └─────────┬───────────────────┘
                              │
                ┌─────────────┼─────────────┐
                │       Plugin System        │
                │  (entry-point discovery)   │
                └─────────────┼─────────────┘
                              │
     ┌────────────────────────┼────────────────────────┐
     │                        │                        │
┌────▼─────┐           ┌─────▼──────┐           ┌─────▼──────┐
│ Analyzers │           │  Scorers   │           │ Reporters  │
├──────────┤           ├────────────┤           ├────────────┤
│ testwatch│────────►  │ flakiness  │────────►  │ report-gen │
│ log-analz│           │  scorer    │           │ dashboard  │
│ testscope│           └────────────┘           └────────────┘
└──────────┘
     │                        │                        │
     └────────────────────────┼────────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Shared Data Store  │
                    │   (ttt_data.json)   │
                    └────────────────────┘
```

The toolkit automatically discovers plugins registered via [Python entry points](https://packaging.python.org/en/latest/specifications/entry-points/) and executes them in order: **analyzers → scorers → reporters**.

### Ecosystem Repositories

| Repository | Role | Plugin Type |
|------------|------|-------------|
| [telecom-test-toolkit](https://github.com/telecom-test-tools/telecom-test-toolkit) | **Orchestrator** — core framework, CLI, pipeline | — |
| [testwatch](https://github.com/telecom-test-tools/testwatch) | Quick pass/fail log scanner | `analyzer` |
| [5g-log-analyzer](https://github.com/telecom-test-tools/5g-log-analyzer) | gNodeB protocol analysis (attach/RRC/setup) | `analyzer` |
| [5gtestscope](https://github.com/telecom-test-tools/5gtestscope) | 5G KPI & failure detection | `analyzer` |
| [Regression-Flakiness-Heatmap-Scorer](https://github.com/telecom-test-tools/Regression-Flakiness-Heatmap-Scorer) | Flaky test detection via heatmaps | `scorer` |
| [test-report-gen](https://github.com/telecom-test-tools/test-report-gen) | Rich HTML report generation | `reporter` |
| [test-monitor-dashboard](https://github.com/telecom-test-tools/test-monitor-dashboard) | Live Streamlit monitoring dashboard | `dashboard` |

---

## 📦 Installation

```bash
# Clone the toolkit
git clone https://github.com/telecom-test-tools/telecom-test-toolkit.git
cd telecom-test-toolkit

# Install (core only)
pip install -e .

# Install with all optional features (dashboard, reporting)
pip install -e ".[all]"
```

---

## 🚀 Usage

### List Plugins

```bash
ttt plugins
```

### Run a Single Plugin

```bash
ttt run testwatch   --input /path/to/test.log
ttt run log-analyzer --input /path/to/gnb.log
ttt run testscope   --input /path/to/5g.log
```

### Run the Full Pipeline

```bash
ttt pipeline --logs /path/to/logs.txt --output ./reports/
```

This runs all discovered plugins in order (analyzers → scorers → reporters), saves results to `ttt_data.json`, and generates an HTML report.

### Launch the Dashboard

```bash
ttt dashboard --data-dir ./reports/
```

---

## 📂 Project Structure

```
telecom-test-toolkit/
├── ttt/                        # Core framework
│   ├── __init__.py
│   ├── cli.py                  # Unified CLI (click)
│   ├── models.py               # Shared data models
│   ├── pipeline.py             # Pipeline engine
│   ├── plugin.py               # Plugin ABC + discovery
│   ├── store.py                # JSON data store
│   └── plugins/                # Built-in plugin adapters
│       ├── __init__.py
│       ├── testwatch_plugin.py
│       ├── log_analyzer_plugin.py
│       ├── testscope_plugin.py
│       ├── flakiness_plugin.py
│       ├── report_gen_plugin.py
│       └── dashboard_plugin.py
├── pyproject.toml              # Package config + entry points
├── LICENSE
├── .gitignore
└── README.md
```

---

## 🔌 Creating a Custom Plugin

1. **Create a plugin class** by subclassing `TTTPlugin`:

```python
from ttt.plugin import TTTPlugin
from ttt.models import AnalysisResult, PipelineContext

class MyPlugin(TTTPlugin):
    name = "my-plugin"
    description = "Custom telecom analyzer"
    plugin_type = "analyzer"  # "analyzer" | "scorer" | "reporter"

    def run(self, context: PipelineContext) -> AnalysisResult:
        # Your analysis logic here
        return AnalysisResult(
            tool_name=self.name,
            plugin_type=self.plugin_type,
            summary={"key": "value"},
        )
```

2. **Register it** in your package's `pyproject.toml`:

```toml
[project.entry-points."ttt.plugins"]
my-plugin = "my_package:MyPlugin"
```

3. **Install** your package — it will be auto-discovered by `ttt plugins`.

---

## 🔧 Development

```bash
# Install in editable mode with all deps
pip install -e ".[all]"

# Verify plugin discovery
python -m ttt.cli plugins

# Run pipeline on sample data
python -m ttt.cli pipeline --logs /path/to/logs.txt --output ./test_output/
```

---

## 📄 License

MIT License — See [LICENSE](LICENSE) for details.
