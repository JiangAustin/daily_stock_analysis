# Branch Hygiene

## Private Ext Mainline

`private_ext` 主线应优先收敛在以下范围内：

- `private_ext/raw_data/`
- `private_ext/fact_pack/`
- `private_ext/scoring/`
- `private_ext/decisions/`
- `private_ext/research/`
- `private_ext/paper_trading/`
- `private_ext/database/`
- `private_ext/reports/`
- `private_ext/utils/`

配套的验证与工具脚本可以存在于：

- `scripts/`
- `tests/`
- `docs/`
- `.github/workflows/`

## 当前分支的越界改动范围

当前分支已经包含或曾经包含的非 `private_ext` 改动主要集中在：

- `scripts/`
- `tests/`
- `docs/`
- `.github/workflows/`
- `.gitignore`

当前 Phase 2.4.3 不应继续向下列目录扩展：

- `src/`
- `api/`
- `apps/dsa-web/`
- `apps/dsa-desktop/`

## 后续拆分建议

建议后续把当前分支继续拆成两条线：

1. `private-research-os-core`
2. `upstream-ui-api-changes`

拆分原则：

- `private-research-os-core` 只承载 `private_ext`、`scripts/`、`tests/`、`docs/` 和必要的 CI 变更。
- `upstream-ui-api-changes` 专门承载 Web / Desktop / API / `src` 一侧的联动改动。
- 不要把投研流水和 UI / API 改动继续耦合在同一个 PR 里。

## 审计结论

Phase 2.4.3 的目标是把可信度修复留在 `private_ext` 主线，把外层工程改动限制在可审计范围内，避免继续把分支膨胀成混合型变更集。
