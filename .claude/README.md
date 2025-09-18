# Repository-Aware Prompt System

This repository implements a specialized coding assistant framework that prioritizes safety, context awareness, and efficient code organization.

## System Overview

The `.claude/` directory contains two critical files that must be read and understood before any code modifications:

### Project Context (`project-context.json`)
Contains immutable project information:
- Architecture patterns and tech stack
- Coding conventions and standards
- Business domain knowledge
- Security and performance considerations

### Session Memory (`session-memory.json`)
Contains dynamic session information:
- Previous decisions and rationale
- Pending tasks and priorities
- Established patterns and learnings
- Current system state

## Mandatory Behavioral Protocol

### 1. Context Analysis Phase
**ALWAYS start by reading both `.claude/` files before responding to any request**

### 2. Question-Answer Phase (QA)
For every implementation request, systematically gather:
- Technical clarity (which files, exact requirements, constraints)
- Context validation (conflicts, related tasks, patterns)
- Implementation boundaries (scope, dependencies)

**No implementation begins until ALL technical unknowns are resolved**

### 3. Approval-Required Planning
Present explicit implementation plan including:
- Files to be created/modified
- Architecture decisions and rationale
- Dependencies addressed
- **Require explicit approval before proceeding**

### 4. File Organization Rules
**Critical size limits:**
- Hard limit: 300 lines maximum per file
- Soft limit: Prefer under 200 lines
- Auto-split files approaching limits into semantic modules

### 5. Implementation Safety
- Validate all file paths
- Maintain backward compatibility
- Test structure before adding complex logic
- Document all decisions in session memory

## Current Project Context

**Domain:** Financial Trading Analysis (Brazilian Stock Market - B3)
**Tech Stack:** Python, pandas
**Data Source:** COTAHIST historical trading data
**Focus:** Pair trading strategies and liquidity analysis

**Established Patterns:**
- COTAHIST fixed-width file parsing
- Liquidity ranking by trading days frequency
- Portuguese naming conventions for business alignment
- CSV output with semicolon separators

## Usage Instructions

1. **Before any request:** AI agent reads both `.claude/` context files
2. **For implementation requests:** Complete QA phase to clarify requirements
3. **Get approval:** Present implementation plan and wait for confirmation
4. **Implement safely:** Follow file size limits and established patterns
5. **Document decisions:** Update session memory with new learnings

## File Structure

```
pair-trading/
├── .claude/
│   ├── project-context.json    # Immutable project knowledge
│   └── session-memory.json     # Dynamic session state
├── COTAHIST_A2016.TXT          # Raw B3 trading data (>50MB)
├── test.py                     # Main data processing script
└── top_100_liquidez_2016.csv   # Processed output (24,902 records)
```

## Success Criteria

Before each response, verify:
- [ ] Context files have been read and analyzed
- [ ] All clarifying questions have been asked
- [ ] Implementation plan is approved
- [ ] No files will exceed 300 lines
- [ ] Changes maintain established patterns
- [ ] Decisions are documented

This system ensures consistent, safe, and maintainable code evolution while preserving institutional knowledge across sessions.