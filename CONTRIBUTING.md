# Contributing to pipa

# 为 pipa 做贡献

Thank you for your interest in contributing to pipa! We welcome all forms of contribution, from bug reports to feature requests and code submissions. To maintain a high-quality and sustainable project, we ask that you follow these guidelines.

感谢您有兴趣为 pipa 做出贡献！我们欢迎所有形式的贡献，从 Bug 报告到功能请求和代码提交。为了维护一个高质量和可持续的项目，我们请求您遵循以下准则。

---

## 🚀 How to Contribute / 如何贡献

### 1. Reporting Issues / 报告问题

If you find a bug or have a feature request, please open an issue on our GitLab repository. Please provide as much detail as possible, including:
如果您发现 Bug 或有功能请求，请[开启一个 Issue](https://github.com/cagedbird043/pipa/issues)。请提供尽可能多的细节，包括：

- A clear and descriptive title. / 一个清晰、描述性的标题。
- Steps to reproduce the bug. / 复现 Bug 的步骤。
- Expected behavior vs. actual behavior. / 期望行为与实际行为的对比。
- Your system environment (OS, Python version, etc.). / 您的系统环境（操作系统、Python 版本等）。

### 2. Submitting Pull Requests (PRs) / 提交合并请求 (PR)

All code changes must be submitted via Pull Requests. We follow a strict **feature-branch workflow**.
所有代码变更都必须通过 Pull Request 提交。我们遵循严格的**功能分支工作流**。

---

## ⚖️ Engineering Discipline / 工程纪律

This is the set of rules that ensures our codebase remains clean, consistent, and maintainable. All contributors are expected to adhere to these standards.
这是一套确保我们代码库保持干净、一致和可维护的规则。所有贡献者都应遵守这些标准。

### 1. Git Workflow / Git 工作流

1.  **Create a branch:** All work must be done on a dedicated feature branch, branched off from `develop`.

    - **创建分支:** 所有工作都必须在一个专用的功能分支上进行，该分支从 `develop` 切出。
    - **Branch Naming Convention / 分支命名约定:**
      - Features: `feature/short-description` (e.g., `feature/add-nginx-workload`)
      - Bug Fixes: `fix/short-description` (e.g., `fix/resolve-perf-parsing-error`)
      - Documentation: `docs/short-description` (e.g., `docs/update-readme`)

2.  **Make atomic commits:** Each commit should represent a single, logical change.

    - **进行原子化提交:** 每个提交都应代表一个单一的、逻辑上的变更。

3.  **Follow the Conventional Commits specification:** All commit messages **MUST** adhere to the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) standard. This is crucial for automated changelog generation.

    - **遵循约定式提交规范:** 所有提交信息**必须**遵守[约定式提交](https://www.conventionalcommits.org/zh/v1.0.0/)标准。这对自动化生成更新日志至关重要。
    - **Format / 格式:** `type(scope): subject` (e.g., `feat(collector): add sar data collection`)

4.  **Open a Pull Request:** Submit your PR against the `develop` branch. Provide a clear description of the changes.

    - **开启一个 Pull Request:** 将您的 PR 提交到 `develop` 分支。请提供清晰的变更描述。

5.  **Code Review:** All PRs must be reviewed and approved by at least one maintainer before being merged.
    - **代码审查:** 所有 PR 都必须经过至少一位维护者的审查和批准后才能合并。

### 2. Code Style & Quality / 代码风格与质量

We use automated tools to enforce code style and quality. This is not optional.
我们使用自动化工具来强制执行代码风格和质量。这不是可选项。

1.  **Formatter (`black`):** All Python code **MUST** be formatted with `black` using its default settings.

    - **格式化工具 (`black`):** 所有 Python 代码**必须**使用 `black` 的默认设置进行格式化。

2.  **Linter (`flake8`):** Your code should pass `flake8` checks without any errors.

    - **代码检查工具 (`flake8`):** 您的代码应通过 `flake8` 的检查，没有任何错误。

3.  **Pre-Commit Hooks:** We **strongly recommend** setting up [pre-commit](https://pre-commit.com/) hooks to automatically run these checks before you even commit. A `.pre-commit-config.yaml` is provided in the repository.
    - **提交前钩子:** 我们**强烈建议**设置 [pre-commit](https://pre-commit.com/) 钩子，以便在您提交之前自动运行这些检查。仓库中已提供 `.pre-commit-config.yaml` 文件。
    - **Setup / 设置:** `pip install pre-commit && pre-commit install`

### 3. Testing / 测试

1.  **Unit Tests are Required:** Any new, non-trivial logic in the core modules (`processor`, `analyzer`) **MUST** be accompanied by unit tests.
    - **单元测试是必需的:** 核心模块（`processor`, `analyzer`）中的任何新的、非平凡的逻辑**必须**附带单元测试。
2.  **CI (Continuous Integration):** All PRs will automatically trigger our CI pipeline on GitHub Actions, which runs all formatting, linting, and unit tests. A passing CI is a mandatory requirement for merging.
    - **持续集成 (CI):** 所有 PR 都会在 GitHub Actions 上自动触发我们的 CI 流水线，该流水线会运行所有的格式化、代码检查和单元测试。通过 CI 是合并的强制性要求。
