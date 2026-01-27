"""Example demonstrating how to create custom tools."""

import asyncio
from typing import Any, Dict

from minicode import Agent, BaseTool, ToolContext
from minicode.llm import OpenAILLM


class CalculatorTool(BaseTool):
    """A simple calculator tool that performs basic arithmetic."""

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Perform basic arithmetic operations. " "Supports: add, subtract, multiply, divide"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide"],
                    "description": "The operation to perform",
                },
                "a": {
                    "type": "number",
                    "description": "First operand",
                },
                "b": {
                    "type": "number",
                    "description": "Second operand",
                },
            },
            "required": ["operation", "a", "b"],
        }

    async def execute(
        self,
        params: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        """Execute the calculation."""
        operation = params.get("operation")
        a = params.get("a")
        b = params.get("b")

        try:
            if operation == "add":
                result = a + b
            elif operation == "subtract":
                result = a - b
            elif operation == "multiply":
                result = a * b
            elif operation == "divide":
                if b == 0:
                    return {
                        "success": False,
                        "error": "Cannot divide by zero",
                    }
                result = a / b
            else:
                return {
                    "success": False,
                    "error": f"Unknown operation: {operation}",
                }

            return {
                "success": True,
                "data": result,
                "operation": operation,
                "operands": [a, b],
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Calculation failed: {str(e)}",
            }


class GreeterTool(BaseTool):
    """A simple tool that greets users."""

    @property
    def name(self) -> str:
        return "greeter"

    @property
    def description(self) -> str:
        return "Generate a personalized greeting message"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the person to greet",
                },
                "style": {
                    "type": "string",
                    "enum": ["formal", "casual", "enthusiastic"],
                    "description": "Style of greeting",
                    "default": "casual",
                },
            },
            "required": ["name"],
        }

    async def execute(
        self,
        params: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        """Generate a greeting."""
        name = params.get("name", "there")
        style = params.get("style", "casual")

        greetings = {
            "formal": f"Good day, {name}. It is a pleasure to make your acquaintance.",
            "casual": f"Hey {name}! How's it going?",
            "enthusiastic": f"OMG {name}!!! SO GREAT to see you!!! 🎉",
        }

        greeting = greetings.get(style, greetings["casual"])

        return {
            "success": True,
            "data": greeting,
            "name": name,
            "style": style,
        }


async def demo_without_llm() -> None:
    """Demonstrate tools without an LLM (direct execution)."""
    print("Demo 1: Direct Tool Execution")
    print("=" * 50)

    # Create tools
    calc = CalculatorTool()
    greeter = GreeterTool()

    # Create a context
    context = ToolContext(agent_name="demo", session_id="test")

    # Execute calculator
    print("\nCalculating 15 + 27:")
    result = await calc.execute(
        {"operation": "add", "a": 15, "b": 27},
        context,
    )
    print(f"Result: {result}")

    # Execute greeter
    print("\nGenerating enthusiastic greeting:")
    result = await greeter.execute(
        {"name": "Alice", "style": "enthusiastic"},
        context,
    )
    print(f"Result: {result}")


async def demo_with_llm() -> None:
    """Demonstrate tools with an LLM agent."""
    print("\n\nDemo 2: Tools with LLM Agent")
    print("=" * 50)

    # Note: This requires OPENAI_API_KEY environment variable
    import os

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\nSkipping LLM demo - OPENAI_API_KEY not set")
        print("Set the environment variable to run this demo.")
        return

    # Create agent with custom tools
    agent = Agent(
        name="calculator-assistant",
        llm=OpenAILLM(api_key=api_key, model="gpt-4"),
        tools=[CalculatorTool(), GreeterTool()],
        prompt="You are a helpful assistant with calculator and greeting capabilities.",
    )

    # Test the agent
    test_message = "Calculate 123 * 456 and then greet John in a formal style"
    print(f"\nUser: {test_message}")
    print("\nAgent: ", end="", flush=True)

    async for chunk in agent.stream(test_message):
        if chunk.get("type") == "content":
            print(chunk.get("content", ""), end="", flush=True)
        elif chunk.get("type") == "tool_call":
            tool_call = chunk.get("tool_call", {})
            function = tool_call.get("function", {})
            print(f"\n[Using {function.get('name')}]", flush=True)
        elif chunk.get("type") == "done":
            print("\n")
            break


async def main() -> None:
    """Run all custom tool examples."""
    print("Custom Tools Example")
    print("=" * 50)
    print("\nThis example shows how to create custom tools")
    print("and use them with agents.\n")

    await demo_without_llm()
    await demo_with_llm()

    print("\n" + "=" * 50)
    print("Example complete!")
    print("\nKey points for creating custom tools:")
    print("1. Extend the BaseTool class")
    print("2. Define name, description, and parameters_schema")
    print("3. Implement the execute() method")
    print("4. Return results in the expected format")
    print("5. Optionally override requires_confirmation() for sensitive operations")


if __name__ == "__main__":
    asyncio.run(main())
