# RealCheck MVP Work Plan

This is the updated work plan derived from current MVP status and external pattern research. It outlines the architectural direction, module responsibilities, and a concrete growth path.

## 1) Architecture Overview
- Goal: A clean, modular pipeline that separates API, AI model, and utilities.
- Core modules:
  - app.api.routes: API layer that wires inputs to a pluggable AI model interface
  - app.models.ai_detector: Real AIModel implementation (swap-in-friendly)
  - app.utils.image_processor: Image processing utilities
  - app.config: Environment-driven configuration
- Pattern: Adapter/wactory (factory) that selects MockAIModel or AIModel based on configuration.

## 2) MVP Extension Targets
1) Introduce a single AI model interface with two implementations:
   - MockAIModel (existing MVP fast path)
   - AIModel (real/production path)
2) Lightweight DI wrapper to instantiate the proper model based on config.
3) Refactor API routes to always interact with the AI model via the interface/wrapper.
4) Move heavy dependencies behind lazy imports; keep requirements minimal for MVP.
5) Add tests for wrapper behavior and API path integration.
6) Implement CI (GitHub Actions) to run tests on pushes.
7) Add input validation tests for file type/size constraints.
8) Update docs with architecture decisions and next steps.

## 3) Task Breakdown (summary)
- T1: Interface consolidation and adapter
- T2: DI wrapper implementation
- T3: API refactor to interface
- T4: Dependency lazy loading and MVP dependency pruning
- T5: Unit tests for wrapper and API path
- T6: Expanded input tests (1-5 images, performance hints)
- T7: CI workflow
- T8: Validation tests for upload inputs
- T9: Documentation updates
- T10: Lightweight perf benchmarks and profiling

## 4) Decision Log Highlights
- Priority for MVP extension is to stable the interface and ensure testability.
- Heavy ML frameworks to be kept behind lazy imports or optional installs until performance needs prove.

## 5) Next Steps
- Start with T1 and T2 in the next iteration.
- Report progress via TODO status and diagnostics after each task.
