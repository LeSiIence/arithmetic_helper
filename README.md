# Arithmetic Practice Assistant (PyQt)

基于 `proposal.pdf` 需求实现的桌面练习系统，使用 Python + PyQt5，采用分层解耦设计。

## 功能覆盖

- 学生姓名输入（用于会话标识）
- 题目生成参数可配置
  - 运算类型：加减乘除、混合运算
  - 难度范围：1-10 / 1-50 / 1-100
  - 混合运算符数量
  - 括号开关与最大括号对数
  - 题目数量（5-50）
- 逐题作答与即时反馈（正确/错误）
- 手写数字识别（按钮识别 + 提交时自动识别兜底）
- 分数与正确率自动统计
- 会话结果自动保存到 `data/history.csv`
- 历史记录查询（按姓名过滤）与详情查看（题目、答案、正误）
- 儿童友好大字体界面（>=14pt）
- 支持中英文界面切换（Setup 页面 Language 下拉框）

## 解耦架构

- `app/domain`：纯数据模型
- `app/services`：题目生成、会话评分业务逻辑
- `app/repositories`：CSV 持久化读写
- `app/controllers`：UI 与业务层编排
- `app/ui`：页面组件与主窗口

## 运行

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 启动程序

```bash
python main.py
```

## 数据文件

- 历史记录默认保存为：`data/history.csv`

## 开发文档

- 架构、注释规范与扩展说明：`docs/DEVELOPMENT.md`
