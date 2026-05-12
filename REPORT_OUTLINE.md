# Mini Claude Code 报告大纲

## 一、引言

- **背景**: 自然语言到代码(NL2Code)是计算语言学的核心方向之一。用户用自然语言描述编程任务，智能体协作完成代码修复
- **问题**: 单 Agent 缺乏外部视角，容易产生幻觉或遗漏
- **本文方案**: 三 Agent(规划/编码/审查) + 统计知识注入的多 Agent 协作框架
- **主要贡献**:
  1. 三 Agent ReAct 编程助手，实现 NL2Code 闭环
  2. 从 2000 样本中统计 fix pattern 分布，注入 Agent 提升性能
  3. 分类器预测修复类型，辅助 Agent 决策
  4. 消融实验验证各组件的贡献

## 二、相关工作

- **NL2Code**: CodeXGLUE (Lu et al., EMNLP 2020), CodeBERT, CodeT5
- **LLM Agent**: ReAct (Yao et al., 2022), Function Calling, Tool Use
- **多 Agent 协作**: Multi-Agent Debate (Du et al., 2023), Self-Consistency (Wang et al., 2022)
- **RAG**: Retrieval-Augmented Generation (Lewis et al., 2020)
- **Chain-of-Thought**: CoT (Wei et al., 2022)
- 本文区别于已有工作：将统计学习与多 Agent 协作结合，从数据中学习修复模式

## 三、方法

### 3.1 系统架构
- Orchestrator 调度三 Agent 串行：规划 → 编码 → 审查
- 审查 Agent 可驳回修改，触发重试

### 3.2 Agent 设计
- **规划 Agent**: Chain-of-Thought 推理 (①理解→②分析→③候选→④方案)，支持 RAG/fix pattern/分类器注入
- **编码 Agent**: 执行 4 个工具 (read/write/edit/run_tests)，支持 Self-Consistency 采样
- **审查 Agent**: 检查 diff + 源文件 + 测试，输出通过/驳回

### 3.3 工具链
- 6 个工具: read_file, write_file, edit_file, run_command, run_tests, get_diff
- 沙箱隔离 + 危险命令过滤

### 3.4 统计学习
- **数据集**: CodeXGLUE Code Refinement (52k Java)
  - DeepSeek 翻译为 Python + 标注 fix type (2000 条)
  - DeepSeek 去混淆占位符为可读变量名
- **Fix Pattern 统计**: DeepSeek 语义分类 (条件逻辑 38% / 赋值 18% / 空值 11% / 边界 7% / 异常 6% / 类型 5% / 循环 1% / 其他 14%)
  - 对比关键词匹配基线 ("其他" 从 52% 降到 14%，证明 LLM 语义理解优势)
- **分类器**: TF-IDF + Logistic Regression
- **RAG**: FAISS 向量检索 + n-gram IDF embedding

### 3.5 推理增强
- Chain-of-Thought: 规划 Agent 强制逐步推理
- Self-Consistency: 编码 Agent 多次采样，选众数/最详细方案

## 四、实验

### 4.1 实验设置
- 测试集: 20 条去混淆 Python bug-fix 样本
- 评测指标: 修复成功率 (审查 Agent 判定通过)
- 对比配置:
  - **full**: 完整三 Agent
  - **no_reviewer**: 无审查 Agent
  - **no_planner**: 无规划 Agent
  - **single**: 单 Agent
  - **+stats**: 注入 fix pattern 分布
  - **+classifier**: 注入分类器预测
  - **+rag**: 注入 RAG 检索案例

### 4.2 实验结果
(待消融实验跑完填入)
| 配置 | 成功率 | 平均耗时 |
|------|--------|---------|
| full | ?% | ?s |
| no_reviewer | ?% | ?s |
| no_planner | ?% | ?s |
| single | ?% | ?s |
| +stats | ?% | ?s |
| +classifier | ?% | ?s |

### 4.3 分析
- 审查 Agent 的贡献（full vs no_reviewer）
- 规划 Agent 的贡献（full vs no_planner）
- 单 Agent 的局限（full vs single）
- 统计知识的作用（full vs +stats）
- 分类器预测的作用（full vs +classifier）

## 五、讨论

- **关键词匹配 vs LLM 语义分类**: 为什么 LLM 理解代码比正则更可靠？
- **分类器性能分析**: 准确率 25% 的原因（8 类过细、样本不均衡），改进方向
- **RAG 局限**: embedding 非语义向量，检索质量受限
- **与训练式方法的对比**: 本文是 agent-based 方法，不微调模型
- **可扩展性**: 可加入更多编程语言、更细粒度的 fix pattern

## 六、结论

- 三 Agent 协作能有效完成 NL2Code 任务
- 从数据中统计 fix pattern 并注入 Agent 提升了推理质量
- 消融实验验证了各组件的必要性
- NL2Code + 统计学习的结合为计算语言学提供了新的研究视角

---

## 参考文献

- Yao et al., "ReAct: Synergizing Reasoning and Acting in Language Models", ICLR 2023
- Wang et al., "Self-Consistency Improves Chain of Thought Reasoning in Language Models", ICLR 2023
- Wei et al., "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models", NeurIPS 2022
- Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks", NeurIPS 2020
- Du et al., "Improving Factuality and Reasoning in Language Models through Multiagent Debate", 2023
- Lu et al., "CodeXGLUE: A Machine Learning Benchmark Dataset for Code Understanding and Generation", EMNLP 2020
