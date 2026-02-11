# Skill Validation Checklist

Run through every item after creating a skill.

## Structure

- [ ] `SKILL.md` exists at skill root
- [ ] `IMPROVEMENTS.md` exists at skill root
- [ ] No `README.md` in skill root
- [ ] No `CHANGELOG.md` in skill root
- [ ] No `INSTALLATION_GUIDE.md` in skill root
- [ ] No `QUICK_REFERENCE.md` in skill root
- [ ] Only directories that contain files exist (no empty dirs)

## YAML Frontmatter

- [ ] Valid YAML between `---` markers (first two lines of file)
- [ ] `name` field: lowercase letters, numbers, and hyphens only
- [ ] `name` field: max 64 characters
- [ ] `description` field: present and non-empty
- [ ] `description` field: max 200 characters
- [ ] `description` includes WHAT the skill does
- [ ] `description` includes WHEN to use it
- [ ] `disable-model-invocation: true` if skill has side effects
- [ ] `allowed-tools` is set (principle of least privilege)

## Body

- [ ] Under 500 lines total (including frontmatter)
- [ ] Uses imperative form ("Extract data", not "This skill extracts")
- [ ] References supporting files with explicit paths when they exist
- [ ] No "When to Use" section (belongs in description only)
- [ ] No duplicate content between body and reference files
- [ ] Includes Self-Improvement Protocol section

## IMPROVEMENTS.md

- [ ] Header explains the log-only pattern
- [ ] Format section documents: Date, Context, Observation, Suggested change
- [ ] Separator line before entries area
- [ ] No actual entries yet (starts empty for new skills)

## Supporting Files (if present)

- [ ] References are max one level deep from skill root
- [ ] Scripts are executable (`chmod +x`)
- [ ] No deeply nested directory structures
- [ ] Every file is referenced from SKILL.md or another loaded file
