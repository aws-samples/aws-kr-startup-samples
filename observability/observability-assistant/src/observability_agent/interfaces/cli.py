"""Main entry point for the observability agent."""
import asyncio
import sys
from typing import NoReturn

from observability_agent.agents.coordinator import CoordinatorAgent


async def main() -> NoReturn:
    """Run the observability agent."""
    
    coordinator = CoordinatorAgent()
    
    # INITIALIZATION PHASE - Exit on any failure
    try:
        print("Initializing ToolRegistry...")
        coordinator.initialize()
        print("ToolRegistry initialized successfully.")
        
        # Show datasource greeting
        greeting = coordinator.get_datasource_greeting()
        print(f"\n{greeting}\n")
        
        print("Type 'exit' to quit.")
        
        # Get the underlying agent
        agent = coordinator.get_agent()
        
    except Exception as e:
        print(f"\n💥 INITIALIZATION FAILED: {e}")
        print("The observability assistant cannot start. Exiting...")
        
        # Clean up and exit
        try:
            coordinator.cleanup()
        except Exception:
            pass  # Ignore cleanup errors during failed initialization
        
        sys.exit(1)
    
    # CONVERSATION LOOP - Handle individual errors gracefully
    try:
        while True:
            try:
                # Get user input
                user_input = input("\nYou: ")
                
                # Check if the user wants to exit
                if user_input.lower() in ["exit", "quit", "q"]:
                    print("Goodbye!")
                    break

                # Process the user input
                print("\nAssistant: ", end="", flush=True)

                # Stream the response
                result = agent.stream_async(user_input)
                async for event in result:
                    if "data" in event:                  
                        print(event["data"], end="", flush=True)
                print()
                
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"\nError: {e}")
                import traceback
                traceback.print_exc()
    
    finally:
        # Clean up the coordinator agent
        print("Cleaning up ToolRegistry...")
        coordinator.cleanup()
        print("Cleanup complete.")


if __name__ == "__main__":
    asyncio.run(main()) 