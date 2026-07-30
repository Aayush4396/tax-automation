---
name: meta-prompt-generator
description: Analyzes project requirements or codebase state and generates structured Meta-Prompts that instruct AI agents to build custom skills, workflows, and automated pipelines, with automatic persistence to project memory folders (.memory/).
---

# Meta-Prompt Generator Skill

## Objective
Generate production-grade Meta-Prompts tailored for Google Antigravity AI Agents to automate complex development tasks, workflow generation, skill creation, and architecture refactoring following official Antigravity standards.

---

## Antigravity Customizations Specification

### 1. Skills Specification
- **Path**: `.agents/skills/<skill-name>/SKILL.md`
- **File Format**: Markdown (`.md`) with YAML frontmatter (`name`, `description`).
- **Body**: Detailed step-by-step instructions (under 500 lines). Optional supporting resources in `scripts/`, `examples/`, `resources/`, `references/`.

### 2. Workflows Specification (per https://antigravity.google/docs/ide/workflows)
- **Path**: `.agents/workflows/<workflow-name>.md` (or `.antigravity/workflows/<workflow-name>.md`)
- **File Format**: Markdown (`.md`) with optional YAML frontmatter (`description`).
- **Description Box (0/250)**: Include YAML frontmatter at the top of the workflow file with a `description:` key (max 250 characters). The Antigravity IDE workflow editor automatically populates the UI Description box from this field.
  ```yaml
  ---
  description: Brief workflow summary (Max 250 characters)
  ---
  ```
- **Character Limit**: Limited to **12,000 characters** per workflow file.
- **Invocation**: Triggered in chat via slash command `/<workflow-name>`.
- **Chaining**: Workflows can call other workflows using slash command syntax (e.g., `"Run /process-entity-taxes"`).
- **Structure**: Clear title (`# Workflow: Name`), high-level description, sequential step-by-step trajectory instructions, human approval gates, and expected artifacts.

---

## Execution Steps

### Step 1: Context & Intent Gathering
1. **Analyze User Goal:** Identify whether the target task is a backend refactor, feature integration, database migration, test suite setup, or architecture cleanup.
2. **Deep Codebase Scan:**
   * Detect key frameworks, monolithic entry points, dependency managers, and database models.
   * Identify missing modular abstractions, service layers, and integration points.
   * **Inventory all files** across all relevant directories — list file names, sizes, and paths.
   * **Detect duplication** — compare files by name and size across directories; flag files that appear duplicated but have different sizes (they contain environment/context-specific logic that must NOT be naively merged).
   * **Catalog data vs. code** — identify which directories contain source code vs. runtime data/output so the restructured layout separates them cleanly.
   * **Check for CI/pipeline scripts** — shell scripts (.sh, .ps1, .bat) that orchestrate multi-step workflows.

3. **Hardcoded Logic & Entity Detection (MANDATORY):**

   Perform a systematic grep/search across the entire codebase. For every match found, record the file, line number, and the hardcoded value. This inventory drives the externalization plan in the output Meta-Prompt.

   #### Categories to Scan

   | Category | What to Search For |
   |:---------|:-------------------|
   | **Filesystem Paths** | Absolute paths to directories or files (`Path(r"...")`, `"/home/..."`, `"C:\..."`) |
   | **Identity / Entity Names** | Names of people, orgs, tenants, or environments embedded in code (regex patterns, string literals, f-strings, variable names) |
   | **Account / Resource IDs** | Identifiers for external accounts, resources, or services (API account IDs, database names, bucket names) |
   | **Passwords & Secrets** | Plaintext passwords, API keys, tokens, or credentials |
   | **Reference Numbers & Lists** | Hardcoded lists of IDs, transaction refs, or lookup values that change over time or per context |
   | **Output Filenames & Templates** | Hardcoded output file naming conventions with embedded entity/context names |
   | **Skip / Include Lists** | Sets or lists of names used to filter, skip, or include items (sheet names, table names, etc.) |
   | **Data Mappings** | Hardcoded lookup tables mapping files to targets, names to categories, etc. |
   | **Regex with Embedded Names** | Regular expressions that contain literal names, IDs, or values that vary per context |
   | **Magic Constants** | Thresholds, version labels, date ranges, or other values that should be configurable |

   #### Externalization Strategy

   For each category of hardcoded value discovered, decide on the most appropriate **externalization target**:

   | Externalization Target | Best For |
   |:-----------------------|:---------|
   | **JSON config files** (`config/<context>.json`) | Structured data: ID registries, data mappings, file-to-target mappings, skip/include lists, output filename templates |
   | **YAML config files** (`config/<context>.yaml`) | Same as JSON, but when human readability and inline comments are important |
   | **Environment variables / `.env` files** | Passwords, secrets, API keys, tokens — values that must not be committed to version control |
   | **Profile / context modules** (`profiles/<context>.py`) | Complex logic that requires code expressions (lambdas, regex builders, conditionals) and varies per entity/context |
   | **CLI arguments** | Values that change per invocation (entity name, date range, environment label, base paths) |
   | **Path resolution from CLI args** | All absolute filesystem paths — derive from a base directory + context at runtime instead of hardcoding |

   #### Generalization Patterns

   When a hardcoded value can be **generalized** (replaced with a template or derived at runtime) instead of externalized to a config file, prefer generalization:

   - **Hardcoded entity name in filename** → Use f-string template: `f"{entity}_Output_{label}.ext"`
   - **Hardcoded absolute path** → Derive from: `project_root / "data" / context / sub_path`
   - **Hardcoded lookup dict** → Generate from profile/config at runtime
   - **Hardcoded skip list** → Load from profile config
   - **Hardcoded data mapping** → Load from JSON/YAML config per context

### Step 2: Meta-Prompt Architecture Construction
Construct the Meta-Prompt using the standard **Antigravity Meta-Prompt Framework**:

1. **Role Definition:** Assign a specialized persona (e.g., *Principal Software Architect*, *DevOps Lead*).
2. **Objective Statement:** Clear purpose and expected outcomes.
3. **Codebase Findings Table:** Present a side-by-side comparison table showing every file, its size per location, and whether it's identical or divergent. This prevents data loss during refactoring.
4. **Hardcoded Logic Inventory:** Present a complete table of every hardcoded value found, organized by category, with file/line locations and the chosen externalization strategy.
5. **Step-by-Step Execution Plan:**
   * **Phase 1: Inspection & Discovery:** Scanning legacy code, frameworks, dependencies. Include file-by-file diff analysis for duplicated-but-divergent files.
   * **Phase 2: Hardcoded Logic Extraction:** For each category, extract values into the chosen externalization target (JSON, YAML, .env, profile module, or CLI arg). Create the config file structure.
   * **Phase 3: Architecture Design:** Propose target directory layout with explicit annotations showing where each current file maps to. Mark files as `✅ Identical (safe merge)` or `⚠️ Divergent (needs context-specific extraction)`.
   * **Phase 4: Generalization:** Replace hardcoded patterns in code with template-based or config-driven lookups. Every absolute path, entity name, and resource ID in source code should resolve from configuration at runtime.
   * **Phase 5: Custom Skills Creation (`.agents/skills/`):** Define names, frontmatter descriptions, and execution logic.
   * **Phase 6: Custom Workflows Creation (`.agents/workflows/`):** Define workflows with sequential steps, human approval gates, YAML `description` frontmatter, slash command triggers, and artifact requirements.
6. **Memory & Persistence Rules:** Instruct the agent to store the generated prompt in the repository's `.memory/` or `.antigravity/memory/` directory.

### Step 3: Validation Checklist
Before finalizing the Meta-Prompt, verify:
- [ ] Every source file in the current codebase has an explicit destination in the proposed structure.
- [ ] Files that differ across copies are handled with a merge/extension strategy, not naive deduplication.
- [ ] **Every hardcoded value** has been cataloged and assigned an externalization strategy or generalization pattern.
- [ ] **No absolute paths** remain in source code — all paths derive from config or CLI args at runtime.
- [ ] **No entity/context names** are hardcoded in source code — all are loaded from profile config or CLI flags.
- [ ] **No passwords or secrets** remain in source code — all are in `.env` or prompted at runtime.
- [ ] Workflows are specified under `.agents/workflows/<workflow-name>.md` with YAML `description` frontmatter (max 250 chars), slash commands `/<workflow-name>`, and character counts under 12,000.
- [ ] Skills are specified under `.agents/skills/<skill-name>/SKILL.md` with YAML frontmatter.
- [ ] Data directories are preserved with their existing layout under the new structure.
- [ ] CI/pipeline scripts, READMEs, and documentation files are accounted for.
- [ ] A verification/regression testing plan exists to compare outputs before and after restructuring.

---

## Output Template Structure

When invoked, output the complete Meta-Prompt formatted like this:

```text
Act as a [Target Role, e.g., Principal Software Architect] specializing in [Domain].

Your objective is to inspect [Target Codebase / Problem Context] and automatically generate a suite of project-specific Antigravity Workflows and Skills.

---

### Codebase Findings & File Inventory
[Side-by-side file comparison table showing sizes, divergences, and context-specific data]

---

### Hardcoded Logic Inventory
[Table of every hardcoded value found, organized by category, with file/line locations and externalization strategy]

### Externalization Plan
[For each category: target format (JSON/YAML/.env/profile module/CLI arg), file path, and example content]

---

### Step 1: Target Architecture
[Complete directory tree with annotations for each file's origin and merge strategy]
[Include config/ directory structure with JSON/YAML files]

---

### Step 2: Hardcoded Logic Extraction
[Phase-by-phase plan to extract hardcoded values into config files and generalize code]

---

### Step 3: Auto-Generate Workspace Skills
Create the following custom skills inside `.agents/skills/`:
1. `.agents/skills/[skill-name-1]/SKILL.md`
   - Frontmatter (`name`, `description`)
   - Detailed step-by-step instructions

---

### Step 4: Auto-Generate Workspace Workflows
Create the following custom workflows inside `.agents/workflows/`:
1. `.agents/workflows/[workflow-name-1].md`
   - YAML frontmatter with `description` (Max 250 chars)
   - Step-by-step trajectory instructions, approval gates, slash commands, and artifact requirements.
   - Character limit: <= 12,000 characters.

---

### Step 5: Save & Persist to Repository Memory
Save this generated Meta-Prompt into the project memory directory so it is preserved across agent chat sessions:

* Primary Memory Location: `.memory/prompts/[meta-prompt-name].md`
* Alternative Memory Location: `.antigravity/memory/[meta-prompt-name].md`

---

### Execution Rules
1. Write all output files directly into the repository using your file-writing tools.
2. Store workspace skills in `.agents/skills/<skill-name>/SKILL.md` and workspace workflows in `.agents/workflows/<workflow-name>.md`.
3. Ensure all workflow files include YAML `description:` frontmatter (under 250 characters) so the Antigravity IDE workflow UI automatically populates the Description box.
4. NEVER naively merge files that differ across copies — extract shared base + context-specific extensions.
5. NEVER leave hardcoded paths, entity names, resource IDs, or passwords in source code after restructuring.
6. Validate output parity by running the system before and after restructuring.
7. Once generated, summarize the created workflows and provide the slash commands to execute them:
   - `/[workflow-name-1]`
```