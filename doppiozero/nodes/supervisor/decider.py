from pocketflow import Node
from ...clients.llm import llm_client
from ...utils.utils import get_logger

logger = get_logger(__name__)


class ActionDecider(Node):
    def prep(self, shared):
        """Prepare the context and question for the decision-making process."""
        # Get the current context (default to "No previous search" if none exists)
        context = shared.get("context", "No previous search")
        # Get the question from the shared store
        question = shared["question"]
        # Return both for the exec step
        return question, context

    def exec(self, inputs):
        """Call the LLM to decide whether to search or answer."""
        question, context = inputs

        logger.info("🤔 Agent deciding what to do next...")

        # Create a prompt to help the LLM decide what to do next
        prompt = f"""
            ### CONTEXT
            You are a research assistant that can search the web.
            Question: {question}
            Previous Research: {context}

            ### ACTION SPACE
            [1] search
            Description: Look up more information on the web
            Parameters:
                - query (str): What to search for

            [2] answer
            Description: Answer the question with current knowledge
            Parameters:
                - answer (str): Final answer to the question

            ## NEXT ACTION
            Decide the next action based on the context and available actions.
            Return your response in this format:

            ```yaml
            thinking: |
                <your step-by-step reasoning process>
            action: search OR answer
            reason: <why you chose this action>
            search_query: <specific search query if action is search>
            ```
        """

        # Call the LLM to make a decision
        result_dc, response_dc = llm_client.generate(prompt)

        return result_dc

    def post(self, shared, prep_res, exec_res):
        """Save the decision and determine the next step in the flow."""
        # If LLM decided to search, save the search query
        if exec_res["action"] == "search":
            shared["search_query"] = exec_res["search_query"]
            logger.info(f"🔍 Agent decided to search for: {exec_res['search_query']}")
        else:
            logger.info("💡 Agent decided to answer the question!")

        # Return the action to determine the next node in the flow
        return exec_res["action"]
