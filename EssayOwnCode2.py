from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from typing import TypedDict, Annotated
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage
import operator


# Load Environment
load_dotenv()


# Define Models & Schemas
model = ChatOpenAI(model="gpt-4o-mini")

class EvaluationSchema(BaseModel):
    feedback: str = Field(description="Detailed feedback for the essay")
    score: int = Field(description="Score out of 10", ge=0, le=10)

structured_model = model.with_structured_output(EvaluationSchema)


# Define State
class UPSCState(TypedDict):
    essay: str
    messages: Annotated[list[BaseMessage], add_messages]
    language_feedback: str
    analysis_feedback: str
    clarity_feedback: str
    individual_scores: Annotated[list[int], operator.add]
    avg_score: float
    overall_feedback: str


# Define LangGraph Nodes
def evaluate_language(state: UPSCState):
    prompt = f"Evaluate the language quality of the following essay:\n{state['essay']}"
    output = structured_model.invoke(prompt)
    return {"language_feedback": output.feedback, "individual_scores": [output.score]}

def evaluate_analysis(state: UPSCState):
    prompt = f"Evaluate the depth of analysis of the following essay:\n{state['essay']}"
    output = structured_model.invoke(prompt)
    return {"analysis_feedback": output.feedback, "individual_scores": [output.score]}

def evaluate_thought(state: UPSCState):
    prompt = f"Evaluate the clarity of thought of the following essay:\n{state['essay']}"
    output = structured_model.invoke(prompt)
    return {"clarity_feedback": output.feedback, "individual_scores": [output.score]}

def final_evaluation(state: UPSCState):
    if state["individual_scores"]:
        avg_score = sum(state["individual_scores"]) / len(state["individual_scores"])
    else:
        avg_score = 0.0
    
    prompt = f"""Provide an overall evaluation considering the following feedback and scores:
- Language: {state['language_feedback']} (Score: {state['individual_scores'][0] if len(state['individual_scores']) > 0 else 'N/A'})
- Analysis: {state['analysis_feedback']} (Score: {state['individual_scores'][1] if len(state['individual_scores']) > 1 else 'N/A'})
- Clarity: {state['clarity_feedback']} (Score: {state['individual_scores'][2] if len(state['individual_scores']) > 2 else 'N/A'})

Based on this, provide a concise final summary and the final average score of {avg_score:.2f}."""
    
    output = model.invoke(prompt)
    return {"overall_feedback": output.content, "avg_score": avg_score}


# Build Graph
def build_graph():
    checkpointer = InMemorySaver()
    workflow = StateGraph(UPSCState)

    workflow.add_node("evaluate_language", evaluate_language)
    workflow.add_node("evaluate_analysis", evaluate_analysis)
    workflow.add_node("evaluate_thought", evaluate_thought)
    workflow.add_node("final_evaluation", final_evaluation)

    workflow.add_edge(START, "evaluate_language")
    workflow.add_edge("evaluate_language", "evaluate_analysis")
    workflow.add_edge("evaluate_analysis", "evaluate_thought")
    workflow.add_edge("evaluate_thought", "final_evaluation")
    workflow.add_edge("final_evaluation", END)

    return workflow.compile(checkpointer=checkpointer)

graph = build_graph()