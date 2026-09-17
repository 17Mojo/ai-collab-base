# Pack Development Guide

**Version**: 1.0.0
**Last Updated**: 2026-09-14

This guide explains how to create custom Packs for ai-collab-base.

## Overview

A Pack is a JSON file defining:
- **Metadata**: ID, name, version, category
- **Workflow**: Steps executed in sequence
- **Branches**: Conditional flow control
- **Quality metrics**: Evaluation criteria

## Pack Structure

```json
{
  "metadata": {
    "pack_id": "my-pack-001",
    "pack_name": "My Custom Pack",
    "version": "1.0.0",
    "category": "productivity",
    "description": "What this pack does",
    "designer": "your-name",
    "created_at": "2026-09-14",
    "tags": ["custom", "example"]
  },
  "domain": {
    "primary_domain": "content-creation",
    "language": "zh-CN"
  },
  "workflow": {
    "steps": [
      {
        "id": "step1",
        "name": "Generate content",
        "type": "generation",
        "prompt": "Your prompt here",
        "output_field": "content"
      }
    ]
  },
  "quality_metrics": {
    "metrics": {
      "completeness": {
        "description": "Output completeness",
        "weight": 0.5,
        "min_threshold": 0.7
      }
    }
  }
}
```

## Step Types

| Type | Purpose | Required Fields |
|------|---------|-----------------|
|  | Collect user input | ,  |
|  | AI analysis | ,  |
|  | AI content generation | ,  |
|  | Output validation |  |
|  | Multi-output merge |  |
|  | Performance tracking |  |

## Branches

Add conditional logic to workflow:

```json
{
  "id": "step1",
  "branches": [
    {
      "condition_type": "regex_match",
      "target_step": "success_path",
      "regex_config": {
        "pattern": "^SUCCESS:",
        "flags": "i"
      }
    },
    {
      "condition_type": "contains",
      "target_step": "error_path",
      "value": "error"
    }
  ]
}
```

### Condition Types

- : Regex pattern match
- : String contains
- : Exact match
- : Numeric threshold
- : Field exists

## Creating a Pack

### Step 1: Copy Template

```bash
cp packs/examples/email-auto-reply.json packs/custom/my-pack.json
```

### Step 2: Edit Metadata

Update the metadata section:
- : Unique identifier (kebab-case)
- : Human-readable name
- : SemVer (1.0.0)
- : One of predefined categories
- : Clear purpose
- : Search keywords

### Step 3: Define Workflow

Add steps with clear input/output:

```json
{
  "id": "generate_title",
  "name": "Generate Title",
  "type": "generation",
  "prompt": "Generate a title for: {{input}}",
  "output_field": "title",
  "depends_on": ["collect_input"]
}
```

### Step 4: Add Branches (Optional)

For conditional flows:
- success path
- retry path
- error path
- human review path

### Step 5: Test

```bash
# Test in dry-run mode
python -m ai_collab.cli pack validate --file packs/custom/my-pack.json

# Run in sandbox
python -m ai_collab.cli pack execute --file packs/custom/my-pack.json --dry-run
```

## Best Practices

1. **Clear naming**: Use descriptive IDs and names
2. **Versioning**: Follow SemVer
3. **Documentation**: Add clear description
4. **Error handling**: Add error_path branches
5. **Testing**: Test before publishing

## Publishing

Once tested:
1. Add to  directory
2. Commit to git
3. Tag with version
4. Share with community

## Examples

See :
-  - Email responses
-  - Social media
-  - Video content

## Validation Rules

Common validation rules:
- length: Min/max characters
- keywords: Required terms
- format: Regex pattern
- sentiment: Positive/negative
- length_check: Exact word count

## Troubleshooting

### Pack will not load

- Check JSON syntax
- Verify metadata fields
- Test with validate command

### Steps do not execute

- Check step IDs match
- Verify output_field names
- Check dependency order

## See Also

- [API_DOCUMENTATION.md](API_DOCUMENTATION.md) (TBD)
- [USER_GUIDE.md](USER_GUIDE.md)
- [CHANGELOG.md](../CHANGELOG.md)
