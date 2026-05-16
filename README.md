# Mini Claude Code

## 基于统计学习的多智能体编程助手

**统计计算语言学 课程项目**

---

### 项目简介

Mini Claude Code 是一个面向 NL2Code（自然语言到代码）任务的多智能体协作框架。用户以自然语言描述编程需求，三个 DeepSeek Agent 通过 ReAct 范式串行协作——规划 Agent 分析代码并制定方案（Chain-of-Thought 推理），编码 Agent 执行修改并运行测试（支持 Self-Consistency 采样），审查 Agent 从四个维度检查修改质量并可驳回重试。

区别于单纯的 Agent 架构搭建，本项目的核心创新在于**"从数据中统计学习 → 反馈给语言模型 Agent"**的闭环管线：从微软 CodeXGLUE 数据集的 2,000 个历史代码修复案例中统计修复模式（fix pattern）分布，训练分类器预测修复类型，构建 RAG 检索索引，将统计知识注入规划 Agent 的推理过程。通过 LLM 语义分类与传统规则匹配的对比分析（"其他"未识别率从 52.5% 降至 13.8%），本项目实证了语言模型在形式语言（代码）上的语义理解优势。

### 课程要求对照

| 要求 | 实现 |
|------|------|
| 计算语言学算法 | NL2Code + 修复模式统计学习 + LLM 语义分类 |
| LLM Agent 应用 | 三 Agent ReAct 循环（规划/编码/审查） |
| 智能体自动化协作 | Orchestrator 串行调度 + 审查 Agent 自动驳回重试 |
| Tool Use | 6 个工具（read_file / write_file / edit_file / run_command / run_tests / get_diff） |
| 数据量 2k+ | CodeXGLUE 训练集 52k + 去混淆 Python 对 2,000 条 |
| 公开数据集可获取 | CodeXGLUE (Microsoft, EMNLP 2020) GitHub 直接下载 |

### 研究方法

1. **数据处理管线**：CodeXGLUE Java 代码 → DeepSeek API 翻译为 Python → LLM 语义分类修复类型 → 占位符去混淆为可读代码
2. **统计学习**：TF-IDF + Logistic Regression 分类器训练（8 类修复类型）、FAISS 向量索引构建（n-gram + IDF embedding）
3. **对比分析**：LLM 语义分类 vs 关键词规则匹配，定量验证 LLM 在代码语义理解上的优势
4. **消融实验**：6 种 Agent 配置（完整/无审查/无规划/单Agent/+统计/+分类器）在 Python 修复任务上的对比

### 实验结果摘要

| 配置 | 成功率 | 平均耗时 |
|------|--------|---------|
| single（单Agent） | 100% | 8.7s |
| full（三Agent） | 90% | 37.5s |
| +stats（注入统计分布） | 70% | 40.6s |

**核心发现**：对于简单 bug，轻量级配置最优；统计知识注入是一把"双刃剑"——在任务复杂度与统计先验不匹配时反而产生干扰。详见 `REPORT.md`。

### 项目结构

```
mini-claude-code/
├── agents/                  # 三 Agent 实现
│   ├── base_agent.py        # ReAct + Tool Use 通用循环
│   ├── llm_client.py        # DeepSeek API 封装 (OpenAI 兼容)
│   ├── planner.py           # 规划 Agent (CoT 推理 + 统计知识注入)
│   ├── coder.py             # 编码 Agent (工具执行 + Self-Consistency)
│   └── reviewer.py          # 审查 Agent (四维度质量把关)
├── tools/                   # 工具链
│   ├── file_tools.py        # read_file, write_file, edit_file
│   └── exec_tools.py        # run_command (沙箱), run_tests
├── rag/                     # 检索增强生成
│   ├── embedder.py          # Token n-gram + IDF 加权 embedding
│   └── retriever.py         # FAISS 最近邻检索
├── orchestrator.py          # 三 Agent 调度器 + 统计注入协调
├── train_classifier.py      # 修复类型分类器训练 (TF-IDF + Logistic Regression)
├── analyze_patterns.py      # Fix pattern 统计分析
├── generate_py_data.py      # Java→Python 翻译 + LLM 语义分类
├── deobfuscate.py           # 占位符去混淆 (断点续跑)
├── evaluate.py              # 消融实验框架 (增量 CSV)
├── demo.py                  # 交互式终端 Demo
├── REPORT.md                # 完整实验报告 (含参考文献)
├── data/                    # CodeXGLUE 数据集 + 处理后数据
│   ├── codexglue_2k.jsonl                # 2,000 条 Python 修复对 (混淆)
│   ├── codexglue_py_deobfuscated.jsonl   # 2,000 条 Python 修复对 (去混淆)
│   ├── fix_patterns.json                 # 修复类型统计分布
│   └── ablation_results.csv              # 消融实验结果
├── models/                  # 训练好的分类器
├── setup.sh                 # 一键环境安装
└── requirements.txt         # openai, faiss-cpu, numpy, scikit-learn, pytest
```

### 快速开始

```bash
# 1. 安装环境
bash setup.sh

# 2. 配置 API Key
cp .env.example .env
# 编辑 .env 填入 DeepSeek API Key
source .env

# 3. 运行交互 Demo
conda activate minicc
python demo.py 1           # Demo 1: 修复除零 bug
python demo.py 2           # Demo 2: 生成井字棋游戏
python demo.py 3           # Demo 3: 补单元测试
python demo.py -i          # 交互模式，自由对话
python demo.py -i --stats  # 交互模式 + 统计知识注入
python demo.py -i --rag    # 交互模式 + RAG 检索

# 4. 运行消融实验
python evaluate.py --limit 30

# 5. 重训分类器
python train_classifier.py
```

### 参考文献

- Yao et al., "ReAct: Synergizing Reasoning and Acting in Language Models", ICLR 2023
- Wang et al., "Self-Consistency Improves Chain of Thought Reasoning", ICLR 2023
- Wei et al., "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models", NeurIPS 2022
- Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks", NeurIPS 2020
- Du et al., "Improving Factuality through Multiagent Debate", 2023
- Lu et al., "CodeXGLUE: A Machine Learning Benchmark Dataset for Code Understanding", EMNLP 2020
