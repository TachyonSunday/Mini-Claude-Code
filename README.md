# Mini Claude Code

多 Agent 编程助手 — 统计计算语言学课程项目。

用户用自然语言描述编程任务，三个 DeepSeek Agent（规划→编码→审查）协作完成编程工作流。

## 快速开始

```bash
# 1. 一键安装
bash setup.sh

# 2. 配置 API Key
cp .env.example .env
# 编辑 .env，填入你的 DeepSeek API Key
source .env

# 3. 运行 Demo
conda activate minicc
python demo.py 1    # 修复除零 bug
python demo.py 2    # 生成井字棋游戏
python demo.py 3    # 补单元测试

# 4. 运行评测
python evaluate.py --limit 50
```

## 分发给别人

```bash
# 打包（不含 API key 和数据索引）
tar czf mini-claude-code.tar.gz \
    --exclude='.env' \
    --exclude='data/*.faiss' \
    --exclude='data/*_meta.jsonl' \
    --exclude='__pycache__' \
    mini-claude-code/

# 接收方
tar xzf mini-claude-code.tar.gz
cd mini-claude-code
bash setup.sh
# 配置 .env → source .env → python demo.py 1
```

## 项目结构

```
mini-claude-code/
├── agents/
│   ├── base_agent.py      # ReAct + Tool Use 通用循环
│   ├── llm_client.py      # DeepSeek API 封装
│   ├── planner.py         # 规划Agent (读代码定方案)
│   ├── coder.py           # 编码Agent (写代码跑测试)
│   └── reviewer.py        # 审查Agent (检查diff把关)
├── tools/
│   ├── file_tools.py      # read_file, write_file, edit_file
│   └── exec_tools.py      # run_command, run_tests
├── rag/
│   ├── embedder.py        # embedding 生成
│   └── retriever.py       # FAISS 检索
├── orchestrator.py        # 三Agent串行调度器
├── evaluate.py            # 评测 + 消融实验
├── demo.py                # 终端交互Demo
├── setup.sh               # 一键安装脚本
├── .env.example           # API Key 配置模板
├── data/                  # CodeXGLUE 数据集
├── workspace/             # Agent 操作隔离目录
└── requirements.txt       # openai, faiss-cpu, numpy, pytest
```

## 架构

```
用户输入
  ↓
Orchestrator (调度器)
  ├── 规划Agent ─→ read_file ─→ 分析问题 + 出方案
  ├── 编码Agent ─→ edit/write/run_tests ─→ 执行修改
  └── 审查Agent ─→ get_diff/read_file ─→ 通过或驳回
                            ↓
                       最终输出
```

## 评测指标

- **代码正确率**: 修改后测试通过率
- **消融实验**: 完整三Agent vs 无审查 vs 无规划 vs 单Agent
- **RAG 增强**: few-shot 相似案例检索注入
