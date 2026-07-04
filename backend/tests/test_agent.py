import unittest
from app.agents.graph import AgentGraph, intent_router_node
from app.agents.state.agent_state import AgentState
from app.llm.providers.mock_llm import MockLLM
from app.services.db_service import DBService
from app.services.schema_service import SchemaService

class TestAgent(unittest.TestCase):
    def setUp(self):
        self.llm = MockLLM()
        self.db_service = DBService()
        self.schema_service = SchemaService()

    def test_intent_router_heuristics(self):
        # General chat checks
        state = AgentState(question="hello assistant", source_id="default")
        res = intent_router_node(state, self.llm)
        self.assertEqual(res["intent"], "GENERAL")

        state = AgentState(question="who are you", source_id="default")
        res = intent_router_node(state, self.llm)
        self.assertEqual(res["intent"], "GENERAL")

        # Modification checks
        state = AgentState(question="insert record into employees", source_id="default")
        res = intent_router_node(state, self.llm)
        self.assertEqual(res["intent"], "ADD")

        state = AgentState(question="update department set name = 'Sales'", source_id="default")
        res = intent_router_node(state, self.llm)
        self.assertEqual(res["intent"], "UPDATE")

        # Inquire checks
        state = AgentState(question="how many employees work in IT", source_id="default")
        res = intent_router_node(state, self.llm)
        self.assertEqual(res["intent"], "INQUIRE")

    def test_agent_graph_build(self):
        agent = AgentGraph(self.llm, self.db_service, self.schema_service)
        self.assertIsNotNone(agent.graph)

if __name__ == "__main__":
    unittest.main()
