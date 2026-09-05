import os
import sys
import uuid

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from agents import coder_agent
from agents import document_agent
from agents import vision_agent
from backend.logging_audit import log_task_result


class Controller:
    """
    Coordinates specialist agents.

    Every agent returns a standard dictionary:
    {
        "model_used": "...",
        "tools_used": [...],
        "status": "success" or "failed",
        "deliverable_paths": [...]
    }
    """

    def build_plan(
        self,
        task_type: str,
        input_files: list[str],
        instructions: str,
    ) -> list[dict]:
        """
        Creates a deterministic execution plan.

        Rule-based plans are intentionally used for this MVP because
        they are predictable and easy to demonstrate. A LangGraph/LLM
        planner can replace this method later without changing agents.
        """
        if task_type == "code_task":
            return [
                {
                    "step": 1,
                    "agent": "coder_agent",
                    "input": instructions,
                    "depends_on": [],
                }
            ]

        if task_type == "vision_task":
            return [
                {
                    "step": 1,
                    "agent": "vision_agent",
                    "input": input_files,
                    "depends_on": [],
                }
            ]

        if task_type == "approval_note":
            return [
                {
                    "step": 1,
                    "agent": "vision_agent",
                    "input": input_files,
                    "depends_on": [],
                },
                {
                    "step": 2,
                    "agent": "document_agent",
                    "input": instructions,
                    "depends_on": [1],
                },
            ]

        return []

    def _create_failure_result(
        self,
        task_id: str,
        error: str,
        step_results: list[dict] | None = None,
    ) -> dict:
        """
        Builds a consistent failed result, logs it, and returns it.

        This avoids duplicated error-handling code and ensures failed
        tasks are auditable too.
        """
        step_results = step_results or []

        result = {
            "task_id": task_id,
            "status": "failed",
            "error": error,
            "steps": step_results,
            "deliverable_paths": [],
            "models_used": [
                step["model_used"]
                for step in step_results
                if step.get("model_used")
            ],
            "tools_used": [
                tool
                for step in step_results
                for tool in step.get("tools_used", [])
            ],
        }

        result["audit"] = log_task_result(result)
        return result

    def run_task(
        self,
        task_type: str,
        input_files: list[str],
        instructions: str,
    ) -> dict:
        """
        Executes the entire task plan, aggregates results,
        and writes an audit entry automatically.
        """
        task_id = str(uuid.uuid4())
        plan = self.build_plan(task_type, input_files, instructions)

        if not plan:
            return self._create_failure_result(
                task_id=task_id,
                error=f"Unsupported task type: {task_type}",
            )

        step_results = []

        for step in plan:
            agent_name = step["agent"]

            if agent_name == "coder_agent":
                result = coder_agent.run(step["input"])

            elif agent_name == "vision_agent":
                result = vision_agent.run(step["input"])

            elif agent_name == "document_agent":
                vision_result = step_results[0]

                if vision_result["status"] != "success":
                    return self._create_failure_result(
                        task_id=task_id,
                        error=(
                            "Vision extraction failed; approval note "
                            "was not generated."
                        ),
                        step_results=step_results,
                    )

                result = document_agent.run(
                    instructions=step["input"],
                    context={
                        "findings": vision_result["findings"],
                    },
                )

            else:
                result = {
                    "status": "failed",
                    "error": f"Unknown agent: {agent_name}",
                    "model_used": None,
                    "tools_used": [],
                    "deliverable_paths": [],
                }

            step_record = {
                "step": step["step"],
                "agent": agent_name,
                **result,
            }
            step_results.append(step_record)

            if result["status"] != "success":
                return self._create_failure_result(
                    task_id=task_id,
                    error=result.get(
                        "error",
                        f"{agent_name} failed while executing the task.",
                    ),
                    step_results=step_results,
                )

        final_result = {
            "task_id": task_id,
            "status": "success",
            "plan": plan,
            "steps": step_results,
            "deliverable_paths": [
                path
                for step in step_results
                for path in step.get("deliverable_paths", [])
            ],
            "models_used": [
                step["model_used"]
                for step in step_results
                if step.get("model_used")
            ],
            "tools_used": [
                tool
                for step in step_results
                for tool in step.get("tools_used", [])
            ],
        }

        # The audit write happens only after every agent has finished.
        final_result["audit"] = log_task_result(final_result)

        return final_result


if __name__ == "__main__":
    controller = Controller()

    result = controller.run_task(
        task_type="code_task",
        input_files=[],
        instructions=(
            "Write a Python script that prints the squares of numbers "
            "from 1 to 5."
        ),
    )

    print("\n--- CONTROLLER TEST ---")
    print("Task ID:", result["task_id"])
    print("Status:", result["status"])
    print("Models used:", result["models_used"])
    print("Tools used:", result["tools_used"])
    print("Sovereignty:", result["audit"]["sovereignty_status"])