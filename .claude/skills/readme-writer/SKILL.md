---
name: readme-writer
description: Generate comprehensive README.md files by analyzing codebase structure, dependencies, and architecture. Use when the user wants to (1) create a new README.md, (2) update or improve existing README, (3) document a project for open source release, (4) generate project documentation, or (5) asks "write a README" or "document this project".
---

# README Writer

Generate professional README.md files through systematic codebase analysis.

## README Generation Workflow

1. **Analyze project structure** - Identify project type, language, and framework
2. **Extract metadata** - Parse package.json, pyproject.toml, Cargo.toml, etc.
3. **Identify key components** - Find entry points, main modules, and architecture
4. **Detect setup requirements** - Environment variables, dependencies, prerequisites
5. **Generate README** - Write comprehensive documentation following best practices

## Analysis Steps

### Step 1: Identify Project Type

Check for configuration files to determine project type:

```
pyproject.toml, setup.py, requirements.txt → Python
package.json → Node.js/JavaScript
Cargo.toml → Rust
go.mod → Go
pom.xml, build.gradle → Java
```

### Step 2: Extract Project Metadata

Parse the main config file for:
- Project name and version
- Description
- Dependencies
- Scripts/commands
- Author information

### Step 3: Analyze Architecture

1. Read main entry points (main.py, index.js, src/main.rs, etc.)
2. Identify key modules and their purposes
3. Map API endpoints (if web project)
4. Document database schema (if applicable)

### Step 4: Identify Setup Requirements

Check for:
- `.env.example` or environment variable usage
- Docker/docker-compose files
- Database migrations
- External service dependencies (APIs, databases)

## README Structure

Generate README with these sections (include only relevant ones):

```markdown
# Project Name

Brief description (1-2 sentences)

## Features
- Key feature 1
- Key feature 2

## Prerequisites
- Required software
- Required accounts/API keys

## Installation

## Configuration
Environment variables and settings

## Usage
Basic usage examples

## API Reference (if applicable)
Endpoints and methods

## Architecture (if complex)
High-level component overview

## Development
How to contribute/develop

## License
```

## Writing Guidelines

- Be concise - avoid verbose explanations
- Use code blocks for all commands
- Include actual examples, not placeholders
- Skip sections that don't apply
- Match the project's language (Korean/English based on existing docs)

## Reference

See `references/section-templates.md` for detailed section examples.
