from duckduckgo_search import DDGS

from ...pocketflow import Node
from ...utils.utils import get_logger

logger = get_logger(__name__)


class SearcherNode(Node):
    def prep(self, shared):
        """Get the search query from the shared store."""
        return shared["search_query"]

    def _search_web(self, query):
        results = DDGS().text(query, max_results=5)
        # Convert results to a string
        results_str = "\n\n".join(
            [f"Title: {r['title']}\nURL: {r['href']}\nSnippet: {r['body']}" for r in results]
        )

        return results_str

    def exec(self, search_query):
        """Search the web for the given query."""
        # Call the search utility function
        logger.info(f"🌐 Searching the web for: {search_query}")
        results = self._search_web(search_query)
        return results

    def post(self, shared, prep_res, exec_res):
        """Save the search results and go back to the decision node."""
        # Add the search results to the context in the shared store
        previous = shared.get("context", "")
        shared["context"] = (
            previous + "\n\nSEARCH: " + shared["search_query"] + "\nRESULTS: " + exec_res
        )

        logger.info("📚 Found information, analyzing results...")

        # Always go back to the decision node after searching
        return "decide"
