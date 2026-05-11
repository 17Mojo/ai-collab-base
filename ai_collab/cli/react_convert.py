#!/usr/bin/env python3
"""
ReAct Requirement Conversion CLI
Command-line interface for converting Owner requirements to Pack drafts
"""

import argparse
import json
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from ai_collab.pack.react_converter import ConversionArtifacts, ReActConverter


def save_artifacts(artifacts: ConversionArtifacts, output_dir: str):
    """Save conversion artifacts to files"""
    os.makedirs(output_dir, exist_ok=True)

    # Save draft_pack.json
    draft_pack_path = os.path.join(output_dir, "draft_pack.json")
    with open(draft_pack_path, "w", encoding="utf-8") as f:
        json.dump(artifacts.draft_pack, f, ensure_ascii=False, indent=2)
    print(f"✓ Saved draft_pack.json to {draft_pack_path}")

    # Save change_manifest.md
    change_manifest_path = os.path.join(output_dir, "change_manifest.md")
    with open(change_manifest_path, "w", encoding="utf-8") as f:
        f.write("# Change Manifest\n\n")
        f.write(f"**Generated**: {datetime.now().isoformat()}\n\n")

        f.write("## Inherited Elements\n\n")
        if artifacts.change_manifest.inherited_elements:
            for elem in artifacts.change_manifest.inherited_elements:
                f.write(f"- **Source Pack**: {elem['source_pack']}\n")
                f.write(f"  - Elements: {', '.join(elem['elements'])}\n")
                f.write(f"  - Type: {elem['inheritance_type']}\n\n")
        else:
            f.write("None\n\n")

        f.write("## New Elements\n\n")
        for elem in artifacts.change_manifest.new_elements:
            f.write(f"- **{elem['element_name']}** ({elem['element_type']})\n")
            f.write(f"  - {elem['description']}\n\n")

        f.write("## Removed Elements\n\n")
        if artifacts.change_manifest.removed_elements:
            for elem in artifacts.change_manifest.removed_elements:
                f.write(f"- **{elem['element_name']}** ({elem['element_type']})\n")
                f.write(f"  - {elem['description']}\n\n")
        else:
            f.write("None\n\n")

        f.write("## Conflicts\n\n")
        if artifacts.change_manifest.conflicts:
            for conflict in artifacts.change_manifest.conflicts:
                f.write(f"- **{conflict.element_name}** ({conflict.conflict_type})\n")
                f.write(f"  - Source packs: {', '.join(conflict.source_packs)}\n")
                f.write(f"  - Description: {conflict.description}\n")
                if conflict.resolution:
                    f.write(f"  - Resolution: {conflict.resolution}\n")
                f.write("\n")
        else:
            f.write("None\n\n")

    print(f"✓ Saved change_manifest.md to {change_manifest_path}")

    # Save validation_report.md
    validation_report_path = os.path.join(output_dir, "validation_report.md")
    with open(validation_report_path, "w", encoding="utf-8") as f:
        f.write("# Validation Report\n\n")
        f.write(f"**Generated**: {datetime.now().isoformat()}\n\n")

        f.write("## Summary\n\n")
        f.write(f"- **Schema Valid**: {'✓' if artifacts.validation_report.schema_valid else '✗'}\n")
        f.write(
            f"- **Compliance Valid**: {'✓' if artifacts.validation_report.compliance_valid else '✗'}\n"
        )
        f.write(
            f"- **Status**: {artifacts.validation_report.schema_valid and artifacts.validation_report.compliance_valid and 'READY_FOR_OWNER_REVIEW' or 'BLOCKED'}\n\n"
        )

        f.write("## Checks\n\n")
        for check_name, check_result in artifacts.validation_report.checks.items():
            status = "✓" if check_result else "✗"
            f.write(f"- **{check_name}**: {status}\n")

        f.write("\n## Errors\n\n")
        if artifacts.validation_report.errors:
            for error in artifacts.validation_report.errors:
                f.write(f"- {error}\n")
        else:
            f.write("None\n")

        f.write("\n## Warnings\n\n")
        if artifacts.validation_report.warnings:
            for warning in artifacts.validation_report.warnings:
                f.write(f"- {warning}\n")
        else:
            f.write("None\n")

    print(f"✓ Saved validation_report.md to {validation_report_path}")

    # Save react_trace.json
    trace_path = os.path.join(output_dir, "react_trace.json")
    trace_data = []
    for trace in artifacts.traces:
        trace_data.append(
            {
                "stage": trace.stage.value,
                "timestamp": trace.timestamp,
                "input_data": trace.input_data,
                "output_data": trace.output_data,
                "reasoning": trace.reasoning,
                "actions": trace.actions,
                "observations": trace.observations,
            }
        )

    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(trace_data, f, ensure_ascii=False, indent=2)
    print(f"✓ Saved react_trace.json to {trace_path}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Convert Owner requirements to Pack drafts using ReAct pattern"
    )
    parser.add_argument("--requirement", "-r", required=True, help="Path to requirement JSON file")
    parser.add_argument(
        "--output",
        "-o",
        default="./conversion_output",
        help="Output directory for conversion artifacts (default: ./conversion_output)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    # Load requirement
    if not os.path.exists(args.requirement):
        print(f"Error: Requirement file not found: {args.requirement}")
        sys.exit(1)

    with open(args.requirement, "r", encoding="utf-8") as f:
        requirement = json.load(f)

    print(f"Converting requirement: {requirement.get('name', 'Unknown')}")
    print(f"Output directory: {args.output}")
    print()

    # Convert requirement
    converter = ReActConverter()
    artifacts = converter.convert(requirement)

    # Save artifacts
    save_artifacts(artifacts, args.output)

    # Print summary
    print()
    print("=" * 60)
    print("Conversion Summary")
    print("=" * 60)
    print(f"Draft Pack ID: {artifacts.draft_pack['metadata']['pack_id']}")
    print(f"Draft Pack Name: {artifacts.draft_pack['metadata']['pack_name']}")
    print(f"Workflow Steps: {len(artifacts.draft_pack['workflow']['steps'])}")
    print(f"Quality Metrics: {len(artifacts.draft_pack['quality_metrics']['metrics'])}")
    print(f"Schema Valid: {artifacts.validation_report.schema_valid}")
    print(f"Compliance Valid: {artifacts.validation_report.compliance_valid}")

    status = (
        "READY_FOR_OWNER_REVIEW"
        if (
            artifacts.validation_report.schema_valid
            and artifacts.validation_report.compliance_valid
        )
        else "BLOCKED"
    )
    print(f"Status: {status}")

    if artifacts.validation_report.errors:
        print()
        print("Errors:")
        for error in artifacts.validation_report.errors:
            print(f"  - {error}")

    if args.verbose:
        print()
        print("ReAct Traces:")
        for trace in artifacts.traces:
            print(f"  Stage: {trace.stage.value}")
            print(f"    Reasoning: {trace.reasoning}")
            print(f"    Actions: {', '.join(trace.actions)}")
            print(f"    Observations: {', '.join(trace.observations)}")
            print()

    print("=" * 60)
    print("Conversion completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
