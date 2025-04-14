from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.models.groq import Groq
import asyncio
import os 
from dotenv import load_dotenv
from agno.storage.agent.sqlite import SqliteAgentStorage
load_dotenv()
from templates.st_instructions import (
    leadInstructions,
    writerInstructions,
    artInstructions,
    loreInstructions,
    criticInstructions,
    artCriticInstructions,
    reporterInstructions,
    innovatorInstructions,
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")

textModel = OpenAIChat(id="gpt-3.5-turbo", api_key=OPENAI_API_KEY)
groqModel = Groq(id="qwen-2.5-32b", api_key=GROQ_API_KEY)
groqMultiModel = Groq(id="llama-3.2-90b-vision-preview", api_key=GROQ_API_KEY)
nvidiaModel = OpenAIChat(id="nvidia/llama-3.3-nemotron-super-49b-v1", api_key=NVIDIA_API_KEY, base_url="https://integrate.api.nvidia.com/v1")


agent_config = {
    "storage": SqliteAgentStorage(table_name="narrative_agent", db_file="agent_storage.db"),
    "add_datetime_to_instructions": True,
    "add_history_to_messages": True,
    "num_history_responses": 5,
    "markdown": True,
    "debug_mode": True,
    "monitoring": True,
}

def create_agent_with_config(name, role, instructions, apply_config=False):
    """
    Factory function to create an agent with optional configuration
    """
    agent_params = {
        "name": name,
        "role": role,
        "model": groqModel,
        "instructions": instructions,
    }
    
    if apply_config:
        agent_params.update(agent_config)
        
    return Agent(**agent_params)

def create_narrative_team(apply_config=False):
    lead_agent = create_agent_with_config(
        "Narrative Lead Agent",
        "Develops the overarching story, worldbuilding, and tone.",
        leadInstructions,
        apply_config
    )

    dialogue_agent = create_agent_with_config(
        "Dialogue Writer Agent",
        "Creates character-driven dialogue and interactions.",
        writerInstructions,
        apply_config
    )

    artstyle_agent = create_agent_with_config(
        "Art Style Director Agent",
        "Translates narrative elements into visual prompts.",
        artInstructions,
        apply_config
    )

    lore_agent = create_agent_with_config(
        "Lore Master Agent",
        "Ensures internal consistency in worldbuilding and character arcs.",
        loreInstructions,
        apply_config
    )

    critic_agent = create_agent_with_config(
        "Critic Agent",
        "Reviews outputs from others for coherence, tone, engagement.",
        criticInstructions,
        apply_config
    )

    art_critic_agent = create_agent_with_config(
        "Art Critic Agent",
        "Evaluates AI-generated artwork for narrative and emotional impact.",
        artCriticInstructions,
        apply_config
    )

    reporter_agent = create_agent_with_config(
        "Reporter Agent",
        "Summarizes progress, flags inconsistencies, and prepares reports for human input.",
        reporterInstructions,
        apply_config
    )
    
    # Backlog ideas
    # SQL agent, RAG agent - https://docs.agno.com/examples/concepts/rag/agentic-rag-lancedb
    # Youtube agent
    
    innovator_agent = create_agent_with_config(
        "Innovator Agent",
        "Generates new ideas and concepts based on the narrative.",
        "You are an innovative thinker who generates new ideas and concepts.",
        apply_config
    )

    team = [lead_agent, dialogue_agent, artstyle_agent, lore_agent, critic_agent, art_critic_agent, reporter_agent]
    narrative_team_params = {
        "team": team,
        "name": "Narrative Team",
        "model": textModel,
        "instructions": [
            "First ask the search journalist to search for the most relevant URLs for that topic.",
            "Then ask the writer to get an engaging draft of the article.",
            "Edit, proofread, and refine the article to ensure it meets the high standards of the New York Times.",
            "The article should be extremely articulate and well written. "
            "Focus on clarity, coherence, and overall quality.",
            "Remember: you are the final gatekeeper before the article is published, so make sure the article is perfect.",
        ],
        "add_datetime_to_instructions": True,
        "markdown": True,
        "debug_mode": False
    }
    
    if apply_config:
        narrative_team_params.update({k: v for k, v in agent_config.items() if k not in ["markdown", "debug_mode", "show_team_responses"]})
    
    agent_team = Agent(**narrative_team_params)
    
    return team, agent_team


# Create default instances (without config)
agent_team, team = create_narrative_team()

# Example discussion
if __name__ == "__main__":
    asyncio.run(
        agent_team.print_response(
            message="Start the discussion on the topic: 'What is the best way to learn to code?'",
            stream=True,
            stream_intermediate_steps=True,
        )
    )