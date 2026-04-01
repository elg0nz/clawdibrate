# Research: Multi-Agent CLI Abstraction Patterns

> Date: 2026-04-01 | Context: `loop.py` needs to shell out to arbitrary agent CLIs

## Problem

`AGENT_COMMANDS` in the bootstrap spec hardcodes 3 CLIs (claude, codex, opencode) using lambdas with incompatible invocation patterns. No extensibility, no config, KeyError on unknown agents.

## Tools Studied

### 1. dmux (standardagents/dmux)
- **Pattern:** Session multiplexer (tmux panes + git worktrees)
- **How:** 11 agents, 4 prompt transport methods: positional, option, stdin, send-keys
- **Key insight:** Doesn't abstract the CLI — orchestrates parallel native sessions
- **Repo:** https://github.com/standardagents/dmux

### 2. simonw/llm
- **Pattern:** Plugin registry (pluggy + Python entry points)
- **How:** Uniform CLI `llm -m model_id "prompt"`, 100+ backends via plugins
- **Key insight:** Provider-agnostic `Model` base class, `extra-openai-models.yaml` for zero-code additions
- **Repo:** https://github.com/simonw/llm

### 3. agent-mux (buildoak/agent-mux)
- **Pattern:** JSON contract dispatch with TOML config
- **How:** Roles mapped to engines in TOML, JSON stdin/stdout, NDJSON events on stderr
- **Key insight:** Variant system for runtime engine swapping, no code needed to add engines
- **Repo:** https://github.com/buildoak/agent-mux

### 4. Overstory (jayminwest/overstory)
- **Pattern:** Runtime adapter interface (TypeScript)
- **How:** `AgentRuntime` interface per CLI tool — spawn, config, guards, readiness, transcript parsing
- **Key insight:** SQLite mail system for inter-agent coordination
- **Repo:** https://github.com/jayminwest/overstory

### 5. aichat (sigoden/aichat)
- **Pattern:** Rust trait + macro-generated registry
- **How:** `Client` trait, `register_client!` macro, OpenAI-compatible adapter covers 17+ providers
- **Key insight:** One adapter implementation (OpenAI-compatible) handles the long tail
- **Repo:** https://github.com/sigoden/aichat

### 6. LiteLLM (BerriAI/litellm)
- **Pattern:** OpenAI-compatible proxy gateway
- **How:** Single `completion()` interface for 100+ providers, self-hosted
- **Key insight:** Everything normalized to OpenAI API format
- **Repo:** https://github.com/BerriAI/litellm

### 7. any-agent (Mozilla)
- **Pattern:** Framework parameter swap
- **How:** `AgentFramework` enum switches entire underlying framework (LangGraph, CrewAI, etc.)
- **Key insight:** Useful when you want to compare framework behavior, not just model behavior

## Two Abstraction Levels

| Level | Tools | Abstracts Over |
|-------|-------|---------------|
| **API-level** | simonw/llm, aichat, LiteLLM | Model APIs — you control agent logic, just need model access |
| **CLI-level** | dmux, agent-mux, Overstory | Agent CLI tools with their own loops, tools, permissions |

## Decision

**Hybrid approach for Clawdibrate:** template strings for built-in agents + `CLAWDIBRATE_AGENT_CMD` env var for any CLI. See `docs/v0_4_2/specs/agent-cli-abstraction.md`.

Rationale: Simpler than a plugin registry, more extensible than hardcoded lambdas. `simonw/llm` added as a built-in agent so users can access 100+ backends through it without us maintaining adapters.
