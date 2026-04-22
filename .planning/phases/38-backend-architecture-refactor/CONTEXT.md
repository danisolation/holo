---
phase: 38
title: Backend Architecture Refactor
goal: Split two largest service files into focused single-responsibility modules
requirements: [BCK-04, BCK-05]
plans: 1
---

# Phase 38: Backend Architecture Refactor

## Context
AIAnalysisService (1235 LOC) and BacktestEngine (591 LOC) are the two largest backend services. Both are monoliths that mix orchestration, data access, external API calls, and business logic. This phase splits them into focused modules.

## Key Constraint
BacktestAnalysisService inherits AIAnalysisService and overrides 4 methods (all in the ContextBuilder group). The decomposition must preserve this inheritance chain or convert it to composition.
