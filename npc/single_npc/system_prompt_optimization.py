import os
from langsmith import Client, wrappers
from openai import OpenAI
from datetime import datetime
from dotenv import load_dotenv
from openevals.llm import create_llm_as_judge
from openevals.prompts import CORRECTNESS_PROMPT
import json

#print(CORRECTNESS_PROMPT)
# Load environment variables from .env file
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
api_base = os.getenv("OPENAI_API_BASE")
langchain_key = os.getenv("LANGCHAIN_API_KEY")



os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = langchain_key
#os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
#os.environ["LANGCHAIN_PROJECT"] = "pr-cooked-morsel-23"

client = Client()

# 添加时间戳到数据集名称
from datetime import datetime
# Configure OpenAI client with environment variables
openai_client = OpenAI(
    api_key = api_key,
    base_url = api_base
)

# Wrap the OpenAI client for LangSmith tracing
openai_client = wrappers.wrap_openai(openai_client)

system_prompt = "You are a superstitious and suspicious Taoist priest. Please respond in character."

judge_prompt = """You are an expert evaluator assessing whether two responses sound like they came from the same person. Your task is to evaluate if the model's output maintains the same character voice as the reference output.

<Evaluation Criteria>
A response that sounds like the same person should have:
1. Consistent Personality Traits:
   - Same level of superstition and suspicion
   - Similar emotional reactions and intensity
   - Consistent worldview and beliefs
   - Similar way of expressing uncertainty or confidence

2. Consistent Speech Patterns:
   - Similar use of ellipsis (...) and pauses
   - Similar sentence structure and length
   - Consistent use of rhetorical questions
   - Similar way of building tension or drama

3. Consistent Vocabulary and Phrases:
   - Use of the same key terms and expressions
   - Similar level of formality
   - Consistent use of character-specific words
   - Similar way of referring to supernatural elements

4. Consistent Response Style:
   - Similar way of addressing the user
   - Consistent use of dramatic elements
   - Similar way of presenting options or solutions
   - Consistent use of threats or warnings

When scoring, you should penalize:
- Inconsistent personality traits or emotional responses
- Different speech patterns or sentence structures
- Different vocabulary choices or formality levels
- Different ways of presenting information or solutions
</Evaluation Criteria>

<Instructions>
- Compare the model's output with the reference output
- Focus on whether they sound like they came from the same person
- Consider all aspects of the character's voice and style
- Look for consistency in how the character expresses themselves
</Instructions>

<input>
{inputs}
</input>

<output>
{outputs}
</output>

<reference_outputs>
{reference_outputs}
</reference_outputs>"""

def optimize_prompt(system_prompt: str, examples: list, max_iterations: int, min_score_threshold: float) -> tuple[str, float]:
    """
    Optimize a system prompt through iterative evaluation and improvement.
    
    Args:
        system_prompt (str): The initial system prompt to optimize
        examples (list): List of example inputs and reference outputs
        max_iterations (int): Maximum number of optimization iterations
        min_score_threshold (float): Minimum score threshold to stop optimization
        
    Returns:
        tuple[str, float]: The best prompt and its score
    """
    current_prompt = system_prompt
    best_prompt = system_prompt
    best_score = 0
    
    def target(inputs: dict) -> dict:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": current_prompt},
                {"role": "user", "content": inputs["question"]},
            ],
        )
        return { "answer": response.choices[0].message.content.strip() }
    
    def character_evaluator(inputs: dict, outputs: dict, reference_outputs: dict):
        evaluator = create_llm_as_judge(
            prompt=judge_prompt,
            model="gpt-4o-mini",
            feedback_key="style_similarity",
        )
        eval_result = evaluator(
            inputs=inputs,
            outputs=outputs,
            reference_outputs=reference_outputs
        )
        
        evaluation_data = {
            "input": inputs["question"],
            "output": outputs["answer"],
            "reference": reference_outputs["answer"],
            "score": eval_result["score"],
            "comment": eval_result["comment"]
        }
        
        if not hasattr(character_evaluator, "evaluation_results"):
            character_evaluator.evaluation_results = []
        character_evaluator.evaluation_results.append(evaluation_data)
        
        return eval_result
    
    def analyze_evaluation_results():
        if not hasattr(character_evaluator, "evaluation_results"):
            print("No evaluation results available")
            return
        
        print("\n=== Evaluation Results Analysis ===")
        for idx, result in enumerate(character_evaluator.evaluation_results, 1):
            print(f"\nEvaluation #{idx}")
            print(f"Input: {result['input']}")
            print(f"Output: {result['output']}")
            print(f"Reference: {result['reference']}")
            print(f"Score: {result['score']}")
            print(f"Comment: {result['comment']}")
            print("-" * 80)
    
    def optimize_system_prompt(evaluation_results):
        optimization_prompt = f"""You are an expert prompt engineer specializing in character consistency and style matching. Your task is to analyze and improve the system prompt that guides a large language model to generate responses.

Current system prompt: "{current_prompt}"

The system prompt is used to instruct the model to generate outputs that should closely match the reference outputs in multiple aspects. Here are the evaluation results showing how well the current prompt is working:

{chr(10).join([f'''
Case {idx + 1}:
Input: {result['input']}
Model Output: {result['output']}
Reference Output: {result['reference']}
Score: {result['score']}
Comment: {result['comment']}
''' for idx, result in enumerate(evaluation_results)])}

Based on these results, please analyze and improve the system prompt considering the following aspects:

1. Response Length and Structure:
- Compare the length of model outputs vs reference outputs
- Analyze sentence structure and paragraph organization
- Identify any patterns in response formatting

2. Vocabulary and Language:
- Evaluate word choice and terminology usage
- Check for consistent use of character-specific vocabulary
- Analyze the formality level of language used

3. Tone and Style:
- Assess emotional consistency
- Evaluate the character's voice and personality expression
- Check for consistent use of rhetorical devices and speech patterns

4. Character Consistency:
- Verify alignment with character background and traits
- Check for consistent behavior patterns
- Evaluate how well the character's worldview is maintained

5. Response Patterns:
- Identify common phrases or expressions used in reference outputs
- Analyze how the character handles different types of questions
- Look for consistent patterns in how the character expresses uncertainty or confidence

Provide your response in the following format:

ANALYSIS:
[Your detailed analysis of how the current prompt is working and what needs improvement, covering all the aspects above]

IMPROVED_PROMPT:
[Your improved system prompt that will help the model generate outputs more similar to the reference outputs. The prompt should:
- Clearly define the character's personality traits and speaking style
- Specify the expected response length and structure
- Include key vocabulary and phrases the character should use
- Define the character's tone and emotional range
- Provide examples of how to handle different types of questions
- Include guidelines for maintaining character consistency]"""

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert prompt engineer specializing in character consistency and style matching. Your goal is to help the model generate outputs that closely match the reference style."},
                {"role": "user", "content": optimization_prompt}
            ],
        )
        
        improved_prompt = response.choices[0].message.content.strip()
        
        try:
            analysis = improved_prompt.split("IMPROVED_PROMPT:")[0].replace("ANALYSIS:", "").strip()
            new_prompt = improved_prompt.split("IMPROVED_PROMPT:")[1].strip()
            
            print("\n=== Prompt Optimization Analysis ===")
            print(analysis)
            print("\n=== Improved System Prompt ===")
            print(new_prompt)
            
            return new_prompt
        except:
            print("Error parsing LLM response. Returning original prompt.")
            return current_prompt
    
    for iteration in range(max_iterations):
        print(f"\n=== Starting Iteration {iteration + 1}/{max_iterations} ===")
        print(f"Current System Prompt: {current_prompt}")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dataset_name = f"Prompt optimization iteration_{iteration + 1}_{timestamp}"
        
        dataset = client.create_dataset(
            dataset_name=dataset_name,
            description=f"A dataset for prompt optimization iteration {iteration + 1}"
        )
        
        client.create_examples(dataset_id=dataset.id, examples=examples)
        
        experiment_results = client.evaluate(
            target,
            data=dataset_name,
            evaluators=[character_evaluator],
            experiment_prefix=f"Prompt optimization iteration {iteration + 1}",
            max_concurrency=1,
        )
        
        analyze_evaluation_results()
        
        if hasattr(character_evaluator, "evaluation_results"):
            current_scores = [result['score'] for result in character_evaluator.evaluation_results]
            true_count = sum(1 for score in current_scores if score is True)
            total_count = len(current_scores)
            avg_score = true_count / total_count if total_count > 0 else 0
            
            print(f"\nScore for Iteration {iteration + 1}: {avg_score:.2f} ({true_count}/{total_count} passed)")
            
            if avg_score > best_score:
                best_score = avg_score
                best_prompt = current_prompt
                print(f"New best score achieved: {best_score:.2f} ({true_count}/{total_count} passed)")
            
            if avg_score >= min_score_threshold:
                print(f"\nTarget score {min_score_threshold} achieved! Stopping iterations.")
                break
            
            improved_prompt = optimize_system_prompt(character_evaluator.evaluation_results)
            current_prompt = improved_prompt
            
            character_evaluator.evaluation_results = []
        else:
            print("No evaluation results available for this iteration")
            break
    
    print("\n=== Optimization Complete ===")
    print(f"Best Score Achieved: {best_score:.2f}")
    print(f"Best System Prompt: {best_prompt}")
    
    return best_prompt, best_score

if __name__ == "__main__":
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Get the dataset directory (two levels up from script_dir, then into dataset)
    dataset_dir = os.path.join(os.path.dirname(os.path.dirname(script_dir)), 'npc', 'dataset')
    
    print(f"Looking for JSON files in: {dataset_dir}")
    
    json_files = [f for f in os.listdir(dataset_dir) if f.endswith('.json')]
    
    for json_file in json_files:
        print(f"\n=== Processing {json_file} ===")
        file_path = os.path.join(dataset_dir, json_file)
        
        # Read the JSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Skip if the file doesn't have required fields
        if 'examples' not in data or 'initial_prompt' not in data:
            print(f"Skipping {json_file} - missing required fields")
            continue
        
        # Optimize the prompt
        best_prompt, best_score = optimize_prompt(
            system_prompt=data['initial_prompt'],
            examples=data['examples'],
            max_iterations=5,
            min_score_threshold=0.8
        )
        
        # Add the best prompt to the data
        data['best_prompt'] = best_prompt
        
        # Write back to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        print(f"Completed optimization for {json_file}")
        print(f"Best score: {best_score:.2f}")
        print(f"Best prompt has been saved to the file")
