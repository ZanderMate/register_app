import logging
from app import ScriptPlatform

logging.basicConfig(level=logging.INFO)

def main():
    # Initialize the platform
    platform = ScriptPlatform()

    # Register scripts
    platform.register_script(
        name="example_1",
        path="scripts/example_script_1.py",
        tags=["example"]
    )
    platform.register_script(
        name="example_2",
        path="scripts/example_script_2.py",
        tags=["example"]
    )

    # List register scripts
    platform.list_scripts()

    # Run a single script using engine.run()
    # entry = platform.registry.get("example")
    # result = platform.engin.run(entry)
    # print(f"Script: {result.script_name} | Success: {result.success}")

    # Run all scripts by iterating over registry._scripts
    # prnt("\nRunning all scripts:")
    # for name in platform.registry._script:
    #   entry = platform.registry.get(name)
    #   result = platform.engine.run(entry)
    #   print(f"Script: {result.script_name} | Success: {result.success}")

    # Run scripts with a specific tag
    print("\nRunning scripts with specific tag.")
    all_results = []
    for name in platform.registry._scripts:
        entry = platform.registry.get(name)
        if "certificate expiration" in entry.tags:
            result = platform.engine.run(entry)
            all_results.append(result)
            print(f"Script: {result.script_name} | Status: {result.success}")

    # Print results summary
    print("\n--- Results Summary ---")
    for result in all_results:
        print(f"Script: {result.script_name}")
        print(f" Success:       {result.success}")
        print(f" Return Code:   {result.return_code}")
        print(f" Duration:      {result.duration_seconds:.2f}s")
        if result.stdout:
            print(f" Output:        {result.stdout}")
        if result.error_message:
            print(f" Error:         {result.error_message}")
if __name__ == "__main__":
    main()