# MySQL Migration Advisor

把**自建 / on-prem MySQL** 的规格与负载特征作为输入，输出迁移到 **Azure Database for MySQL Flexible Server** 的**选型建议**：推荐 SKU 层级、IOPS/存储估算、参数兼容性风险、迁移阻断点。

定位是**迁移决策前**（pre-decision / sizing），**不是**迁移执行（execution 交给 DMS / MySQL Import）。

## 语言
- 与用户交互用**中文**
- 代码、标识符、注释、提交信息用**英文**

## 架构边界（最重要的原则）

- **确定性内核 vs LLM，必须分清**：
  - SKU 判定、IOPS 计算、存储估算、参数比对 → **deterministic 规则代码**（纯函数、可单测、可复现），**绝不交给 LLM 猜**。
  - LLM 只用于边缘：自然语言输入解析、把结构化结果讲成人话、解释建议理由。
- **决策逻辑只此一份**：核心在 `core.py`（或 `advisor/core.py`）。CLI、Web UI、SKILL.md/MCP 都只是这份内核的**门面**，不得各写一套规则。

## 防编造（硬规则，违反即 bug）

- 任何 Azure 规格数字——**SKU 的 vCore / 内存 / IOPS 上限 / storage 上限**、**参数默认值**、**硬限制**（如 `lower_case_table_names` 创建后不可变、无 SUPER 权限、某些参数 not-exposed / need-restart）——凡**未经官方文档核实**的，一律用占位值 + 标注：

  ```python
  # TODO: verify against official spec — https://learn.microsoft.com/azure/mysql/flexible-server/...
  ```

- 引用 Azure 限制 / 默认值时**必须给来源**（Microsoft Learn 链接或官方文档名）。指不出来源 = 当作未验证，标占位。
- 不编造看起来合理的数字。宁可写 `None` + TODO，也不写一个"差不多"的值。

## 工程规范

- Python 3.10+
- 决策内核：纯函数 + `dataclass` 描述输入/输出，输入输出可序列化
- **每条决策规则配 pytest**：规则改了，测试必须跟着证明
- **避免过度设计**：规则跟着**真实抓到的迁移坑**一个个长出来（具体输入 → 具体判定），不预先造通用框架。攒够 3 个同类规则再考虑抽象。

## 目录约定（随项目长出来，先不强求）

```
advisor/
  core.py        # 决策内核（唯一一份规则）
  models.py      # dataclass 输入/输出
  specs/         # Azure SKU / 参数规格数据（带来源标注）
cli.py           # 命令行门面
tests/           # pytest，每条规则一个用例
```
