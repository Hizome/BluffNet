# BluffNet AI API 接入执行计划

## 目标
在现有 BluffNet 架构上，完成“通过外部 LLM API 驱动 AI 打牌”的稳定可用版本，并具备可观测性与可配置能力。

## 状态说明
- `TODO`: 未开始
- `DOING`: 进行中
- `DONE`: 已完成

## 执行清单
| ID | 任务 | 状态 | 完成标准 |
| --- | --- | --- | --- |
| P0 | 建立执行计划文档并开始跟踪 | DONE | 本文件创建，后续按任务更新状态 |
| P1 | LLM 调用稳定性增强（超时/重试/回退） | DONE | `llm_client.py` 支持失败重试、明确回退策略、错误日志可读 |
| P2 | LLM 决策输入约束化（合法动作与下注边界） | DONE | `agents.py` 在 prompt 中传入合法动作与 raise 边界，减少非法输出 |
| P3 | 配置层可观测性增强 | DONE | 增加配置与执行相关日志/返回字段，能定位 profile 与 agent 问题 |
| P4 | 前端 Dashboard 增加 Agent/Profile 配置入口 | DONE | 在 `DashboardView.vue` 可直接配置 `agent_type/profile` 并保存 |
| P5 | 文档与联调示例更新 | DONE | `doc/ai_integration.md` 增加最新配置示例与排障说明 |
| P6 | 回归验证 | DONE | 完成后端基本运行验证与关键接口验证，记录结果 |

## 更新记录
- 2026-02-17: 创建计划并开始状态跟踪（P0 完成）。
- 2026-02-17: 完成 P1，`backend/llm_client.py` 已加入超时配置、指数退避重试、错误日志与统一 fallback。
- 2026-02-17: 完成 P2，`backend/agents.py` 已加入 legal_actions / raise_bounds 输入和本地动作约束。
- 2026-02-17: 完成 P3，新增 `/config/llm_profiles`，并在 `/config/agents`、`/config/agent` 返回 LLM 诊断信息（model/base_url/has_api_key），`engine` 增加配置变更日志。
- 2026-02-17: 完成 P4，Dashboard 支持直接设置每个玩家 `agent_type/profile` 并显示 key 可用性状态。
- 2026-02-17: 完成 P5，`doc/ai_integration.md` 已补充 profile 发现接口、稳定性参数与 Dashboard 配置流程。
- 2026-02-17: 完成 P6，已通过 `python -m py_compile backend/*.py`、随机 agent 烟测（10 steps）和 `npm --prefix frontend run build`。
- 2026-02-17: 扩展完成 `openai/anthropic` 双协议支持，`LLM_{PROFILE}_PROVIDER` 可切换调用路径；新增 MiniMax Anthropic 配置模板。
- 2026-02-17: 回滚 `minimax_chat`（`chatcompletion_v2`）接入代码，当前仅保留 `openai/anthropic` 运行路径。

## Future Plan
- 评估并设计 `MiniMax chatcompletion_v2` 的独立接入方案（请求协议、消息角色映射、错误码处理），待需求明确后再实现。
