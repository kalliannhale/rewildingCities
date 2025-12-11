# experiment.py

from canopy.orchestrator import run_experiment

result = run_experiment(
    "garden/experiments/test_soil_pipeline.yml",
    profile="dev"
)

print(f"Success: {result.success}")
print(f"Completed steps: {result.completed_steps}")

# Add this:
if hasattr(result, 'error') and result.error:
    print(f"Error: {result.error}")

if result.step_results:
    for step_id, step_result in result.step_results.items():
        print(f"\n{'='*60}")
        print(f"Step: {step_id}")
        print(f"  Success: {step_result.success}")
        
        # Add this too:
        if hasattr(step_result, 'error') and step_result.error:
            print(f"  Error: {step_result.error}")
        
        if step_result.envelope:
            env = step_result.envelope
            print(f"  Data path: {env.data['path']}")
            print(f"  Feature count: {env.metadata.get('feature_count')}")
            print(f"  CRS: {env.metadata.get('crs')}")
            print(f"  Warnings ({len(env.warnings)}):")
            for w in env.warnings:
                print(f"    [{w.level}] {w.message}")