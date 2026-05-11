# Mini Claude Code 项目计划

## 一、课程要求对照

**课程**: 统计计算语言学

| 要求 | 满足方式 |
|---|---|
| 计算语言学算法 | NL2Code（自然语言→代码）是计算语言学前沿方向 |
| LLM Agent 应用 | 三 Agent ReAct 协作架构（规划→编码→审查） |
| 智能体自动化协作 | Agent 链式调度，审查 Agent 自动拦截不合格输出 |
| Tool Use | 文件读写、命令执行、测试运行，完整工具链 |
| 数据量 2k+ | CodeXGLUE 公开数据集（bug fix / code refinement 子集） |
| 公开数据集可获取 | pip 安装或 GitHub 直接下载 |

---

## 二、项目概述

**做什么**: 用户用自然语言描述编程任务，三个 DeepSeek Agent 协作完成：

```
用户: "utils.py 的 divide 函数没有处理除零，帮我修一下"

规划Agent ──→ 读代码，分析问题，制定修改方案
      ↓
编码Agent ──→ 执行修改，跑测试验证
      ↓
审查Agent ──→ 检查 diff，确认修改正确、无副作用
      ↓
输出: 修改完成，3 个测试通过
```

**核心卖点**:
- 不是对话，是**干活**——Agent 真正读写文件、跑命令
- 三 Agent 互相制衡，审查 Agent 是"质量控制关卡"
- 有消融实验：拆掉某个 Agent 后性能下降多少

---

## 三、技术架构

```
┌──────────────┐
│  用户输入     │  "修一下 divide 的除零bug"
└──────┬───────┘
       ↓
┌──────────────────────────────────────────────┐
│              Orchestrator（调度器）            │
└──────────────────────────────────────────────┘
       ↓                ↓                ↓
┌──────────┐    ┌──────────┐    ┌──────────┐
│ 规划Agent │ →  │ 编码Agent │ →  │ 审查Agent │
│ System:  │    │ System:  │    │ System:  │
│ "你是架构 │    │ "你是程序 │    │ "你是代码 │
│  师，负责 │    │  员，负责 │    │  审查者， │
│  读代码、 │    │  写代码、 │    │  检查修改 │
│  定方案"  │    │  跑测试"  │    │  是否合格" │
└────┬─────┘    └────┬─────┘    └────┬─────┘
     │               │               │
     ▼               ▼               ▼
┌──────────────────────────────────────────────┐
│                 工具集 (Tools)                │
│  read_file | write_file | edit_file          │
│  run_command | run_tests | get_diff          │
└──────────────────────────────────────────────┘
```

### 工具定义

```python
TOOLS = {
    "read_file":  "读取文件内容，参数: file_path",
    "write_file": "创建/覆写文件，参数: file_path, content",
    "edit_file":  "精确替换文件中一段文本，参数: file_path, old, new",
    "run_command": "在隔离目录中执行命令，参数: cmd",
    "run_tests":  "运行测试并返回结果，参数: test_path",
    "get_diff":   "查看当前修改内容，参数: 无",
}
```

### 数据流

```
每个 Agent 的输出 = JSON
{
  "thought": "推理过程",
  "tool_calls": [
    {"name": "read_file", "args": {"file_path": "utils.py"}},
    {"name": "run_tests", "args": {"test_path": "tests/"}}
  ]
}

工具执行结果注入下一轮对话，每个 Agent 最多 N 轮工具调用
```

---

## 四、Demo 演示设计（答辩/汇报用）

三个演示场景，覆盖不同能力维度：

| Demo | 场景 | 展示能力 | 预估时长 |
|---|---|---|---|
| Demo 1 | 修复 utils.py 除零 bug | 理解+修改已有代码 | 30s |
| Demo 2 | 从零生成井字棋游戏 | 创造新代码 | 60s |
| Demo 3 | 给未测试的函数补单元测试 | 理解+补充代码 | 45s |

终端输出格式示例：

```
╔══════════════════════════════════════════════════╗
║              Mini Claude Code                    ║
║        多 Agent 编程助手                          ║
╚══════════════════════════════════════════════════╝

📝 任务: 修复 utils.py 的 divide 函数除零问题

┌─ 🔍 规划Agent ─────────────────────────────────┐
│ read_file("utils.py")                           │
│ 发现: divide(a,b) 没有处理 b==0 的情况           │
│ 方案: 加 if 判断 + ZeroDivisionError 捕获        │
└────────────────────────────────────────────────┘

┌─ ✏️ 编码Agent ──────────────────────────────────┐
│ edit_file("utils.py", "return a/b", new_code)   │
│ run_tests("test_utils.py")                      │
│ ✓ 3 passed                                     │
└────────────────────────────────────────────────┘

┌─ ✅ 审查Agent ──────────────────────────────────┐
│ get_diff()                                      │
│ + if b == 0: raise ValueError("除数不能为零")     │
│ 审查: ✓ 逻辑正确 ✓ 测试通过 ✓ 风格一致            │
└────────────────────────────────────────────────┘

✅ 完成: 修改 3 行，测试全部通过
```

---

## 五、数据集

### 来源

**CodeXGLUE** (微软, EMNLP 2020)
- 地址: https://github.com/microsoft/CodeXGLUE
- Code Refinement 子任务: bug 代码 → 修复后代码
- 规模: 训练集 ~50k，测试集 ~5k，取 2k 完全够
- 格式: JSONL，每条 `{"buggy": "...", "fixed": "...", "bug_type": "..."}`

### 用法

```
数据集双重身份:
  评测基准 ──→ 跑 500 条，统计通过率
  RAG 知识库 ──→ embedding 检索相似 bug 的修复方案 → 注入 Prompt
```

### RAG 管线

```
当前 bug 代码
    ↓ DeepSeek embeddings API
384维向量
    ↓ FAISS 检索
Top-3 相似历史修复案例
    ↓ 注入规划Agent的Prompt
"参考以下类似bug的修复方式: ..."
```

---

## 六、评测指标

| 指标 | 含义 | 计算方法 |
|---|---|---|
| 代码正确率 | 修改后测试通过 | pass_count / total |
| 工具调用成功率 | Tool Use 没出错 | tool_success / total_calls |
| 审查召回率 | 错误修改被审查拦截 | caught / total_errors |
| 平均耗时 | 完成任务的时间 | 总时间 / 任务数 |
| RAG 命中率 | 检索到的案例确实有用 | 人工标注或自动匹配 |

### 消融实验（必做，展示点）

| 实验组 | 配置 | 预期正确率 |
|---|---|---|
| 完整三 Agent | 规划 + 编码 + 审查 | 76% |
| 无审查 Agent | 规划 + 编码 | 62% |
| 无规划 Agent | 编码 + 审查 | 58% |
| 单 Agent | 一个 Agent 全做 | 51% |
| 三 Agent + RAG | 规划有 few-shot 参考 | 82% |

---

## 七、开发计划

### Phase 1: 基础设施（核心）

| # | 任务 | 产出 | 预估 |
|---|---|---|---|
| 1.1 | 创建 conda 环境 | `conda create -n minicc` | 5min |
| 1.2 | 工具层 Tools | `tools/file_tools.py`, `tools/exec_tools.py` | 1h |
| 1.3 | 代码沙箱 | 隔离目录 + `subprocess.run` | 30min |
| 1.4 | 单个 Agent 基类 | 通用 ReAct + Tool Use 循环 | 1.5h |
| 1.5 | DeepSeek Function Calling | API Schema 定义 + 调用封装 | 1h |

### Phase 2: 多 Agent 协作

| # | 任务 | 产出 | 预估 |
|---|---|---|---|
| 2.1 | 规划 Agent | System Prompt + read_file 工具 | 45min |
| 2.2 | 编码 Agent | System Prompt + write/edit/exec 工具 | 45min |
| 2.3 | 审查 Agent | System Prompt + read_file/diff 工具 | 45min |
| 2.4 | 调度器 Orchestrator | 串行调度 + 上下文传递 | 1h |

### Phase 3: 数据集 + RAG

| # | 任务 | 产出 | 预估 |
|---|---|---|---|
| 3.1 | 下载 CodeXGLUE 数据 | `data/codexglue_refinement.jsonl` | 30min |
| 3.2 | embedding + FAISS 索引 | `rag/index.faiss` | 1h |
| 3.3 | RAG 检索注入 | 规划Agent 接收 few-shot | 45min |

### Phase 4: 评测

| # | 任务 | 产出 | 预估 |
|---|---|---|---|
| 4.1 | 评测脚本 | `evaluate.py` | 1.5h |
| 4.2 | 消融实验 | 5 组对比指标 | 跑一夜 |
| 4.3 | 结果可视化 | 柱状图 + 表格 | 1h |

### Phase 5: Demo + 文档

| # | 任务 | 产出 | 预估 |
|---|---|---|---|
| 5.1 | 终端 Demo 脚本 | `demo.py`，交互式演示 | 1h |
| 5.2 | README | 项目文档 | 45min |

---

## 八、环境搭建注意事项

### Conda 环境

```bash
conda create -n minicc python=3.13 -y
conda activate minicc
pip install openai faiss-cpu numpy
# 不需要 torch, transformers, langchain, llamaindex
```

### 依赖极简原则

| 需要 | 不需要 |
|---|---|
| `openai` (DeepSeek SDK) | `langchain` / `llamaindex`（太重） |
| `faiss-cpu` (向量检索) | `torch` / `transformers`（不本地跑模型） |
| `numpy` (FAISS 依赖) | `chromadb` / `pinecone`（FAISS 更轻） |
| `subprocess` (内置) | `docker`（太复杂，目录隔离即可） |

### API 注意事项

- DeepSeek Function Calling 兼容 OpenAI 格式
- Tool 定义用 JSON Schema，注意参数类型声明
- 每次 Agent 对话保留 `tool_calls` → `tool_results` 的完整上下文

### 代码沙箱安全

- 专门建一个 `workspace/` 目录，Agent 所有操作限制在此目录内
- `subprocess.run` 加 `timeout=30` 防止死循环
- 禁止执行 `rm -rf /` 等危险命令（关键字过滤）
- 实际上大作业不需要严格安全措施，标注"仅供演示"即可

---

## 九、项目结构

```
mini-claude-code/
├── agents/
│   ├── __init__.py
│   ├── base_agent.py        # ReAct + Tool Use 通用循环
│   ├── planner.py           # 规划Agent
│   ├── coder.py             # 编码Agent
│   └── reviewer.py          # 审查Agent
├── tools/
│   ├── __init__.py
│   ├── file_tools.py        # read_file, write_file, edit_file
│   └── exec_tools.py        # run_command, run_tests
├── rag/
│   ├── __init__.py
│   ├── embedder.py          # embedding 生成
│   └── retriever.py         # FAISS 检索
├── orchestrator.py          # 调度三Agent串行
├── evaluate.py              # 评测脚本
├── demo.py                  # 终端交互Demo
├── data/
│   └── codexglue_refinement.jsonl  # 数据集
├── workspace/               # Agent 操作隔离目录
└── requirements.txt
```

---

## 十、潜在风险与应对

| 风险 | 应对 |
|---|---|
| CodeXGLUE 数据难下载 | 有镜像，或直接用 GitHub 上别人 clone 的 |
| DeepSeek Function Calling 不稳定 | 回退到纯 JSON Prompt 解析（你沙盘已经做过了） |
| FAISS 安装失败 | `pip install faiss-cpu` 在 Linux 下无问题 |
| API 调用太慢，评测跑不完 | 500 条约 30 分钟，可接受；或优化并发 |
| Agent 陷入死循环 | Tool Use 加 max_iterations=5 硬限制 |

---

## 十一、与沙盘项目的代码复用

| 沙盘代码 | 复用方式 |
|---|---|
| `call_deepseek_api()` | 直接复用，改参数名 |
| `parse_action()` / JSON 解析 | 直接复用 |
| `evaluate.py` 评测框架 | 改数据结构，框架不变 |
| conda 环境管理 | 新建环境，kangkang 配置复制 |
| System Prompt 设计模式 | 复用 ReAct 强约束风格 |
