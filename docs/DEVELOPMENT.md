# Development Documentation

本文档面向开发者，解释项目结构、关键数据流和扩展方式。

## 1. 架构概览

项目按解耦分层组织：

- `app/domain`: 领域模型（纯数据，不依赖 UI 和存储）
- `app/services`: 业务逻辑（题目生成、会话流程、评分）
- `app/repositories`: 数据持久化（CSV 读写）
- `app/controllers`: UI 事件编排层（把用户动作映射为业务调用）
- `app/ui`: PyQt 页面与组件（展示和交互）
- `app/i18n`: 运行时国际化（key -> 文案）

关键原则：

1. UI 不直接访问 CSV 文件。
2. UI 不直接实现评分规则。
3. 服务层不依赖 PyQt 控件类型。
4. 控制器负责把业务结果转换成 UI 所需信号。

## 2. 核心数据流

### 开始练习

1. `SetupPage` 收集用户配置并发出 `start_requested`。
2. `MainWindow` 调用 `PracticeController.start_practice()`。
3. `SessionService.start()` 生成题目并初始化会话状态。
4. 控制器发出 `question_changed`，`PracticePage` 更新题目显示。

### 提交答案

1. `PracticePage` 发出 `submit_requested(answer)`。
2. 控制器调用 `SessionService.submit_answer()`。
3. 控制器发出 `answer_checked`，页面显示即时反馈。

### 完成会话

1. `PracticePage` 发出 `next_requested`。
2. 控制器调用 `SessionService.move_next()`。
3. 无下一题时调用 `SessionService.finish()` 生成 `SessionResult`。
4. `HistoryRepository.save_session()` 写入 `data/history.csv`。
5. 切换到 `SummaryPage` 展示结果和题目回顾。

### 历史查询

1. `HistoryPage` 发出 `search_requested(name_filter)`。
2. 控制器调用 `HistoryRepository.load_sessions()`。
3. 控制器发出 `history_loaded`，页面渲染表格与统计信息。

## 3. 国际化设计

国际化由 `Localizer` 统一提供：

- `Localizer.tr(key, **kwargs)`: 文案查询与格式化
- `Localizer.set_locale(locale)`: 切换语言
- `locale_changed` 信号: 通知页面刷新文案

新增文案流程：

1. 在 `app/i18n/localizer.py` 同时补充 `zh_CN` 和 `en_US` key。
2. 页面通过 `tr("key_name")` 使用，而不是硬编码字符串。
3. 若文案需要动态参数，使用占位符（例如 `{score}`）。

## 4. 注释与文档约定

已采用的约定：

- 模块级 docstring：说明模块职责和边界。
- 类级 docstring：说明该类在架构中的角色。
- 方法级 docstring：说明输入输出和调用语义。
- 仅在复杂逻辑处添加行内注释，避免无信息密度的注释。

建议新增代码时继续遵循以上约定。

## 5. 常见扩展点

### 5.1 新增题型

在 `ProblemGenerator._generate_by_operation()` 中新增操作分支，并：

- 更新 `SetupPage` 的操作选项
- 确保结果可被 `SessionService` 正常评分
- 必要时补充 i18n 文案 key

### 5.2 替换存储方式

新增一个 repository（如 SQLiteRepository），接口保持与 `HistoryRepository` 一致：

- `save_session(session: SessionResult) -> None`
- `load_sessions(name_filter: str = "") -> list[SessionResult]`

然后在 `MainWindow` 注入新的 repository 实例即可。

### 5.3 增加新语言

在 `Localizer._messages` 新增语言字典（如 `ja_JP`），并在 `SetupPage` 语言下拉中增加选项。

## 6. 本地开发检查

推荐每次修改后执行：

```bash
python -m compileall .
```

并在 IDE 中查看 lints，确保无新增错误。
